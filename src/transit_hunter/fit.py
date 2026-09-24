"""Bayesian transit fitting with ``batman`` and ``emcee``.

Model
-----
A circular-orbit ``batman`` transit (quadratic limb darkening) times a constant
baseline ``f0`` is fitted to the detrended light curve inside windows around
each transit. The sampled parameters and their priors are:

=============  ===========================================  ===========================
parameter      meaning                                      prior
=============  ===========================================  ===========================
``t0``         mid-transit time near the data centre        uniform, +/- 1 BLS duration
``period``     orbital period                               uniform, wide around BLS
``rp_rs``      planet-to-star radius ratio k                uniform (1e-4, 1)
``ln_a_rs``    ln(a / R*)                                   uniform (ln 1.2, ln 500)
``b``          impact parameter                             uniform (0, 1 + k)
``q1, q2``     Kipping (2013) limb-darkening parameters     uniform (0, 1) [+ optional
                                                            Gaussian prior on u1, u2]
``f0``         out-of-transit baseline                      uniform (0.9, 1.1)
``ln_jitter``  extra white noise added in quadrature        uniform (ln 1e-7, ln 0.1)
=============  ===========================================  ===========================

The mean stellar density is deliberately *not* used as a prior: comparing the
density implied by the transit shape with the catalogue value is one of the
vetting tests (:mod:`transit_hunter.vet`).

The reference epoch ``t0`` is moved to the transit closest to the middle of
the data, which minimises the correlation between ``t0`` and ``period``.

Sampling
--------
The chain starts in a small ball around the maximum-a-posteriori point (found
with Powell's method from several impact parameters, to avoid the grazing /
non-grazing local optima). It runs until it is longer than 50 integrated
autocorrelation times and the autocorrelation estimate has stabilised to 1 %,
or until ``max_steps``. Burn-in is two autocorrelation times; the chain is
thinned by half an autocorrelation time.
"""

from __future__ import annotations

import logging
import math
import multiprocessing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure
from scipy.optimize import minimize

from .catalog import StellarParams
from .lightcurve import LightCurve
from .models import BatmanModel, q_to_u
from .plotting import (
    BLUE,
    INK,
    INK_MUTED,
    ORANGE,
    new_figure,
    save_figure,
    style,
)
from .utils import AU, DAY, R_EARTH, R_JUP, R_SUN, RHO_SUN, G, bin_timeseries, fold

log = logging.getLogger(__name__)

PARAMS = ("t0", "period", "rp_rs", "ln_a_rs", "b", "q1", "q2", "f0", "ln_jitter")


@dataclass(frozen=True)
class FitConfig:
    """MCMC settings.

    Attributes
    ----------
    n_walkers : emcee walkers.
    max_steps, min_steps, check_interval : chain length control (see module docstring).
    window : half-width of the fitted window around each transit, in units of
        the BLS duration.
    fit_jitter : sample an additional white-noise term.
    ld_prior : optional Gaussian prior ``(u1, sigma_u1, u2, sigma_u2)`` on the
        quadratic coefficients, e.g. from tabulated stellar-atmosphere models.
    supersample : sub-exposures per cadence (``None`` = automatic: 1 for 2-min data).
    n_workers : processes for likelihood evaluation (requires the "fork" start method).
    seed : random seed for walker initialisation and sampling.
    """

    n_walkers: int = 40
    max_steps: int = 20000
    min_steps: int = 2000
    check_interval: int = 500
    window: float = 2.5
    fit_jitter: bool = True
    ld_prior: tuple[float, float, float, float] | None = None
    supersample: int | None = None
    n_workers: int = 1
    seed: int | None = 42


class TransitFitter:
    """Posterior for one transiting planet in a detrended light curve."""

    def __init__(
        self,
        lc: LightCurve,
        period: float,
        t0: float,
        duration: float,
        depth: float,
        config: FitConfig | None = None,
    ):
        self.config = config or FitConfig()
        lc = lc.finite()
        n_mid = round((np.median(lc.time) - t0) / period)
        t0 = t0 + n_mid * period
        near = np.abs(fold(lc.time, period, t0)) < self.config.window * duration
        if near.sum() < 20:
            raise ValueError("fewer than 20 data points inside the transit windows")
        self.time = lc.time[near]
        self.flux = lc.flux[near]
        self.err = lc.flux_err[near]
        self.names = PARAMS if self.config.fit_jitter else PARAMS[:-1]
        self.guess = {"t0": t0, "period": period, "duration": duration, "depth": max(depth, 1e-6)}

        diffs = np.diff(self.time)
        cadence = float(np.median(diffs[diffs < 0.1])) if np.any(diffs < 0.1) else 2 / 1440
        self.cadence = cadence
        auto = max(1, math.ceil(cadence * 1440 / 2.0 - 1e-6))
        self.supersample = self.config.supersample or auto
        self.exp_time = cadence if self.supersample > 1 else 0.0
        self._model: BatmanModel | None = None

        span = float(self.time.max() - self.time.min())
        d_period = max(duration * period / max(span, period), 1e-5 * period)
        self.bounds: dict[str, tuple[float, float]] = {
            "t0": (t0 - duration, t0 + duration),
            "period": (period - d_period, period + d_period),
            "rp_rs": (1e-4, 1.0),
            "ln_a_rs": (math.log(1.2), math.log(500.0)),
            "b": (0.0, 2.0),  # the effective upper limit 1 + k is applied in log_prior
            "q1": (0.0, 1.0),
            "q2": (0.0, 1.0),
            "f0": (0.9, 1.1),
            "ln_jitter": (math.log(1e-7), math.log(0.1)),
        }

    # -- serialisation: the batman object is rebuilt lazily in worker processes
    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_model"] = None
        return state

    @property
    def model(self) -> BatmanModel:
        if self._model is None:
            self._model = BatmanModel(self.time, self.supersample, self.exp_time)
        return self._model

    @property
    def ndim(self) -> int:
        return len(self.names)

    def unpack(self, theta: np.ndarray) -> dict[str, float]:
        p = dict(zip(self.names, (float(x) for x in theta), strict=True))
        p.setdefault("ln_jitter", -math.inf)
        return p

    def log_prior(self, theta: np.ndarray) -> float:
        p = self.unpack(theta)
        for name in self.names:
            lo, hi = self.bounds[name]
            if not lo < p[name] < hi:
                return -math.inf
        if p["b"] >= 1.0 + p["rp_rs"]:
            return -math.inf  # no transit at all
        lp = 0.0
        if self.config.ld_prior is not None:
            mu1, s1, mu2, s2 = self.config.ld_prior
            u1, u2 = q_to_u(p["q1"], p["q2"])
            lp -= 0.5 * (((u1 - mu1) / s1) ** 2 + ((u2 - mu2) / s2) ** 2)
        return lp

    def model_flux(self, theta: np.ndarray, time: np.ndarray | None = None) -> np.ndarray:
        p = self.unpack(theta)
        a_rs = math.exp(p["ln_a_rs"])
        inc = math.degrees(math.acos(min(p["b"] / a_rs, 1.0)))
        u1, u2 = q_to_u(p["q1"], p["q2"])
        model = self.model if time is None else BatmanModel(time, self.supersample, self.exp_time)
        return p["f0"] * model(p["t0"], p["period"], p["rp_rs"], a_rs, inc, u1, u2)

    def log_likelihood(self, theta: np.ndarray) -> float:
        p = self.unpack(theta)
        resid = self.flux - self.model_flux(theta)
        var = self.err**2 + math.exp(2.0 * p["ln_jitter"])
        return float(-0.5 * np.sum(resid**2 / var + np.log(2.0 * math.pi * var)))

    def log_prob(self, theta: np.ndarray) -> float:
        lp = self.log_prior(theta)
        if not math.isfinite(lp):
            return -math.inf
        ll = self.log_likelihood(theta)
        return lp + ll if math.isfinite(ll) else -math.inf

    # -- optimisation and sampling
    def _start(self, b: float) -> np.ndarray:
        g = self.guess
        k = math.sqrt(g["depth"])
        chord = math.sqrt(max((1.0 + k) ** 2 - b**2, 1e-4))
        a_rs = float(np.clip(g["period"] / (math.pi * g["duration"]) * chord, 1.5, 400.0))
        oot = np.abs(fold(self.time, g["period"], g["t0"])) > 0.75 * g["duration"]
        f0 = float(np.median(self.flux[oot])) if oot.sum() > 5 else 1.0
        start = {
            "t0": g["t0"],
            "period": g["period"],
            "rp_rs": k,
            "ln_a_rs": math.log(a_rs),
            "b": b,
            "q1": 0.36,
            "q2": 0.3,
            "f0": f0,
            "ln_jitter": math.log(1e-5),
        }
        return np.array([start[n] for n in self.names])

    def find_map(self) -> np.ndarray:
        """Maximum-a-posteriori parameters (Powell, from several impact parameters)."""
        best, best_lp = None, -math.inf
        for b in (0.1, 0.5, 0.8):
            x0 = self._start(b)
            if not math.isfinite(self.log_prob(x0)):
                continue
            res = minimize(
                self._neg_log_prob,
                x0,
                method="Powell",
                options={"maxiter": 20000, "xtol": 1e-6, "ftol": 1e-9},
            )
            lp = self.log_prob(res.x)
            if lp > best_lp:
                best, best_lp = res.x, lp
        if best is None:
            raise RuntimeError("could not find a valid starting point for the fit")
        return best

    def _neg_log_prob(self, theta: np.ndarray) -> float:
        lp = self.log_prob(theta)
        return -lp if math.isfinite(lp) else 1e25

    def _initial_walkers(self, center: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        scale = {
            "t0": 1e-4,
            "period": 1e-7 * self.guess["period"],
            "rp_rs": 1e-4,
            "ln_a_rs": 1e-3,
            "b": 1e-3,
            "q1": 1e-3,
            "q2": 1e-3,
            "f0": 1e-6,
            "ln_jitter": 1e-2,
        }
        sigma = np.array([scale[n] for n in self.names])
        walkers = []
        while len(walkers) < self.config.n_walkers:
            trial = center + sigma * rng.standard_normal(self.ndim)
            if math.isfinite(self.log_prob(trial)):
                walkers.append(trial)
        return np.array(walkers)

    def sample(self) -> FitResult:
        """Run the MCMC and return posterior summaries."""
        import emcee

        cfg = self.config
        rng = np.random.default_rng(cfg.seed)
        center = self.find_map()
        p0 = self._initial_walkers(center, rng)

        pool = None
        if cfg.n_workers > 1 and "fork" in multiprocessing.get_all_start_methods():
            global _ACTIVE_FITTER
            _ACTIVE_FITTER = self
            pool = multiprocessing.get_context("fork").Pool(cfg.n_workers)
            log_prob_fn = _global_log_prob
        else:
            log_prob_fn = self.log_prob
        try:
            sampler = emcee.EnsembleSampler(cfg.n_walkers, self.ndim, log_prob_fn, pool=pool)
            # emcee draws from NumPy's legacy RNG; seed it explicitly for reproducibility.
            start = emcee.State(
                p0, random_state=np.random.RandomState(int(rng.integers(2**31))).get_state()
            )
            converged = False
            old_tau = np.inf
            tau = np.full(self.ndim, np.nan)
            for _ in sampler.sample(start, iterations=cfg.max_steps):
                it = sampler.iteration
                if it % cfg.check_interval:
                    continue
                tau = sampler.get_autocorr_time(tol=0)
                stable = np.all(np.abs(old_tau - tau) / tau < 0.01)
                if (
                    it >= cfg.min_steps
                    and np.all(np.isfinite(tau))
                    and np.all(50 * tau < it)
                    and stable
                ):
                    converged = True
                    break
                old_tau = tau
        finally:
            if pool is not None:
                pool.close()
                pool.join()

        n_steps = sampler.iteration
        tau = sampler.get_autocorr_time(tol=0)
        tau_max = float(np.nanmax(tau)) if np.any(np.isfinite(tau)) else float(n_steps) / 10
        burn = min(int(2 * tau_max), n_steps // 2)
        thin = max(1, int(0.5 * np.nanmin(tau))) if np.any(np.isfinite(tau)) else 1
        chain = sampler.get_chain(discard=burn, thin=thin, flat=True)
        log_prob = sampler.get_log_prob(discard=burn, thin=thin, flat=True)
        if not converged:
            log.warning(
                "MCMC did not meet the convergence criterion after %d steps (max tau %.0f)",
                n_steps,
                tau_max,
            )
        best = chain[int(np.argmax(log_prob))]
        return FitResult(
            names=list(self.names),
            samples=chain,
            log_prob=log_prob,
            best=best,
            map_start=center,
            n_steps=int(n_steps),
            burn=int(burn),
            thin=int(thin),
            autocorr=[float(x) for x in tau],
            acceptance=float(np.mean(sampler.acceptance_fraction)),
            converged=bool(converged),
            fitter=self,
        )


_ACTIVE_FITTER: TransitFitter | None = None


def _global_log_prob(theta: np.ndarray) -> float:
    assert _ACTIVE_FITTER is not None
    return _ACTIVE_FITTER.log_prob(theta)


# --------------------------------------------------------------------------- results
def summarize(samples: np.ndarray) -> dict[str, float]:
    """Median and 68 % central interval of a 1-D sample."""
    samples = np.asarray(samples, dtype=float)
    samples = samples[np.isfinite(samples)]
    if samples.size == 0:
        return {"median": float("nan"), "err_lo": float("nan"), "err_hi": float("nan")}
    p16, p50, p84 = np.percentile(samples, [15.865, 50.0, 84.135])
    return {"median": float(p50), "err_lo": float(p50 - p16), "err_hi": float(p84 - p50)}


def derived_samples(
    params: dict[str, np.ndarray],
    stellar: StellarParams | None = None,
    rng: np.random.Generator | None = None,
) -> dict[str, np.ndarray]:
    """Physical quantities computed sample-by-sample from the posterior.

    Stellar radius (and Teff) uncertainties are propagated by drawing one value
    per posterior sample from a normal distribution truncated at zero. If the
    catalogue gives no uncertainty, the value is held fixed (and the resulting
    planet-radius uncertainty is correspondingly underestimated).
    """
    rng = rng or np.random.default_rng(0)
    k = params["rp_rs"]
    a_rs = np.exp(params["ln_a_rs"])
    b = params["b"]
    period = params["period"]
    sin_i = np.sqrt(np.clip(1.0 - (b / a_rs) ** 2, 0.0, 1.0))
    sq = np.sqrt(params["q1"])
    out: dict[str, np.ndarray] = {
        "a_rs": a_rs,
        "inc_deg": np.degrees(np.arccos(np.clip(b / a_rs, -1.0, 1.0))),
        "u1": 2.0 * sq * params["q2"],
        "u2": sq * (1.0 - 2.0 * params["q2"]),
        "depth_ppm": k**2 * 1e6,
    }
    chord14 = np.sqrt(np.clip((1.0 + k) ** 2 - b**2, 0.0, None))
    chord23 = np.sqrt(np.clip((1.0 - k) ** 2 - b**2, 0.0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        x14 = np.clip(np.nan_to_num(chord14 / (a_rs * sin_i), nan=1.0, posinf=1.0), 0, 1)
        x23 = np.clip(np.nan_to_num(chord23 / (a_rs * sin_i), nan=0.0, posinf=1.0), 0, 1)
    out["t14_hours"] = 24 * period / np.pi * np.arcsin(x14)
    out["t23_hours"] = 24 * period / np.pi * np.arcsin(x23)
    rho = 3.0 * np.pi * a_rs**3 / (G * (period * DAY) ** 2)  # kg m^-3
    out["rho_star_cgs"] = rho / 1000.0
    out["rho_star_solar"] = rho / RHO_SUN

    n = k.size
    if stellar is not None and stellar.radius:
        r_star = _draw_positive(stellar.radius, stellar.radius_err, n, rng)
        out["rp_earth"] = k * r_star * R_SUN / R_EARTH
        out["rp_jup"] = k * r_star * R_SUN / R_JUP
        out["a_au"] = a_rs * r_star * R_SUN / AU
    if stellar is not None and stellar.teff:
        teff = _draw_positive(stellar.teff, stellar.teff_err, n, rng)
        # Zero Bond albedo, full heat redistribution.
        out["teq_k"] = teff * np.sqrt(1.0 / (2.0 * a_rs))
    return out


def _draw_positive(value: float, err: float | None, n: int, rng: np.random.Generator) -> np.ndarray:
    if err is None or not np.isfinite(err) or err <= 0:
        return np.full(n, float(value))
    draws = rng.normal(value, err, n)
    bad = draws <= 0
    while np.any(bad):
        draws[bad] = rng.normal(value, err, bad.sum())
        bad = draws <= 0
    return draws


@dataclass
class FitResult:
    names: list[str]
    samples: np.ndarray
    log_prob: np.ndarray
    best: np.ndarray
    map_start: np.ndarray
    n_steps: int
    burn: int
    thin: int
    autocorr: list[float]
    acceptance: float
    converged: bool
    fitter: TransitFitter
    stellar: StellarParams | None = None
    derived: dict[str, np.ndarray] = field(default_factory=dict)

    def param_samples(self) -> dict[str, np.ndarray]:
        return {name: self.samples[:, i] for i, name in enumerate(self.names)}

    def compute_derived(self, stellar: StellarParams | None, seed: int = 0) -> None:
        self.stellar = stellar
        self.derived = derived_samples(self.param_samples(), stellar, np.random.default_rng(seed))

    def summary(self) -> dict[str, dict[str, float]]:
        out = {name: summarize(values) for name, values in self.param_samples().items()}
        out.update({name: summarize(values) for name, values in self.derived.items()})
        return out

    def best_params(self) -> dict[str, float]:
        return dict(zip(self.names, (float(x) for x in self.best), strict=True))

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly report of the fit."""
        return {
            "posterior": self.summary(),
            "max_posterior_sample": self.best_params(),
            "n_samples": int(self.samples.shape[0]),
            "n_steps": self.n_steps,
            "burn_in": self.burn,
            "thin": self.thin,
            "autocorr_time": dict(zip(self.names, self.autocorr, strict=True)),
            "acceptance_fraction": self.acceptance,
            "converged": self.converged,
            "n_points": int(self.fitter.time.size),
            "supersample": self.fitter.supersample,
            "stellar": None if self.stellar is None else self.stellar.as_dict(),
            "config": {
                "n_walkers": self.fitter.config.n_walkers,
                "window_durations": self.fitter.config.window,
                "fit_jitter": self.fitter.config.fit_jitter,
                "ld_prior": self.fitter.config.ld_prior,
            },
        }


def fit_transit(
    lc: LightCurve,
    period: float,
    t0: float,
    duration: float,
    depth: float,
    stellar: StellarParams | None = None,
    config: FitConfig | None = None,
) -> FitResult:
    """Fit one planet (see module docstring) and attach derived quantities."""
    fitter = TransitFitter(lc, period, t0, duration, depth, config)
    result = fitter.sample()
    result.compute_derived(stellar, seed=(config.seed if config and config.seed is not None else 0))
    return result


# --------------------------------------------------------------------------- plots
def plot_fit(result: FitResult, path: str | Path, title: str = "") -> Path:
    """Phase-folded data with the best-fitting model and residuals."""
    fitter = result.fitter
    best = result.best_params()
    period, t0 = best["period"], best["t0"]
    hours = fold(fitter.time, period, t0) * 24.0
    resid = fitter.flux - fitter.model_flux(result.best)
    f0 = best["f0"]
    half = np.max(np.abs(hours))
    grid_t = t0 + np.linspace(-half, half, 1500) / 24.0
    model = fitter.model_flux(result.best, grid_t)
    bin_h = max(result.derived.get("t14_hours", np.array([2.0])).mean() / 10.0, 2.0 / 60.0)
    with style():
        fig, axes = new_figure(2, 1, figsize=(8, 5.2), sharex=True, height_ratios=[3, 1])
        ax, axr = axes[:, 0]
        ax.plot(
            hours,
            (fitter.flux / f0 - 1) * 1e6,
            ".",
            ms=1.5,
            color=INK_MUTED,
            alpha=0.5,
            rasterized=True,
            label="data",
        )
        hb, fb, eb, _ = bin_timeseries(hours, fitter.flux / f0, width=bin_h)
        ax.errorbar(
            hb,
            (fb - 1) * 1e6,
            yerr=eb * 1e6,
            fmt="o",
            ms=3.5,
            color=BLUE,
            lw=1,
            label=f"{bin_h * 60:.0f}-min bins",
        )
        ax.plot(
            (grid_t - t0) * 24,
            (model / f0 - 1) * 1e6,
            "-",
            color=ORANGE,
            lw=1.8,
            label="max-posterior model",
        )
        ax.set_ylabel("flux − 1 (ppm)")
        depth = best["rp_rs"] ** 2 * 1e6
        low = np.nanpercentile((fitter.flux / f0 - 1) * 1e6, 0.5)
        high = np.nanpercentile((fitter.flux / f0 - 1) * 1e6, 99.5)
        ax.set_ylim(min(low, -1.5 * depth), max(high, 0.5 * depth))
        ax.legend(
            loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=3, markerscale=2, borderaxespad=0.1
        )
        rb_h, rb, rb_e, _ = bin_timeseries(hours, resid, width=bin_h)
        axr.plot(hours, resid * 1e6, ".", ms=1.5, color=INK_MUTED, alpha=0.5, rasterized=True)
        axr.errorbar(rb_h, rb * 1e6, yerr=rb_e * 1e6, fmt="o", ms=3, color=BLUE, lw=1)
        axr.axhline(0.0, color=INK, lw=0.8)
        spread = 4 * np.nanstd(rb) * 1e6 if rb.size > 3 else 4 * np.nanstd(resid) * 1e6
        axr.set_ylim(-max(spread, 1.0), max(spread, 1.0))
        axr.set_ylabel("residual (ppm)")
        axr.set_xlabel("hours from mid-transit")
        axr.set_xlim(-half, half)
        fig.suptitle(title or "Transit fit", x=0.01, ha="left", fontsize=12, fontweight="bold")
        return save_figure(fig, path)


def plot_corner(result: FitResult, path: str | Path, title: str = "") -> Path:
    """Corner plot of the sampled parameters (times shown as offsets from their medians)."""
    import corner

    params = result.param_samples()
    t0_med = float(np.median(params["t0"]))
    p_med = float(np.median(params["period"]))
    columns = [
        ((params["t0"] - t0_med) * 1440.0, "ΔT$_0$ (min)"),
        ((params["period"] - p_med) * 86400.0, "ΔP (s)"),
        (params["rp_rs"], "$R_p/R_\\star$"),
        (np.exp(params["ln_a_rs"]), "$a/R_\\star$"),
        (params["b"], "$b$"),
        (params["q1"], "$q_1$"),
        (params["q2"], "$q_2$"),
    ]
    if "ln_jitter" in params:
        columns.append((params["ln_jitter"], "ln σ$_{\\rm jit}$"))
    data = np.column_stack([c[0] for c in columns])
    labels = [c[1] for c in columns]
    k = data.shape[1]
    with style():
        fig = Figure(figsize=(1.55 * k + 1, 1.55 * k + 1))
        corner.corner(
            data,
            labels=labels,
            fig=fig,
            color=BLUE,
            quantiles=[0.15865, 0.5, 0.84135],
            show_titles=True,
            title_fmt=".3g",
            title_kwargs={"fontsize": 8},
            label_kwargs={"fontsize": 9},
            hist_kwargs={"color": BLUE},
            plot_datapoints=False,
            fill_contours=True,
            levels=(0.393, 0.865),
            smooth=1.0,
        )
        fig.suptitle(
            (title + "\n" if title else "") + f"T$_0$ = {t0_med:.5f} BTJD, P = {p_med:.6f} d",
            x=0.99,
            ha="right",
            y=0.98,
            fontsize=10,
        )
        return save_figure(fig, path, dpi=110)

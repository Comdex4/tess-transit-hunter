"""Transit geometry and ``batman`` light-curve models.

Conventions (circular orbits unless stated otherwise; Winn 2010, "Transits and
Occultations", arXiv:1001.2010):

* ``k = Rp/R*`` is the planet-to-star radius ratio; ``a_rs = a/R*``.
* ``b = a cos(i) / R*`` is the impact parameter (0 = central transit).
* ``T14`` is the total duration (first to fourth contact) and ``T23`` the
  duration of the flat bottom (second to third contact)::

      T14 = P/pi * asin( sqrt((1 + k)^2 - b^2) / (a_rs * sin i) )
      T23 = P/pi * asin( sqrt((1 - k)^2 - b^2) / (a_rs * sin i) )

* Kepler's third law with M_p << M* links the transit shape to the mean stellar
  density: ``rho* = 3 pi a_rs^3 / (G P^2)`` (Seager & Mallen-Ornelas 2003).
* Quadratic limb darkening ``I(mu)/I(1) = 1 - u1 (1 - mu) - u2 (1 - mu)^2`` is
  sampled through the Kipping (2013) parameters ``q1 = (u1 + u2)^2`` and
  ``q2 = u1 / (2 (u1 + u2))``: the unit square in (q1, q2) maps one-to-one onto
  the physically allowed region (positive, monotonically decreasing intensity).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .utils import DAY, M_SUN, R_SUN, RHO_SUN, G


def inclination_deg(a_rs: float, b: float) -> float:
    """Orbital inclination (degrees) from ``a/R*`` and impact parameter."""
    return math.degrees(math.acos(min(max(b / a_rs, -1.0), 1.0)))


def t14(period: float, a_rs: float, rp_rs: float, b: float) -> float:
    """Total transit duration (days) for a circular orbit."""
    sin_i = math.sqrt(max(1.0 - (b / a_rs) ** 2, 0.0))
    chord = (1.0 + rp_rs) ** 2 - b**2
    if chord <= 0 or sin_i == 0:
        return 0.0
    return period / math.pi * math.asin(min(math.sqrt(chord) / (a_rs * sin_i), 1.0))


def t23(period: float, a_rs: float, rp_rs: float, b: float) -> float:
    """Duration of the flat part of the transit (days); 0 for grazing geometry."""
    sin_i = math.sqrt(max(1.0 - (b / a_rs) ** 2, 0.0))
    chord = (1.0 - rp_rs) ** 2 - b**2
    if chord <= 0 or sin_i == 0:
        return 0.0
    return period / math.pi * math.asin(min(math.sqrt(chord) / (a_rs * sin_i), 1.0))


def stellar_density(period: float, a_rs: float) -> float:
    """Mean stellar density (kg m^-3) implied by ``a/R*`` and the period (days)."""
    return 3.0 * math.pi * a_rs**3 / (G * (period * DAY) ** 2)


def a_rs_from_density(period: float, rho: float) -> float:
    """``a/R*`` for a period (days) and mean stellar density (kg m^-3)."""
    return (G * rho * (period * DAY) ** 2 / (3.0 * math.pi)) ** (1.0 / 3.0)


def a_rs_from_mass_radius(period: float, mass: float, radius: float) -> float:
    """``a/R*`` from Kepler's third law; mass and radius in solar units."""
    a = (G * mass * M_SUN * (period * DAY) ** 2 / (4.0 * math.pi**2)) ** (1.0 / 3.0)
    return a / (radius * R_SUN)


def density_solar(rho: float) -> float:
    """Convert kg m^-3 to solar units."""
    return rho / RHO_SUN


def q_to_u(q1: float, q2: float) -> tuple[float, float]:
    """Kipping (2013) (q1, q2) -> quadratic limb-darkening (u1, u2)."""
    sq = math.sqrt(q1)
    return 2.0 * sq * q2, sq * (1.0 - 2.0 * q2)


def u_to_q(u1: float, u2: float) -> tuple[float, float]:
    """Quadratic limb-darkening (u1, u2) -> Kipping (2013) (q1, q2)."""
    total = u1 + u2
    if total <= 0:
        return 0.0, 0.5
    return total**2, u1 / (2.0 * total)


@dataclass
class TransitParams:
    """Parameters of a transiting planet on a circular orbit."""

    t0: float
    period: float
    rp_rs: float
    a_rs: float
    b: float
    u1: float = 0.4
    u2: float = 0.2

    @property
    def inc(self) -> float:
        return inclination_deg(self.a_rs, self.b)

    @property
    def t14(self) -> float:
        return t14(self.period, self.a_rs, self.rp_rs, self.b)

    @property
    def t23(self) -> float:
        return t23(self.period, self.a_rs, self.rp_rs, self.b)


class BatmanModel:
    """A ``batman`` model bound to fixed time stamps, for repeated evaluation.

    ``batman.TransitModel`` precomputes quantities for the time array at
    construction; re-using one instance (it recomputes the sky-projected
    separation whenever t0, P, a, or i change) is much faster than building a
    new model for every likelihood call.

    For long exposures, pass ``exp_time`` (days) and ``supersample_factor`` so
    the model is integrated over each exposure (Kipping 2010).
    """

    def __init__(self, time: np.ndarray, supersample_factor: int = 1, exp_time: float = 0.0):
        import batman

        self._batman = batman
        self.time = np.asarray(time, dtype=float)
        self.params = batman.TransitParams()
        self.params.t0 = 0.0
        self.params.per = 1.0
        self.params.rp = 0.1
        self.params.a = 10.0
        self.params.inc = 90.0
        self.params.ecc = 0.0
        self.params.w = 90.0
        self.params.limb_dark = "quadratic"
        self.params.u = [0.4, 0.2]
        if self.time.size:
            self.params.t0 = float(self.time[0])
        kwargs = {}
        if supersample_factor > 1 and exp_time > 0:
            kwargs = {"supersample_factor": int(supersample_factor), "exp_time": float(exp_time)}
        self.model = batman.TransitModel(self.params, self.time, **kwargs)

    def __call__(
        self,
        t0: float,
        period: float,
        rp_rs: float,
        a_rs: float,
        inc: float,
        u1: float,
        u2: float,
    ) -> np.ndarray:
        p = self.params
        p.t0, p.per, p.rp, p.a, p.inc = t0, period, rp_rs, a_rs, inc
        p.u = [u1, u2]
        return self.model.light_curve(p)

    def from_params(self, tp: TransitParams) -> np.ndarray:
        return self(tp.t0, tp.period, tp.rp_rs, tp.a_rs, tp.inc, tp.u1, tp.u2)


def transit_model(
    time: np.ndarray,
    params: TransitParams,
    supersample_factor: int = 1,
    exp_time: float = 0.0,
) -> np.ndarray:
    """Relative flux of a single transiting planet at ``time`` (one-off evaluation)."""
    return BatmanModel(time, supersample_factor, exp_time).from_params(params)

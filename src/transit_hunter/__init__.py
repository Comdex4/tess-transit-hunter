"""tess-transit-hunter: detect, fit, and vet exoplanet transits in TESS light curves.

Modules
-------
data       download, clean, and cache SPOC 2-minute PDCSAP light curves
detrend    robust removal of stellar variability (with transit masking)
search     Box Least Squares period search, iterative multi-planet search
fit        batman + emcee transit fitting and derived planet properties
catalog    NASA Exoplanet Archive / TIC queries
inject     injection-recovery completeness tests
vet        false-positive vetting diagnostics
pipeline   end-to-end orchestration used by the ``transit-hunter`` CLI
"""

from .lightcurve import LightCurve

__version__ = "0.1.0"
__all__ = ["LightCurve", "__version__"]

"""Port Python de R/elasticity.R et compute_Rc (R/seasonal_dynamic.R)."""

import numpy as np

from .aggregation import _to_float_array


def compute_elasticity(Q, X):
    """Élasticité bivariée de Sankarasubramanian et al. (2001) :
    médiane de ((Q-Qmean)/(X-Xmean)) * Xmean/Qmean."""
    q = _to_float_array(Q)
    x = _to_float_array(X)
    q_mean = np.nanmean(q)
    x_mean = np.nanmean(x)
    with np.errstate(divide="ignore", invalid="ignore"):
        eps = (q - q_mean) / (x - x_mean) * x_mean / q_mean
    return np.nanmedian(eps)


def compute_Rc(Q, R):
    """Coefficient de ruissellement : somme(Q) / somme(R)."""
    q = _to_float_array(Q)
    r = _to_float_array(R)
    if len(q) != len(r):
        import warnings
        warnings.warn("'Q' et 'R' n'ont pas la même longueur !")
    return np.nansum(q) / np.nansum(r)

"""Port Python de R/flow_duration_curve.R (quantiles, fréquences, FDC).

compute_FDC_p / compute_FDC_Q retournent des vecteurs de longueur n
indépendante de l'entrée (sorties « ragged ») : ils sont marqués
is_ragged pour un traitement dédié dans l'extraction.
"""

from statistics import NormalDist

import numpy as np

from .aggregation import _rle_most_frequent, _to_float_array


def compute_Qp(Q, p):
    """Quantile de probabilité de dépassement p : quantile(Q, 1-p),
    interpolation linéaire (type 7 R = défaut numpy)."""
    q = _to_float_array(Q)
    q = q[~np.isnan(q)]
    p = np.asarray(p, dtype=float)
    res = np.quantile(q, 1 - p)
    return res if res.ndim else float(res)


def compute_fAp(Q, lowLim):
    """Fréquence de dépassement de lowLim : n(Q > lowLim) / N (N inclut
    les NA, comme en R)."""
    q = _to_float_array(Q)
    lim_arr = _to_float_array(lowLim) if np.ndim(lowLim) > 0 else \
        np.asarray([lowLim], dtype=float)
    lim = _rle_most_frequent(lim_arr[~np.isnan(lim_arr)])
    n = np.sum(q[~np.isnan(q)] > lim)
    return float(n) / len(q)


def fdc_slope(Q, p=(0.33, 0.66)):
    """Pente du segment médian de la courbe des débits classés."""
    p = np.asarray(p, dtype=float)
    qp = compute_Qp(Q, p)
    return -(np.log10(qp[0]) - np.log10(qp[1])) / (p[1] - p[0])


def _fdc_p(n, isNormLaw):
    if isNormLaw:
        nd = NormalDist()
        return np.array([nd.cdf(v) for v in np.linspace(-3, 3, n)])
    return np.linspace(0, 1, n)


def compute_FDC_p(n=1000, isNormLaw=False):
    return _fdc_p(n, isNormLaw)


def compute_FDC_Q(Q, n=1000, isNormLaw=False):
    return compute_Qp(Q, _fdc_p(n, isNormLaw))


compute_FDC_p.is_ragged = True
compute_FDC_Q.is_ragged = True

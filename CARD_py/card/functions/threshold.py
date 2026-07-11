"""Port Python de R/threshold.R (apply_threshold, compute_VolDef).

Les index retournés (what='first'/'last' ou fonction) sont 0-based
(R : 1-based) — cohérent avec le pipeline is_date d'EXstat_py.
"""

import operator

import numpy as np
import pandas as pd

from .aggregation import _rle_most_frequent, _to_float_array
from .aggregation import which_maxNA, which_minNA

_WHERE_OPS = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    ">=": operator.ge,
    ">": operator.gt,
}

# fonctions applicables via what="<nom>" (équivalent R get(what))
_WHAT_FUNCS = {
    "which.max": lambda x: float(np.nanargmax(x)),
    "which.min": lambda x: float(np.nanargmin(x)),
    "which.maxNA": which_maxNA,
    "which.minNA": which_minNA,
}


def _contiguous_periods(ID: np.ndarray) -> list[np.ndarray]:
    """Découpe une liste d'index croissants en runs contigus."""
    if len(ID) == 0:
        return []
    jumps = np.flatnonzero(np.diff(ID) != 1) + 1
    return np.split(ID, jumps)


def apply_threshold(X, lim, where="<=", what="X", select="all",
                    Date=None, period=None):
    X = _to_float_array(X)

    lim_arr = _to_float_array(lim) if np.ndim(lim) > 0 or isinstance(lim, pd.Series) \
        else np.asarray([lim], dtype=np.float64)
    if np.all(np.isnan(lim_arr)):
        return np.nan

    if Date is not None and period is not None:
        d = pd.to_datetime(pd.Series(Date) if not isinstance(Date, pd.Series) else Date)
        p0, p1 = pd.Timestamp(period[0]), pd.Timestamp(period[1])
        ok = (p0 <= d) & (d <= p1)
        X = X[ok.to_numpy()]

    lim_val = _rle_most_frequent(lim_arr)

    if where not in _WHERE_OPS:
        raise ValueError(f"'where' invalide : {where!r}")
    with np.errstate(invalid="ignore"):
        cond = _WHERE_OPS[where](X, lim_val)
    cond = np.where(np.isnan(X), False, cond)
    ID = np.flatnonzero(cond)

    if isinstance(select, (int, float)) and not isinstance(select, bool):
        select_val = select
        if np.isnan(select_val):
            return np.nan
    elif not isinstance(select, str):
        # vecteur : valeur la plus fréquente (rle) comme en R
        select_val = _rle_most_frequent(_to_float_array(select))
        if np.isnan(select_val):
            return np.nan
    else:
        select_val = None

    if select_val is not None or select in ("longest", "shortest"):
        periods = _contiguous_periods(ID)
        if not periods:
            return np.nan

        period_select = None
        if select_val is not None:
            for p in periods:
                if select_val in X[p]:
                    period_select = p
                    break
        elif select == "longest":
            lengths = [len(p) for p in periods]
            period_select = periods[int(np.argmax(lengths))]
        elif select == "shortest":
            lengths = [len(p) for p in periods]
            period_select = periods[int(np.argmin(lengths))]

        if period_select is None:
            return np.nan
        return _extract_what(X, period_select, what)

    elif select == "all":
        return _extract_what(X, ID, what)

    raise ValueError(f"'select' invalide : {select!r}")


def _extract_what(X: np.ndarray, idx: np.ndarray, what: str):
    if what == "X":
        return X[idx]
    if len(idx) == 0:
        return np.nan
    if what == "length":
        return float(len(idx))
    if what == "last":
        return float(idx[-1])
    if what == "first":
        return float(idx[0])
    # R : period[1] + get(what)(X[period]) - 1  (1-based)
    # Python 0-based : idx[0] + fn_0based(X[idx])
    fn = _WHAT_FUNCS.get(what)
    if fn is None:
        raise ValueError(f"'what' invalide : {what!r}")
    rel = fn(X[idx])
    if np.isnan(rel):
        return np.nan
    return float(idx[0] + rel)


def compute_VolDef(Q, upLim, select_longest=True, select=None):
    # `select` accepté et ignoré : en R, select="longest" matche
    # partiellement l'argument select_longest, qui n'est pas utilisé
    # dans le corps de la fonction (fiches vLF, allLF...)
    Qdef = apply_threshold(Q, lim=upLim, where="<=", what="X", select="longest")
    if np.ndim(Qdef) == 0 and np.isnan(Qdef):
        return np.nan
    return float(np.nansum(Qdef) * 24 * 3600 / 1e6)

"""Port Python de R/return_period.R (lois Gumbel et log-normale, get_Xn)."""

from statistics import NormalDist

import numpy as np
import pandas as pd

from .aggregation import _to_float_array

_EULER = 0.5772


def compute_GumbelParams(X):
    x = _to_float_array(X)
    b = np.sqrt(6) / np.pi * np.std(x[~np.isnan(x)], ddof=1)
    a = np.nanmean(x) - b * _EULER
    return {"a": a, "b": b}


def compute_GumbelLaw(a, b, returnPeriod):
    if returnPeriod <= 1:
        raise ValueError("returnPeriod doit être supérieur à 1")
    F_x = 1 - (1 / returnPeriod)
    u = -np.log(-np.log(F_x))
    return b * u + a


def compute_LogNormal(X, returnPeriod):
    if returnPeriod <= 1:
        raise ValueError("returnPeriod doit être supérieur à 1")
    x = _to_float_array(X)
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return np.nan
    freq = 1 / returnPeriod
    n_null = int(np.sum(x == 0))
    if (n_null / n) <= freq:
        freq = freq - (n_null / n)
        pos = np.log(x[x > 0])
        return np.exp(NormalDist().inv_cdf(freq) * np.std(pos, ddof=1)
                      + np.mean(pos))
    return 0.0


def get_Xn(X, returnPeriod, waterType="low", Date=None, period=None):
    x = _to_float_array(X)
    if Date is not None and period is not None:
        d = pd.to_datetime(pd.Series(Date) if not isinstance(Date, pd.Series)
                           else Date)
        p0, p1 = pd.Timestamp(period[0]), pd.Timestamp(period[1])
        ok = ((p0 <= d) & (d <= p1)).to_numpy()
        x = x[ok]

    if waterType == "high":
        params = compute_GumbelParams(x)
        return compute_GumbelLaw(params["a"], params["b"], returnPeriod)
    if waterType == "low":
        return compute_LogNormal(x, returnPeriod)
    raise ValueError(f"waterType invalide : {waterType!r}")

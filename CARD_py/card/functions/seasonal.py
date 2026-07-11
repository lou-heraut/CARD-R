"""Port Python de get_deltaX (R/global.R) — changements entre périodes."""

import numpy as np
import pandas as pd

from .aggregation import _to_float_array
from .baseflow import get_BFI
from .return_period import get_Xn


def _nanmean_or_nan(x):
    if len(x) == 0 or np.all(np.isnan(x)):
        return np.nan
    return np.nanmean(x)


def get_deltaX(X, Date, past, futur, to_normalise,
               returnPeriod=None, waterType="low", Q_for_BFI=None):
    x = _to_float_array(X)
    d = pd.to_datetime(pd.Series(Date) if not isinstance(Date, pd.Series) else Date)

    p0, p1 = pd.Timestamp(past[0]), pd.Timestamp(past[1])
    f0, f1 = pd.Timestamp(futur[0]), pd.Timestamp(futur[1])
    ok_past = ((p0 <= d) & (d <= p1)).to_numpy()
    ok_futur = ((f0 <= d) & (d <= f1)).to_numpy()
    x_past = x[ok_past]
    x_futur = x[ok_futur]

    if returnPeriod is not None:
        agg_past = get_Xn(x_past, returnPeriod=returnPeriod,
                          waterType=waterType)
        agg_futur = get_Xn(x_futur, returnPeriod=returnPeriod,
                           waterType=waterType)
    elif Q_for_BFI is not None:
        q = _to_float_array(Q_for_BFI)
        agg_past = get_BFI(q[ok_past], x_past)
        agg_futur = get_BFI(q[ok_futur], x_futur)
    else:
        agg_past = _nanmean_or_nan(x_past)
        agg_futur = _nanmean_or_nan(x_futur)

    if to_normalise:
        return (agg_futur - agg_past) / agg_past * 100
    return agg_futur - agg_past

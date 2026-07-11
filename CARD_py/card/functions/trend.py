"""Port Python de R/trend.R — délègue au GeneralMannKendall d'EXstat_py."""

import numpy as np

from .. import _exstat  # garantit que le chemin EXstat_py est dans sys.path
from tools import GeneralMannKendall  # noqa: E402

from .aggregation import _to_float_array

_ = _exstat  # import utilisé pour son effet de bord (sys.path)


def get_MKalpha(X, level=0.1, time_dependency_option="AR1"):
    res = GeneralMannKendall(_to_float_array(X), level=level,
                             time_dependency_option=time_dependency_option,
                             do_detrending=True)
    return res["a"]


def get_MKH(X, level=0.1, time_dependency_option="AR1"):
    res = GeneralMannKendall(_to_float_array(X), level=level,
                             time_dependency_option=time_dependency_option,
                             do_detrending=True)
    return res["H"]


def get_MKp(X, level=0.1, time_dependency_option="AR1"):
    res = GeneralMannKendall(_to_float_array(X), level=level,
                             time_dependency_option=time_dependency_option,
                             do_detrending=True)
    return res["p"]

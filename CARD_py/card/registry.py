"""Registre {nom de fonction dans les YAML CARD → callable Python}.

Les clés reprennent exactement les noms utilisés dans les fiches YAML
(donc les noms R, y compris ceux contenant un point comme which.maxNA).
"""

import numpy as np

from .functions import aggregation as agg
from .functions import (baseflow, climate, fdc, performance, return_period,
                        seasonal, threshold, trend)

FUNCTIONS = {
    # agrégations de base (np.* → chemin Cython d'EXstat_py)
    "mean": np.mean,
    "median": np.median,
    "min": np.min,
    "max": np.max,
    "sum": np.sum,
    # global.R
    "minus": agg.minus,
    "divided": agg.divided,
    "minNA": agg.minNA,
    "maxNA": agg.maxNA,
    "sumNA": agg.sumNA,
    "which.minNA": agg.which_minNA,
    "which.maxNA": agg.which_maxNA,
    "rollmean_center": agg.rollmean_center,
    "rollsum_center": agg.rollsum_center,
    "circular_minus": agg.circular_minus,
    "circular_divided": agg.circular_divided,
    "circular_median": agg.circular_median,
    "get_deltaX": seasonal.get_deltaX,
    # threshold.R
    "apply_threshold": threshold.apply_threshold,
    "compute_VolDef": threshold.compute_VolDef,
    # performance.R / rat.R
    "compute_Biais": performance.compute_Biais,
    "compute_NSE": performance.compute_NSE,
    "compute_NSElog": performance.compute_NSElog,
    "compute_NSEi": performance.compute_NSEi,
    "compute_NSEracine": performance.compute_NSEracine,
    "compute_KGE": performance.compute_KGE,
    "compute_KGEracine": performance.compute_KGEracine,
    "compute_STD": performance.compute_STD,
    "compute_RAT_X": performance.compute_RAT_X,
    # elasticity.R / seasonal_dynamic.R
    "compute_elasticity": climate.compute_elasticity,
    "compute_Rc": climate.compute_Rc,
    # return_period.R
    "get_Xn": return_period.get_Xn,
    "compute_GumbelParams": return_period.compute_GumbelParams,
    "compute_GumbelLaw": return_period.compute_GumbelLaw,
    "compute_LogNormal": return_period.compute_LogNormal,
    # flow_duration_curve.R
    "compute_Qp": fdc.compute_Qp,
    "compute_fAp": fdc.compute_fAp,
    "fdc_slope": fdc.fdc_slope,
    "compute_FDC_p": fdc.compute_FDC_p,
    "compute_FDC_Q": fdc.compute_FDC_Q,
    # baseflow.R
    "BFS": baseflow.BFS,
    "dBFS": baseflow.dBFS,
    "get_BFI": baseflow.get_BFI,
    "get_BFM": baseflow.get_BFM,
    "compute_VolSnowmelt": baseflow.compute_VolSnowmelt,
    "compute_tVolSnowmelt": baseflow.compute_tVolSnowmelt,
    "compute_tSnowmelt": baseflow.compute_tSnowmelt,
    # trend.R
    "get_MKalpha": trend.get_MKalpha,
    "get_MKH": trend.get_MKH,
    "get_MKp": trend.get_MKp,
}


def resolve(name: str):
    try:
        return FUNCTIONS[name]
    except KeyError:
        raise KeyError(
            f"Fonction CARD inconnue : '{name}'. "
            f"Fonctions disponibles : {sorted(FUNCTIONS)}"
        ) from None


def is_transform(fn) -> bool:
    """True si la fonction retourne un vecteur de même longueur que l'entrée
    (transform) et non un scalaire (agrégation)."""
    return getattr(fn, "is_transform", False)


def is_ragged(fn) -> bool:
    """True si la fonction retourne un vecteur de longueur indépendante de
    l'entrée (ex. compute_FDC_p) — nécessite un traitement dédié."""
    return getattr(fn, "is_ragged", False)

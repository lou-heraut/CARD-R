"""Port Python de R/performance.R et R/rat.R (critères de performance
obs/sim : biais, NSE, KGE, STD, RAT)."""

import numpy as np
from scipy import stats

from .aggregation import _to_float_array


def _clean_pair(obs, sim, skipna=True):
    obs = _to_float_array(obs)
    sim = _to_float_array(sim)
    if len(obs) != len(sim):
        raise ValueError("obs et sim doivent avoir la même longueur")
    if skipna:
        ok = ~(np.isnan(obs) | np.isnan(sim))
        obs, sim = obs[ok], sim[ok]
    return obs, sim


def compute_Biais(obs, sim, sim_minus_obs=True):
    obs, sim = _clean_pair(obs, sim)
    if sim_minus_obs:
        return np.sum(sim - obs) / np.sum(obs)
    return np.sum(obs - sim) / np.sum(obs)


def compute_NSE(obs, sim):
    obs, sim = _clean_pair(obs, sim)
    return 1 - np.sum((sim - obs) ** 2) / np.sum((obs - np.mean(obs)) ** 2)


def compute_hsaLog(x, method="inf.na"):
    x = _to_float_array(x).copy()
    if method == "Pushpalatha2012":
        x = x + np.nanmean(x) / 100
    elif isinstance(method, (int, float)):
        x = x + method
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.log(x)
    if method == "inf.na":
        y[~np.isfinite(y)] = np.nan
    return y


def compute_NSElog(obs, sim, log_method="inf.na"):
    obs = _to_float_array(obs)
    sim = _to_float_array(sim)
    if np.nansum(obs != 0) > 0 and np.nansum(sim != 0) > 0:
        return compute_NSE(compute_hsaLog(obs, method=log_method),
                           compute_hsaLog(sim, method=log_method))
    return 0.0


def compute_NSEi(obs, sim):
    obs = _to_float_array(obs)
    sim = _to_float_array(sim)
    if np.nansum(obs != 0) > 0 and np.nansum(sim != 0) > 0:
        with np.errstate(divide="ignore"):
            return compute_NSE(1 / obs, 1 / sim)
    return np.nan


def compute_NSEracine(obs, sim):
    return compute_NSE(np.sqrt(_to_float_array(obs)),
                       np.sqrt(_to_float_array(sim)))


def _kge_short(R, AG, BETA):
    return 1 - np.sqrt((R - 1) ** 2 + (AG - 1) ** 2 + (BETA - 1) ** 2)


def compute_KGE(obs, sim, method=1):
    obs, sim = _clean_pair(obs, sim)
    mobs, msim = np.mean(obs), np.mean(sim)
    sobs, ssim = np.std(obs, ddof=1), np.std(sim, ddof=1)
    rso = np.corrcoef(sim, obs)[0, 1]
    beta = msim / mobs
    if method == 2:
        gamma = (ssim / msim) / (sobs / mobs)
        return _kge_short(rso, gamma, beta)
    return _kge_short(rso, ssim / sobs, beta)


def compute_KGEracine(obs, sim):
    return compute_KGE(np.sqrt(_to_float_array(obs)),
                       np.sqrt(_to_float_array(sim)))


def compute_STD(obs, sim):
    obs = _to_float_array(obs)
    sim = _to_float_array(sim)
    sd_obs = np.std(obs[~np.isnan(obs)], ddof=1)
    sd_sim = np.std(sim[~np.isnan(sim)], ddof=1)
    return sd_sim / sd_obs


def compute_RAT_X(Bias, X, thresh=0.05):
    """RAT (Nicolle et al. 2020) : corrélation de Spearman significative entre
    un critère de performance et une variable explicative → manque de
    robustesse. p-value asymptotique (equiv. R cor.test exact=FALSE)."""
    b = _to_float_array(Bias)
    x = _to_float_array(X)
    ok = ~(np.isnan(b) | np.isnan(x))
    if ok.sum() <= 2:
        return np.nan
    p = stats.spearmanr(b[ok], x[ok]).pvalue
    return bool(p < thresh)

"""Génère un jeu de données journalier synthétique pour la validation croisée
R vs Python (2 stations, 1970-2100 pour couvrir les horizons H0-H3).

Colonnes : date, id, Q, Q_obs, Q_sim, R, Rl, Rs, R_obs, R_sim, T, T_obs,
ETP, ET0_obs — l'ensemble des input_vars utilisés par les fiches CARD.
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "data" / "test_data.csv"


def make_station(dates, rng, phase_shift=0.0, trend=0.0, scale=20.0):
    doy = dates.dayofyear.to_numpy()
    years = dates.year.to_numpy()
    # hautes eaux en hiver, basses eaux en été (régime pluvial)
    seasonal = scale * (1 + 0.8 * np.sin(2 * np.pi * (doy - 120 + phase_shift) / 365.25))
    noise = np.exp(rng.normal(0, 0.25, len(dates)))
    drift = 1 + trend * (years - 1970)
    return seasonal * noise * drift


def main():
    rng = np.random.default_rng(42)
    dates = pd.date_range("1970-01-01", "2100-12-31", freq="D")
    n = len(dates)
    doy = dates.dayofyear.to_numpy()
    years = dates.year.to_numpy()

    frames = []
    for sid, (phase, trend) in {"S001": (0.0, -0.002),
                                "S002": (40.0, -0.001)}.items():
        q = make_station(dates, rng, phase_shift=phase, trend=trend)

        # obs/sim : Q_obs = Q ; Q_sim = biais léger + bruit
        q_sim = q * (1 + 0.05) * np.exp(rng.normal(0, 0.1, n))

        # températures : cycle saisonnier + réchauffement
        t = (12 + 9 * np.sin(2 * np.pi * (doy - 200 + phase) / 365.25)
             + rng.normal(0, 2.5, n) + 0.02 * (years - 1970))

        # précipitations : jours secs + gamma
        wet = rng.random(n) < 0.4
        r = np.where(wet, rng.gamma(0.7, 8.0, n), 0.0)
        r_sim = r * np.exp(rng.normal(0, 0.15, n))
        rs = np.where(t < 0, r, 0.0)   # solide quand T < 0
        rl = r - rs

        # évapotranspiration de référence
        etp = np.clip(2.5 + 2.2 * np.sin(2 * np.pi * (doy - 200) / 365.25)
                      + rng.normal(0, 0.4, n), 0, None)

        frames.append(pd.DataFrame({
            "date": dates, "id": sid,
            "Q": q, "Q_obs": q, "Q_sim": q_sim,
            "R": r, "Rl": rl, "Rs": rs, "R_obs": r, "R_sim": r_sim,
            "T": t, "T_obs": t,
            "ETP": etp, "ET0_obs": etp,
        }))
    data = pd.concat(frames, ignore_index=True)

    # lacunes : une courte (~1.4 % de l'année, sous NApct_lim=3) et une
    # longue (~8 %, au-dessus) pour tester le filtrage des deux côtés
    short_gap = (data["id"] == "S001") & \
        (data["date"].between("1985-03-10", "1985-03-14"))
    long_gap = (data["id"] == "S002") & \
        (data["date"].between("1990-05-01", "1990-05-30"))
    value_cols = [c for c in data.columns if c not in ("date", "id")]
    data.loc[short_gap | long_gap, value_cols] = np.nan

    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUT, index=False)
    print(f"{OUT} : {len(data)} lignes, {data['id'].nunique()} stations, "
          f"{len(value_cols)} colonnes de valeurs")


if __name__ == "__main__":
    main()

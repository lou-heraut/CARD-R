"""Validation croisée : exécute CARD_py sur les YAML de référence et compare
aux sorties du package R CARD (tests/data/R_out/).

Convention d'index : les variables de type date (is_date) sont 0-based côté
Python (np.argmax) et 1-based côté R (which.max) → comparaison avec +1.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from card import CARD_extraction  # noqa: E402

TESTS = Path(__file__).parent
REPO = TESTS.parent.parent
R_OUT = TESTS / "data" / "R_out"

RTOL = 1e-8
ATOL = 1e-10

FAILURES = []


def check(label, ok, detail=""):
    status = "OK " if ok else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def _to_float(vals):
    return pd.Series(vals).astype("Float64").to_numpy(dtype=float, na_value=np.nan)


def compare_series(label, r_vals, py_vals, offset=0.0):
    r = _to_float(r_vals)
    p = _to_float(py_vals) + offset
    if len(r) != len(p):
        check(label, False, f"longueurs différentes R={len(r)} py={len(p)}")
        return
    na_match = np.array_equal(np.isnan(r), np.isnan(p))
    both = ~np.isnan(r) & ~np.isnan(p)
    close = np.allclose(r[both], p[both], rtol=RTOL, atol=ATOL)
    if na_match and close:
        n = int(both.sum())
        check(label, True, f"{n} valeurs identiques (tol {RTOL})")
    else:
        diff = np.abs(r[both] - p[both])
        detail = (f"NA divergents" if not na_match
                  else f"max |diff| = {np.nanmax(diff):.3e}")
        idx = np.flatnonzero(~np.isclose(r, p, rtol=RTOL, atol=ATOL, equal_nan=True))[:5]
        check(label, False, f"{detail} ; premiers index divergents {idx.tolist()}")


def align_yearly(r_df, py_df, r_col, py_col):
    """Aligne R (id, date) et Python (id, Date) sur (id, année)."""
    r = r_df.copy()
    r["_y"] = pd.to_datetime(r["date"]).dt.year
    p = py_df.copy()
    date_col = "Date" if "Date" in p.columns else "date"
    p["_y"] = pd.to_datetime(p[date_col]).dt.year
    m = r[["id", "_y", r_col]].merge(
        p[["id", "_y", py_col]], on=["id", "_y"], how="outer",
        suffixes=("_R", "_py"),
    )
    c_r = r_col if r_col != py_col else f"{r_col}_R"
    c_p = py_col if r_col != py_col else f"{py_col}_py"
    return m[c_r], m[c_p], m


def main():
    data = pd.read_csv(TESTS / "data" / "test_data.csv", parse_dates=["date"])

    res = CARD_extraction(
        data,
        CARD_name=["QA", "median-QJC5", "tQJXA", "dtLF", "delta-endLF_H"],
        CARD_path=REPO / "dev" / "yaml_ref",
        verbose=False,
    )
    dataEX = res["dataEX"]

    # ── QA ──────────────────────────────────────────────────────────────
    print("\nQA")
    r = pd.read_csv(R_OUT / "QA.csv")
    r_v, p_v, _ = align_yearly(r, dataEX["QA"], "QA", "QA")
    compare_series("QA (moyenne annuelle)", r_v, p_v)

    # ── median-QJC5 ─────────────────────────────────────────────────────
    print("\nmedian-QJC5")
    r = pd.read_csv(R_OUT / "median-QJC5.csv")
    p = dataEX["median-QJC5"]
    m = r[["id", "Yearday", "median-QJ", "median-QJC5"]].merge(
        p[["id", "Yearday", "median-QJ", "median-QJC5"]],
        on=["id", "Yearday"], suffixes=("_R", "_py"), how="outer",
    )
    compare_series("median-QJ (médiane par yearday)",
                   m["median-QJ_R"], m["median-QJ_py"])
    compare_series("median-QJC5 (rollmean cyclique k=5)",
                   m["median-QJC5_R"], m["median-QJC5_py"])

    # ── tQJXA (is_date : fonctions 0-based + conversion EXstat_py
    #    reproduisent exactement les valeurs R — vérifié empiriquement) ──
    print("\ntQJXA")
    r = pd.read_csv(R_OUT / "tQJXA.csv")
    r_v, p_v, _ = align_yearly(r, dataEX["tQJXA"], "tQJXA", "tQJXA")
    compare_series("tQJXA (date du max annuel)", r_v, p_v)

    # ── dtLF ────────────────────────────────────────────────────────────
    print("\ndtLF")
    r = pd.read_csv(R_OUT / "dtLF.csv")
    r_v, p_v, _ = align_yearly(r, dataEX["dtLF"], "dtLF", "dtLF")
    compare_series("dtLF (durée des basses eaux)", r_v, p_v)

    # ── delta-endLF_H ───────────────────────────────────────────────────
    print("\ndelta-endLF_H")
    r = pd.read_csv(R_OUT / "delta-endLF_H1__delta-endLF_H2__delta-endLF_H3.csv")
    p = dataEX["delta-endLF_H"]
    m = r.merge(p, on="id", suffixes=("_R", "_py"), how="outer")
    for h in ("H1", "H2", "H3"):
        col = f"delta-endLF_{h}"
        compare_series(f"{col} (delta de dates, offsets annulés)",
                       m[f"{col}_R"], m[f"{col}_py"])

    print()
    if FAILURES:
        print(f"✗ {len(FAILURES)} comparaison(s) en échec")
        sys.exit(1)
    print("✓ Les 5 fiches de référence sont validées R ↔ Python")


if __name__ == "__main__":
    main()

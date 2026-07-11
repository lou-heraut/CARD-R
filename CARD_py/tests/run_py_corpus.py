"""Validation croisée corpus complet : exécute chaque fiche YAML via CARD_py
et compare aux sorties R (tests/data/R_corpus/).

Produit tests/data/corpus_report.csv avec une ligne par (fiche, variable) :
    status ∈ ok | ok_approx | diff | py_error | r_error | r_missing | empty
et imprime une synthèse par statut.

Comparaison générique :
- jointure sur id (+ date exacte si présente des deux côtés) ;
- colonnes numériques communes comparées à tolérance relative 1e-6 ;
- ok_approx : ≥ 95 %% des valeurs identiques (divergences de bord attendues,
  ex. convention rolling pandas vs RcppRoll pour k pair).
"""

import sys
import traceback
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
warnings.filterwarnings("ignore")

from card import CARD_extraction  # noqa: E402
from card.loader import load_card  # noqa: E402

TESTS = Path(__file__).parent
REPO = TESTS.parent.parent
R_ROOT = TESTS / "data" / "R_corpus"
CARD_YML = REPO / "CARD_yml"

RTOL = 1e-6
ATOL = 1e-9


def to_float(s):
    return pd.Series(s).astype("Float64").to_numpy(dtype=float, na_value=np.nan)


def find_yaml_cards():
    cards = {}
    for p in sorted(CARD_YML.rglob("*.yaml")):
        cards[p.stem] = p
    return cards


def compare_frames(r_df, p_df, id_col="id"):
    """Compare toutes les colonnes numériques communes. Retourne une liste
    de dicts (variable, n_common, n_equal, max_diff, status)."""
    p_df = p_df.copy()
    r_df = r_df.copy()

    # harmonise les noms de colonne date
    r_date = next((c for c in r_df.columns if c.lower() == "date"), None)
    p_date = next((c for c in p_df.columns if c.lower() == "date"), None)
    keys = [id_col]
    if r_date and p_date:
        r_df["_date"] = pd.to_datetime(r_df[r_date])
        p_df["_date"] = pd.to_datetime(p_df[p_date])
        keys.append("_date")

    num_r = {c for c in r_df.columns
             if c not in (id_col, r_date, "_date")
             and pd.api.types.is_numeric_dtype(pd.Series(to_float(r_df[c])))}
    num_p = set(p_df.columns) - {id_col, p_date, "_date"}
    common = sorted(num_r & num_p)
    if not common:
        return [{"variable": "", "n_common": 0, "n_equal": 0,
                 "max_diff": np.nan, "status": "no_common_cols"}]

    # doublons de clés (ex. sorties ragged sans date) → alignement par rang
    if (r_df.duplicated(keys).any() or p_df.duplicated(keys).any()):
        r_df["_rank"] = r_df.groupby(keys, observed=True).cumcount()
        p_df["_rank"] = p_df.groupby(keys, observed=True).cumcount()
        keys = keys + ["_rank"]

    m = r_df[keys + common].merge(p_df[keys + list(common)], on=keys,
                                  how="outer", suffixes=("_R", "_P"))
    out = []
    for c in common:
        rv = to_float(m[f"{c}_R"])
        pv = to_float(m[f"{c}_P"])
        both = ~np.isnan(rv) & ~np.isnan(pv)
        na_mismatch = int((np.isnan(rv) != np.isnan(pv)).sum())
        n_common = int(both.sum())
        if n_common == 0 and na_mismatch == 0:
            out.append({"variable": c, "n_common": 0, "n_equal": 0,
                        "max_diff": np.nan, "status": "empty"})
            continue
        eq = np.isclose(rv[both], pv[both], rtol=RTOL, atol=ATOL)
        n_eq = int(eq.sum())
        max_diff = float(np.max(np.abs(rv[both] - pv[both]))) if n_common else np.nan
        frac = (n_eq / (n_common + na_mismatch)) if (n_common + na_mismatch) else 0
        if frac == 1.0:
            status = "ok"
        elif frac >= 0.95:
            status = "ok_approx"
        else:
            status = "diff"
        out.append({"variable": c, "n_common": n_common, "n_equal": n_eq,
                    "max_diff": max_diff, "status": status})
    return out


def main(only=None):
    data = pd.read_csv(TESTS / "data" / "test_data.csv", parse_dates=["date"])
    r_status = pd.read_csv(R_ROOT / "_status.csv").set_index("card")
    yaml_cards = find_yaml_cards()

    rows = []
    names = sorted(yaml_cards) if only is None else only
    for name in names:
        r_ok = name in r_status.index and r_status.loc[name, "status"] == "ok"
        r_dir = R_ROOT / name

        try:
            res = CARD_extraction(data, CARD_name=[name],
                                  CARD_path=yaml_cards[name].parent)
            p_df = res["dataEX"][name]
            py_status = "ok"
        except Exception as e:
            p_df = None
            py_status = f"py_error: {type(e).__name__}: {e}"

        if not r_ok:
            msg = r_status.loc[name, "message"] if name in r_status.index else "absent"
            rows.append({"card": name, "variable": "", "status": "r_error",
                         "detail": str(msg)[:120]})
            continue
        if p_df is None:
            rows.append({"card": name, "variable": "", "status": "py_error",
                         "detail": py_status[:200]})
            traceback.print_exc()
            continue

        r_files = sorted(r_dir.glob("*.csv"))
        if not r_files:
            rows.append({"card": name, "variable": "", "status": "r_missing",
                         "detail": ""})
            continue
        r_df = pd.concat([pd.read_csv(f) for f in r_files], axis=0) \
            if len(r_files) > 1 and all(
                set(pd.read_csv(f, nrows=0).columns)
                == set(pd.read_csv(r_files[0], nrows=0).columns)
                for f in r_files) else pd.read_csv(r_files[0])
        if len(r_files) > 1 and len(r_df) == len(pd.read_csv(r_files[0])):
            # fichiers hétérogènes : fusion sur colonnes communes id/date
            r_df = pd.read_csv(r_files[0])
            for f in r_files[1:]:
                other = pd.read_csv(f)
                on = [c for c in ("id", "date") if
                      c in r_df.columns and c in other.columns]
                r_df = r_df.merge(other, on=on, how="outer")

        for cmp_row in compare_frames(r_df, p_df):
            rows.append({"card": name, **cmp_row,
                         "detail": ""})
        print(f"[done] {name}")

    report = pd.DataFrame(rows)
    report.to_csv(TESTS / "data" / "corpus_report.csv", index=False)

    print("\n=== Synthèse ===")
    print(report["status"].value_counts().to_string())
    bad = report[report["status"].isin(["diff", "py_error", "no_common_cols"])]
    if len(bad):
        print("\n=== À investiguer ===")
        print(bad.to_string(index=False, max_colwidth=80))


if __name__ == "__main__":
    only = sys.argv[1:] or None
    main(only)

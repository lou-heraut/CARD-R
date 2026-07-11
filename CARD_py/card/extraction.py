"""CARD_extraction — port Python de R/CARD_process.R, basé sur les fiches YAML.

Chaque fiche est une chaîne de processus P1..Pn ; chaque processus est exécuté
par process_extraction (EXstat_py), sauf deux cas gérés ici car absents du
port EXstat_py :

1. sampling_period adaptatif ({type: adaptive}) : le mois de début de l'année
   hydrologique est calculé par station (mois du max/min des moyennes
   mensuelles inter-annuelles), comme fix_sampling_period() en R.
2. transforms (rollmean_center, ...) en time_step 'none' : sortie vectorielle
   de même longueur que l'entrée, assignée comme nouvelle colonne.

Les kwargs dont la valeur est un nom de colonne des données courantes
(ex. {lim: upLim}) sont résolus dynamiquement en colonnes, comme le fait
process_extraction() en R avec funct_args.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

from ._exstat import process_extraction
from process_extraction import _apply_nayear_lim
from .loader import load_card
from .registry import is_ragged, is_transform, resolve

_DEFAULT_CARD_DIR = Path(__file__).resolve().parent.parent.parent / "CARD_yml"


# ---------------------------------------------------------------------------
# Détection de colonnes
# ---------------------------------------------------------------------------

def _detect_cols(data: pd.DataFrame):
    date_col, id_col = None, None
    for col in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[col]) and date_col is None:
            date_col = col
        elif (data[col].dtype == object
              or isinstance(data[col].dtype, pd.CategoricalDtype)
              or pd.api.types.is_string_dtype(data[col])) and id_col is None:
            id_col = col
    return date_col, id_col


def _resolve_col(col: str, data: pd.DataFrame, date_col: str | None) -> str:
    if col in data.columns:
        return col
    if date_col is not None and col.lower() == date_col.lower():
        return date_col
    raise KeyError(
        f"Colonne '{col}' introuvable. Colonnes disponibles : {list(data.columns)}"
    )


# ---------------------------------------------------------------------------
# kwargs référencant des colonnes → colonnes positionnelles + wrapper
# ---------------------------------------------------------------------------

def _build_funct_tuple(entry: dict, data: pd.DataFrame, date_col: str | None):
    """FunctEntry (loader) → tuple (fn, *cols, kwargs, is_date) pour EXstat_py.

    EXstat_py ne passe que des colonnes en positionnel : les littéraux
    positionnels (ex. [divided, "dQXA", 2, ...]) et les kwargs référencant
    des colonnes (ex. {lim: upLim}) sont réinjectés par un wrapper.
    """
    pos_args = [("col", _resolve_col(v, data, date_col)) if t == "col"
                else ("lit", v)
                for t, v in entry["pos_args"]]
    cols = [v for t, v in pos_args if t == "col"]
    has_literals = any(t == "lit" for t, _ in pos_args)
    kwargs = dict(entry["kwargs"])

    # comme en R : tout kwarg str qui correspond à un nom de colonne des
    # données courantes est remplacé par la colonne ("longest", "length",
    # "<=", etc. ne matchent jamais) ; la colonne date matche insensible
    # à la casse (ex. Date: "date" → colonne "Date" d'EXstat_py)
    ref_names, ref_cols = [], []
    for k, v in list(kwargs.items()):
        if not isinstance(v, str):
            continue
        if v in data.columns:
            target = v
        elif date_col is not None and v.lower() == date_col.lower():
            target = date_col
        else:
            continue
        ref_names.append(k)
        ref_cols.append(target)
        del kwargs[k]

    fn = resolve(entry["fn_name"])
    if ref_names or has_literals:
        n_cols = len(cols)

        def wrapped(*args, _fn=fn, _pos=pos_args, _n=n_cols,
                    _refs=tuple(ref_names), **kw):
            series = iter(args[:_n])
            full = [next(series) if t == "col" else v for t, v in _pos]
            kw = {**kw, **dict(zip(_refs, args[_n:]))}
            return _fn(*full, **kw)

        fn = wrapped
        cols = cols + ref_cols

    t = [fn] + cols
    if kwargs:
        t.append(kwargs)
    if entry["is_date"]:
        t.append(True)
    return tuple(t)


# ---------------------------------------------------------------------------
# sampling_period adaptatif (équivalent fix_sampling_period en R)
# ---------------------------------------------------------------------------

def _adaptive_start(gdata: pd.DataFrame, sp_entry: dict, date_col: str) -> str:
    """Mois de début 'MM-01' pour une station : mois où la moyenne mensuelle
    inter-annuelle de la colonne atteint fn (max ou min). Défaut '09-01'."""
    col = sp_entry["cols"][0]
    monthly = gdata.groupby(gdata[date_col].dt.month)[col].mean()
    monthly = monthly.dropna()
    if len(monthly) == 0:
        return "09-01"
    fn = resolve(sp_entry["fn_name"])
    target = fn(monthly.to_numpy())
    matches = monthly.index[monthly == target]
    if len(matches) == 0:
        return "09-01"
    return f"{int(matches[0]):02d}-01"


def _sampling_periods_by_station(data, sp, id_col, date_col) -> dict:
    """Retourne {id: sampling_period} — constant si sp est fixe."""
    ids = data[id_col].unique()
    if isinstance(sp, dict) and sp.get("type") == "adaptive":
        entry = sp["funct"]
        col = _resolve_col(entry["cols"][0], data, date_col)
        entry = {**entry, "cols": [col]}
        return {
            i: _adaptive_start(data[data[id_col] == i], entry, date_col)
            for i in ids
        }
    return {i: sp for i in ids}


# ---------------------------------------------------------------------------
# Transforms (time_step 'none', sortie vectorielle)
# ---------------------------------------------------------------------------

def _run_transform(data, proc, id_col, date_col):
    if proc["time_step"] != "none":
        raise ValueError(
            f"{proc['name']} : une fonction transform "
            f"({proc['funct'][0]['fn_name']}) nécessite time_step 'none'."
        )
    sort_cols = [id_col] + ([date_col] if date_col else [])
    out = data.sort_values(sort_cols).reset_index(drop=True)

    new_names = []
    for entry in proc["funct"]:
        fn = resolve(entry["fn_name"])
        cols = [_resolve_col(c, out, date_col) for c in entry["cols"]]
        kwargs = {k: v for k, v in entry["kwargs"].items() if k != "skipna"}
        new = pd.Series(np.nan, index=out.index)
        for _, g in out.groupby(id_col, sort=False, observed=True):
            new.loc[g.index] = fn(*[g[c] for c in cols], **kwargs)
        out[entry["name"]] = new
        new_names.append(entry["name"])

    if proc["keep"] == "all":
        return out
    keep_cols = [id_col] + ([date_col] if date_col else []) + new_names
    return out[keep_cols]


def _run_ragged(data, proc, id_col, date_col):
    """Fonctions à sortie de longueur indépendante de l'entrée
    (ex. compute_FDC_p/Q, n=1000) : une ligne par élément du vecteur
    résultat, par station."""
    if proc["time_step"] != "none":
        raise ValueError(
            f"{proc['name']} : une fonction ragged nécessite time_step 'none'."
        )
    sort_cols = [id_col] + ([date_col] if date_col else [])
    data = data.sort_values(sort_cols)

    parts = []
    for gid, g in data.groupby(id_col, sort=False, observed=True):
        values = {}
        length = None
        for entry in proc["funct"]:
            fn = resolve(entry["fn_name"])
            cols = [_resolve_col(c, data, date_col) for c in entry["cols"]]
            kwargs = {k: v for k, v in entry["kwargs"].items()
                      if k != "skipna"}
            v = np.asarray(fn(*[g[c] for c in cols], **kwargs))
            if length is None:
                length = len(v)
            elif len(v) != length:
                raise ValueError(
                    f"{proc['name']} : longueurs de sortie incohérentes "
                    f"entre les fonctions ragged ({length} vs {len(v)})."
                )
            values[entry["name"]] = v
        part = pd.DataFrame({id_col: gid, **values})
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------------------
# Exécution d'un processus
# ---------------------------------------------------------------------------

def _used_columns(proc) -> set:
    """Colonnes de données référencées par les functs et le sampling adaptatif."""
    used = set()
    for e in proc["funct"]:
        used.update(v for t, v in e["pos_args"] if t == "col")
        used.update(v for v in e["kwargs"].values() if isinstance(v, str))
    sp = proc["sampling_period"]
    if isinstance(sp, dict):
        used.update(sp["funct"]["cols"])
    return used


def _run_process(data, proc, period_default=None, cancel_lim=False,
                 verbose=False, sparse_cols=frozenset()):
    """Exécute un processus. Retourne (result, sparse_cols_du_résultat).

    sparse_cols : colonnes issues d'un fan-out keep='all' du processus
    précédent (valeur sur la première ligne de chaque groupe, NaN ailleurs).
    En R ces NaN de construction ne comptent pas comme lacunes
    (is.na_not_nan) ; côté pandas on compacte les lignes creuses quand le
    processus n'utilise QUE des colonnes creuses — le dénominateur
    calendaire d'EXstat_py (n_expected) détecte alors correctement les
    périodes réellement manquantes.
    """
    date_col, id_col = _detect_cols(data)
    if id_col is None:
        data = data.copy()
        data["id"] = "time serie"
        id_col = "id"

    used = _used_columns(proc)
    used_values = {u for u in used
                   if not (date_col is not None
                           and u.lower() == date_col.lower())}
    used_sparse = used_values & set(sparse_cols)
    if (used_sparse and used_values <= set(sparse_cols)
            and proc["keep"] != "all"):
        data = data.dropna(subset=list(used_sparse), how="all")

    period = proc["period"] if proc["period"] is not None else period_default
    NApct_lim = None if cancel_lim else proc["NApct_lim"]
    NAyear_lim = None if cancel_lim else proc["NAyear_lim"]

    fns = [resolve(e["fn_name"]) for e in proc["funct"]]
    transforms = [is_transform(f) for f in fns]
    raggeds = [is_ragged(f) for f in fns]
    if any(transforms) or any(raggeds):
        if not (all(transforms) or all(raggeds)):
            raise ValueError(
                f"{proc['name']} : mélange de transforms/ragged et "
                "d'agrégations non supporté."
            )
        # pré-traitements normalement faits par process_extraction
        if period is not None and date_col is not None:
            p0, p1 = pd.Timestamp(period[0]), pd.Timestamp(period[1])
            data = data[(data[date_col] >= p0) & (data[date_col] <= p1)]
        if NAyear_lim is not None and date_col is not None:
            value_cols = [c for c in data.columns
                          if pd.api.types.is_numeric_dtype(data[c])]
            data = _apply_nayear_lim(data, id_col, date_col,
                                     value_cols, NAyear_lim)
        carried = frozenset(sparse_cols) if proc["keep"] == "all" \
            else frozenset()
        if all(transforms):
            return _run_transform(data, proc, id_col, date_col), carried
        return _run_ragged(data, proc, id_col, date_col), carried

    funct = {e["name"]: _build_funct_tuple(e, data, date_col)
             for e in proc["funct"]}

    common = dict(
        funct=funct,
        time_step=proc["time_step"],
        period=period,
        NApct_lim=NApct_lim,
        NAyear_lim=NAyear_lim,
        Seasons=proc["Seasons"],
        keep=proc["keep"],
        compress=proc["compress"],
        expand=proc["expand"],
        verbose=verbose,
    )

    # colonnes creuses du résultat : fan-out keep='all' sur un time_step
    # groupé (year, year-month, year-season) — pour time_step 'none' la
    # valeur est diffusée sur toutes les lignes (dense)
    if proc["keep"] == "all":
        out_sparse = set(sparse_cols)
        if proc["time_step"] != "none":
            out_sparse |= {e["name"] for e in proc["funct"]}
        out_sparse = frozenset(out_sparse)
    else:
        out_sparse = frozenset()

    sp = proc["sampling_period"]
    if isinstance(sp, dict):
        # adaptatif : sampling_period par station → un appel par valeur de sp
        sp_map = _sampling_periods_by_station(data, sp, id_col, date_col)
        groups: dict[str, list] = {}
        for i, s in sp_map.items():
            groups.setdefault(s, []).append(i)
        parts = []
        for s, ids in groups.items():
            subset = data[data[id_col].isin(ids)].copy()
            if isinstance(subset[id_col].dtype, pd.CategoricalDtype):
                # les catégories inutilisées créeraient des groupes NaN
                # fantômes dans le groupby d'EXstat_py (observed=False)
                subset[id_col] = subset[id_col].cat.remove_unused_categories()
            parts.append(process_extraction(subset, sampling_period=s, **common))
        result = pd.concat(parts, ignore_index=True)
        sort_cols = [c for c in (id_col, "Date", date_col) if c in result.columns]
        if sort_cols:
            result = result.sort_values(sort_cols[:2]).reset_index(drop=True)
        return result, out_sparse

    return process_extraction(data, sampling_period=sp, **common), out_sparse


# ---------------------------------------------------------------------------
# metaEX
# ---------------------------------------------------------------------------

def _as_list(x, n):
    if isinstance(x, list):
        if len(x) != n:
            return [x] * n if n > 1 and not isinstance(x[0], (str, int, float, bool)) else (x + [x[-1]] * (n - len(x)))[:n]
        return x
    return [x] * n


def _join_sp(sp):
    if isinstance(sp, list):
        if sp and isinstance(sp[0], list):
            return [", ".join(s) for s in sp]
        return ", ".join(sp)
    return sp


def _meta_rows(card) -> pd.DataFrame:
    en, fr, gl = card["meta"]["en"], card["meta"]["fr"], card["meta"]["global"]

    variable_en = en.get("variable")
    n = len(variable_en) if isinstance(variable_en, list) else 1

    def field(d, key):
        return _as_list(d.get(key, ""), n)

    sp_en = _join_sp(en.get("sampling_period"))
    sp_fr = _join_sp(fr.get("sampling_period"))

    palette = gl.get("palette")
    if isinstance(palette, list) and palette and isinstance(palette[0], list):
        palette = [" ".join(p) for p in palette]
    elif isinstance(palette, list):
        palette = " ".join(palette)

    return pd.DataFrame({
        "variable_en": _as_list(variable_en, n),
        "unit_en": field(en, "unit"),
        "name_en": field(en, "name"),
        "description_en": field(en, "description"),
        "method_en": field(en, "method"),
        "sampling_period_en": _as_list(sp_en, n),
        "topic_en": field(en, "topic"),
        "variable_fr": _as_list(fr.get("variable"), n),
        "unit_fr": field(fr, "unit"),
        "name_fr": field(fr, "name"),
        "description_fr": field(fr, "description"),
        "method_fr": field(fr, "method"),
        "sampling_period_fr": _as_list(sp_fr, n),
        "topic_fr": field(fr, "topic"),
        "is_experimental": _as_list(gl.get("is_experimental"), n),
        "input_vars": _as_list(gl.get("input_vars"), n),
        "source": _as_list(gl.get("source"), n),
        "preferred_sampling_period": _as_list(gl.get("preferred_sampling_period"), n),
        "is_date": _as_list(gl.get("is_date"), n),
        "to_normalise": _as_list(gl.get("to_normalise"), n),
        "palette": _as_list(palette, n),
        "script_path": [card["path"]] * n,
    })


# ---------------------------------------------------------------------------
# API principale
# ---------------------------------------------------------------------------

def _find_cards(CARD_path, CARD_name):
    root = Path(CARD_path)
    found = {}
    for p in sorted(root.rglob("*.yaml")):
        stem = p.stem
        # préfixe numérique optionnel '001_' posé par CARD_management
        if "_" in stem and stem.split("_", 1)[0].isdigit():
            stem = stem.split("_", 1)[1]
        found.setdefault(stem, p)
    if CARD_name is None:
        return found
    missing = [n for n in CARD_name if n not in found]
    if missing:
        raise FileNotFoundError(
            f"CARD introuvables sous {root} : {missing}"
        )
    return {n: found[n] for n in CARD_name}


def CARD_extraction(data, CARD_name=("QA", "QJXA"), CARD_path=None,
                    period_default=None, cancel_lim=False,
                    simplify=False, extract_only_metadata=False,
                    verbose=False):
    """Extrait des variables hydroclimatiques selon des fiches CARD YAML.

    data : DataFrame avec une colonne datetime, une colonne str (id) et
           les colonnes numériques d'entrée requises par les fiches.
    Retourne {"metaEX": DataFrame, "dataEX": {card_id: DataFrame}}.
    """
    if CARD_path is None:
        CARD_path = os.environ.get("CARD_YML_PATH", _DEFAULT_CARD_DIR)

    cards = _find_cards(CARD_path, list(CARD_name) if CARD_name else None)

    metaEX_parts, dataEX = [], {}
    for name, path in cards.items():
        card = load_card(path)
        metaEX_parts.append(_meta_rows(card))
        if extract_only_metadata:
            continue
        if verbose:
            print(f"Computes {name}")
        result = data
        sparse = frozenset()
        for proc in card["processes"]:
            result, sparse = _run_process(result, proc,
                                          period_default=period_default,
                                          cancel_lim=cancel_lim,
                                          verbose=verbose,
                                          sparse_cols=sparse)
        dataEX[name] = result

    metaEX = pd.concat(metaEX_parts, ignore_index=True) if metaEX_parts \
        else pd.DataFrame()

    if extract_only_metadata:
        return {"metaEX": metaEX}

    if simplify and dataEX:
        dfs = list(dataEX.values())
        merged = dfs[0]
        for df in dfs[1:]:
            by = [c for c in merged.columns
                  if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])]
            merged = merged.merge(df, on=by, how="outer")
        return {"metaEX": metaEX, "dataEX": merged}

    return {"metaEX": metaEX, "dataEX": dataEX}

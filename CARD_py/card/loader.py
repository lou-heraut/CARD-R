"""Lecture des fiches CARD YAML — remplace sourceProcess() du package R.

Une fiche chargée est un dict :
    {
      "id": str,
      "meta": {"en": {...}, "fr": {...}, "global": {...}},   # défauts appliqués
      "processes": [                                          # P1..Pn ordonnés
          {
            "name": "P1",
            "funct": [FunctEntry, ...],
            "time_step": str, "sampling_period": ..., "period": ...,
            "NApct_lim": ..., "NAyear_lim": ..., "Seasons": [...],
            "keep": ..., "compress": bool, "expand": bool,
          },
      ],
    }

FunctEntry (dict) : {name, fn_name, fn, cols, kwargs, is_date}
Les symboles $H0..$Hn sont substitués par les dates de meta.global.horizons.
Le sampling_period adaptatif {type: adaptive, funct: [...]} est parsé de la
même façon qu'un tuple funct.
"""

import re

import yaml

_GLOBAL_DEFAULTS = {
    "is_experimental": False,
    "input_vars": "X",
    "source": None,
    "preferred_sampling_period": None,
    "is_date": False,
    "to_normalise": True,
    "palette": None,
}

_PROCESS_DEFAULTS = {
    "time_step": "year",
    "sampling_period": None,
    "period": None,
    "NApct_lim": None,
    "NAyear_lim": None,
    "Seasons": ["DJF", "MAM", "JJA", "SON"],
    "keep": None,
    "compress": False,
    "expand": False,
}

_HORIZON_RE = re.compile(r"^\$(H\d+)$")


def _substitute_horizons(value, horizons):
    """Remplace récursivement les symboles '$Hx' par les dates des horizons."""
    if isinstance(value, str):
        m = _HORIZON_RE.match(value)
        if m:
            key = m.group(1)
            if not horizons or key not in horizons:
                raise ValueError(
                    f"Symbole '{value}' sans horizon correspondant dans "
                    "meta.global.horizons."
                )
            return horizons[key]
        return value
    if isinstance(value, dict):
        return {k: _substitute_horizons(v, horizons) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_horizons(v, horizons) for v in value]
    return value


def _parse_funct_tuple(name, raw, horizons):
    """Parse [fn_name, *cols, kwargs?, is_date?] en FunctEntry."""
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], str):
        raise ValueError(f"Tuple funct invalide pour '{name}' : {raw!r}")
    fn_name = raw[0]
    rest = list(raw[1:])

    is_date = False
    if rest and isinstance(rest[-1], bool):
        is_date = rest.pop()

    kwargs = {}
    if rest and isinstance(rest[-1], dict):
        kwargs = _substitute_horizons(rest.pop(), horizons)

    # arguments positionnels : str = nom de colonne, numérique = littéral
    # (ex. [divided, "dQXA", 2, {first: true}] — cf. delta-dtFlood_H)
    pos_args = []
    for item in rest:
        if isinstance(item, str):
            pos_args.append(("col", item))
        elif isinstance(item, (int, float)):
            pos_args.append(("lit", item))
        else:
            raise ValueError(
                f"Élément inattendu dans le tuple funct de '{name}' : {item!r}"
            )

    # la résolution fn_name -> callable est paresseuse (registry.resolve à
    # l'exécution) : le chargement des métadonnées ne doit pas exiger que
    # toutes les fonctions soient déjà portées
    return {
        "name": name,
        "fn_name": fn_name,
        "pos_args": pos_args,
        "cols": [v for t, v in pos_args if t == "col"],
        "kwargs": kwargs,
        "is_date": is_date,
    }


def _parse_sampling_period(raw, horizons):
    if raw is None:
        return None
    if isinstance(raw, dict):
        if raw.get("type") != "adaptive":
            raise ValueError(f"sampling_period dict invalide : {raw!r}")
        entry = _parse_funct_tuple("_sampling", raw["funct"], horizons)
        return {"type": "adaptive", "funct": entry}
    return raw  # "MM-DD" ou ["MM-DD", "MM-DD"]


def load_card(path):
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    meta = raw.get("meta", {})
    meta_global = {**_GLOBAL_DEFAULTS, **meta.get("global", {})}
    horizons = meta_global.get("horizons")

    processes = []
    process_raw = raw.get("process", {})
    names = sorted(process_raw, key=lambda p: int(p.lstrip("P")))
    for i, pname in enumerate(names, start=1):
        if pname != f"P{i}":
            raise ValueError(
                f"{path} : processus non consécutifs ({names}), attendu P1..Pn."
            )
        p_raw = process_raw[pname]
        proc = {**_PROCESS_DEFAULTS,
                **{k: v for k, v in p_raw.items() if k != "funct"}}
        proc["name"] = pname
        proc["funct"] = [
            _parse_funct_tuple(var, t, horizons)
            for var, t in p_raw["funct"].items()
        ]
        proc["sampling_period"] = _parse_sampling_period(
            proc["sampling_period"], horizons
        )
        proc["period"] = _substitute_horizons(proc["period"], horizons)
        processes.append(proc)

    if not processes:
        raise ValueError(f"{path} : aucun processus défini.")

    return {
        "id": raw.get("id"),
        "meta": {
            "en": meta.get("en", {}),
            "fr": meta.get("fr", {}),
            "global": meta_global,
        },
        "processes": processes,
        "path": str(path),
    }

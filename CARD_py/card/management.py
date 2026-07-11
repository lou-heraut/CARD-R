"""Port Python de R/CARD_management.R — gestion des fiches CARD YAML."""

import shutil
from pathlib import Path

import pandas as pd

from .extraction import _DEFAULT_CARD_DIR, _find_cards, _meta_rows
from .loader import load_card


def CARD_list_all(CARD_path=None, include_experimental=False) -> pd.DataFrame:
    """Liste toutes les fiches CARD disponibles avec leurs métadonnées.

    Contrairement au package R (qui lit un CSV pré-généré), les métadonnées
    sont lues directement depuis les blocs meta des YAML.
    """
    if CARD_path is None:
        CARD_path = _DEFAULT_CARD_DIR
    cards = _find_cards(CARD_path, None)
    rows = [_meta_rows(load_card(p)) for p in cards.values()]
    metaEX = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not include_experimental and "is_experimental" in metaEX.columns:
        metaEX = metaEX[~metaEX["is_experimental"].astype(bool)]
        metaEX = metaEX.reset_index(drop=True)
    return metaEX


def CARD_management(CARD_name=("QA", "QJXA"), CARD_path="./WIP",
                    CARD_source=None, add_id=True, overwrite=False,
                    verbose=False):
    """Copie des fiches YAML dans un dossier de travail pour personnalisation.

    CARD_name : liste de noms, ou dict imbriqué {sous_dossier: [noms, ...]}
                pour organiser en sous-dossiers numérotés (comme en R).
    """
    if CARD_source is None:
        CARD_source = _DEFAULT_CARD_DIR
    dest = Path(CARD_path)

    if dest.exists():
        if overwrite:
            shutil.rmtree(dest)
        else:
            raise FileExistsError(
                f"Le dossier {dest} existe déjà, utilisez overwrite=True "
                "pour l'écraser."
            )
    dest.mkdir(parents=True)

    available = _find_cards(CARD_source, None)

    def _copy_names(names, target: Path):
        for j, name in enumerate(names, start=1):
            if name not in available:
                raise FileNotFoundError(f"CARD introuvable : {name}")
            fname = f"{j:03d}_{name}.yaml" if add_id else f"{name}.yaml"
            shutil.copy(available[name], target / fname)
            if verbose:
                print(f"  {available[name]} -> {target / fname}")

    if isinstance(CARD_name, dict):
        for i, (sub, names) in enumerate(CARD_name.items(), start=1):
            sub_dir = dest / (f"{i:03d}_{sub}" if add_id else sub)
            sub_dir.mkdir(parents=True)
            _copy_names(names, sub_dir)
    else:
        _copy_names(list(CARD_name), dest)

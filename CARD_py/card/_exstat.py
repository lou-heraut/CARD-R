"""Localisation du module EXstat_py (non packagé pour l'instant).

Ordre de résolution :
1. variable d'environnement EXSTAT_PY_PATH
2. chemin par défaut du projet EXstat
"""

import os
import sys

_DEFAULT_PATH = os.path.expanduser(
    "~/Documents/INRAE/projects/EXstat_project/EXstat_Claude/EXstat_py"
)


def _locate() -> str:
    path = os.environ.get("EXSTAT_PY_PATH", _DEFAULT_PATH)
    if not os.path.isfile(os.path.join(path, "process_extraction.py")):
        raise ImportError(
            f"EXstat_py introuvable à '{path}'. "
            "Définissez la variable d'environnement EXSTAT_PY_PATH vers le "
            "dossier contenant process_extraction.py."
        )
    return path


_path = _locate()
if _path not in sys.path:
    sys.path.insert(0, _path)

from process_extraction import process_extraction  # noqa: E402,F401

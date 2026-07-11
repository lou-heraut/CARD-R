# CARD_py — port Python du package CARD

Extraction de variables hydroclimatiques à partir des fiches CARD **YAML**
(`CARD_yml/`), en s'appuyant sur le port Python d'EXstat
(`EXstat_project/EXstat_Claude/EXstat_py/`).

## Statut — validation croisée corpus complet (2026-07-11)

Les ~210 fiches YAML ont été exécutées via CARD_py et comparées aux fiches
R du repo (données synthétiques 2 stations × 131 ans, toutes variables
d'entrée). Résultats (`tests/data/corpus_report*.csv`) :

- **En mode compat RcppRoll** (`CARD_ROLL_COMPAT=rcpp`) : 506 comparaisons
  identiques (tol 1e-6), les seules divergences résiduelles viennent du
  comptage des lacunes autour des moyennes mobiles (voir plus bas) et de
  fiches cassées côté R.
- **En mode par défaut** (rolling pandas) : mêmes résultats plus les
  divergences attendues de la convention rolling k pair (±1 jour sur les
  dates dérivées de VC10/VCX10 ; minima de bord de fenêtre pour la famille
  summer sur ce jeu de test au régime artificiel).
- **11 fiches crashent dans le package R lui-même** sur ce jeu de données
  (CR, CRS_season, FDC×5, QJC10, RA_ratio, RAl_ratio, RAs_ratio) — les
  versions Python s'exécutent et produisent des valeurs hydrologiquement
  cohérentes ; pas de référence R possible.
- **n-VCN10-5_H** : régression détectée (commit 2f2243e, renommage de
  masse ayant cassé le nom de sortie de P2 — R rendait silencieusement
  tout NA là où Python levait une erreur explicite). Corrigée dans le R
  et le YAML le 2026-07-11 ; validation croisée identique depuis.

La validation a aussi détecté et corrigé **un bug de conversion YAML** :
29 fiches (familles Low_Flows_Summer/Winter + QSA_JJASO) avaient perdu la
borne de fin de leur fenêtre `sampling_period` dans le bloc process.

Fiches de référence initiales (`dev/yaml_ref/`), validées exactement :

| Fiche | Couverture |
|-------|-----------|
| QA | agrégation annuelle simple, sampling_period fixe |
| median-QJC5 | time_step yearday, transform rollmean cyclique |
| tQJXA | is_date, sampling_period adaptatif |
| dtLF | chaîne 4 processus, keep=all, apply_threshold, kwarg-colonne (`lim: upLim`) |
| delta-endLF_H | horizons `$Hx`, get_deltaX, référence colonne date |

## Utilisation

```python
import pandas as pd
import sys; sys.path.insert(0, "CARD_py")
from card import CARD_extraction, CARD_list_all

data = pd.DataFrame({"date": ..., "Q": ..., "id": ...})   # date en datetime64
res = CARD_extraction(data, CARD_name=["QA", "dtLF"])
res["dataEX"]["QA"]      # un DataFrame par fiche
res["metaEX"]            # métadonnées (une ligne par variable)
```

Le chemin d'EXstat_py se règle via la variable d'environnement
`EXSTAT_PY_PATH` (défaut : chemin du projet EXstat, voir `card/_exstat.py`).
Le chemin des fiches via `CARD_path=` ou `CARD_YML_PATH` (défaut :
`../CARD_yml`).

## Architecture

```
card/
  loader.py       # YAML -> Process (remplace sourceProcess R) :
                  #   défauts, horizons $Hx, sampling adaptatif, tuples funct
  registry.py     # {nom YAML -> callable} (noms R conservés, ex. which.maxNA)
  extraction.py   # CARD_extraction : chaîne P1..Pn via process_extraction
                  #   + sampling adaptatif par station + transforms vectoriels
                  #   + résolution des kwargs référencant des colonnes
  management.py   # CARD_list_all, CARD_management
  functions/      # port de R/ (global.R, threshold.R, get_deltaX)
tests/
  make_test_data.py   # données synthétiques 2 stations, 1970-2100
  validate_R.R        # sorties de référence via le package R (fiches .R)
  validate_py.py      # exécution Python + comparaison
```

## Validation croisée

```bash
cd CARD_py
python3 tests/make_test_data.py
Rscript tests/validate_R.R
python3 tests/validate_py.py
```

## Notes de sémantique

- **Rolling centré** : convention pandas (`center=True`). Divergence
  assumée avec RcppRoll pour k pair (jour excédentaire à gauche au lieu
  de droite → série décalée de +1 position vs R) : on privilégie l'outil
  Python standard sur la réplication d'un détail d'implémentation R.
  Impact : valeurs absolues des dates dérivées d'un rolling k pair
  (ex. endLF) décalées de +1 ; durées et deltas insensibles.
- **Index 0-based** : `which.*NA` et `apply_threshold` (first/last)
  retournent des index 0-based ; la conversion is_date d'EXstat_py
  redonne exactement les valeurs R.
- **sampling_period adaptatif** : mois du max/min des moyennes mensuelles
  inter-annuelles, calculé par station (équivalent `fix_sampling_period` R) ;
  les stations sont regroupées par mois obtenu avant l'appel à EXstat_py.
- **kwargs colonnes** (`lim: upLim`) : résolus dynamiquement contre les
  colonnes des données courantes, comme les `funct_args` R. Les clés
  `where`, `what`, `select`, `waterType` ne sont jamais interprétées
  comme colonnes.
- **skipna** : `{skipna: true}` est consommé par EXstat_py (suppression des
  NaN avant agrégation) ; il ne faut PAS le mettre pour les fonctions
  positionnelles (which.*NA) qui ont besoin des positions d'origine.
- **Comptage des lacunes et moyennes mobiles** : en R, RcppRoll convertit
  les NA en NaN arithmétiques, invisibles pour le NApct
  (`is.na_not_nan`) — une année contenant une vraie lacune peut donc
  passer le filtre NApct côté R. Python compte honnêtement les NaN
  induits par le rolling : légèrement plus strict (divergence assumée,
  plus rigoureuse). Impacte les années à lacunes proches du seuil.
- **Colonnes creuses (fan-out keep='all')** : R marque les lignes de
  remplissage en NaN (non comptées comme lacunes) ; côté pandas,
  CARD_py compacte les lignes creuses quand le processus suivant
  n'utilise que ces colonnes — le dénominateur calendaire d'EXstat_py
  détecte alors les périodes réellement manquantes.

## Reste à faire

- `keep: [nom]` (liste de colonnes, cf. QJC10) non supporté par EXstat_py
  (la fiche QJC10 s'exécute, la sélection de colonnes est juste ignorée).
- Fonctions présentes en R mais utilisées par aucune fiche YAML
  (rq_slopes/segmented pour les fiches dtRec skippées, compute_R2...) :
  non portées.
- Packager EXstat_py (pyproject) pour remplacer la résolution par chemin.
- Signaler en amont les 11 fiches qui crashent dans le package R
  (bugs R indépendants de la migration).

# CLAUDE.md — CARD

## Contexte et état du projet (figé le 2026-07-11)

CARD est un recueil de fiches hydroclimatiques pour le package EXstat.
Chaque fiche décrit comment extraire une variable (débit, précipitation,
température...) à partir de séries temporelles journalières.

Le projet a deux phases, **toutes deux terminées** :

1. **Conversion R → YAML** : les 212 fiches de `inst/__all__/` sont
   converties dans `CARD_yml/` (2 skipped : dtRec/median-dtRec,
   instables). Les YAML sont la **source de vérité future** ; les fiches
   R restent la référence de validation. Log : `dev/conversion_log.csv`.
2. **Migration Python (`CARD_py/`)** : package Python qui exécute les
   fiches YAML via le port Python d'EXstat, **validé par comparaison
   croisée R↔Python sur le corpus complet** (détails section
   "Migration Python" plus bas et `CARD_py/README.md`).

La validation croisée a servi de test de non-régression pour la
conversion elle-même : elle a détecté et corrigé un bug de conversion
(29 fiches, borne de fin de `sampling_period` perdue) et une régression
dans une fiche R (n-VCN10-5_H, commit 2f2243e).

**Réorganisation du 2026-07-11 (phase A de la roadmap) — IMPORTANT :**
le code Python et les fiches YAML ont QUITTÉ ce repo, qui redevient
purement R. Nouvelle organisation :

- `CARD_project/card/` — nouveau package Python `card` (repo git séparé) :
  fiches YAML dans `src/card/cards/`, fonctions hydro, tests et harnais
  de validation croisée. Voir `card/README.md` et `card/ROADMAP.md`.
- `EXstat_project/exstat/` — nouveau package Python `exstat` (repo git
  séparé) : moteur générique d'extraction (sampling adaptatif, sorties
  vectorielles, kwargs-colonnes, colonnes creuses intégrés nativement).
- Les anciens emplacements `CARD/CARD_yml/` et `CARD/CARD_py/` n'existent
  plus ; `dev/yaml_ref/` reste ici (5 fiches de référence historiques).

**Où reprendre si besoin :**
- Prochaine étape : phase B de `card/ROADMAP.md` (noms Python natifs dans
  les YAML — numpy direct, renommages correctifs — puis suppression du
  registre). La table de renommage doit être validée par l'utilisateur.
- Ce repo (CARD R) : modifications locales non commitées (correction de
  inst/__all__/.../n-VCN10-5_H.R, CLAUDE.md, dev/). Les deux nouveaux
  repos card/ et exstat/ sont git init mais sans commit initial.
- Signaler en amont les 11 fiches qui crashent dans le package R lui-même
  (CR, CRS_season, FDC×5, QJC10, RA_ratio, RAl/RAs_ratio — bugs R
  indépendants de la migration, les versions Python fonctionnent).
- La mémoire persistante de Claude contient aussi l'état du projet
  (`project_card_conversion.md`).

---

## Structure des dossiers

```
inst/__all__/          # Fiches R sources, organisées par thème
  Flow/
    High_Flows/
      serie/           # Une variable par fiche
      criteria/        # Variables composites (multi-étapes, horizons)
    Low_Flows/...
    Mean_Flows/...
    Performance/
  Evapotranspiration/
  Precipitations/
  Sensitivity_to_Climate_Variability/
  Temperature/

dev/yaml_ref/          # 5 fiches de référence validées (historique)

# HORS de ce repo (réorganisation 2026-07-11) :
../card/               # package Python card — fiches YAML (src/card/cards/),
                       #   fonctions hydro, tests, harnais de validation
../../EXstat_project/exstat/   # package Python exstat — moteur d'extraction
```

---

## Format YAML — Règles de rédaction

### Structure générale

```yaml
id: QA
version: "1.0"
authors: []
date: "2026-04-26"

meta:
  en:
    variable: QA
    unit: "m^{3}.s^{-1}"
    name: Annual mean daily discharge
    description: ""
    method: "1. annual aggregation [09-01, 08-31] - mean"
    sampling_period: ["09-01", "08-31"]
    topic: "Flow, Mean Flows, Intensity"

  fr:
    variable: QA
    unit: "m^{3}.s^{-1}"
    name: Moyenne annuelle du débit journalier
    description: ""
    method: "1. agrégation annuelle [01-09, 31-08] - moyenne"
    sampling_period: ["01-09", "31-08"]
    topic: "Débit, Moyennes Eaux, Intensité"

  global:
    input_vars: Q
    preferred_sampling_period: "09-01"
    palette: ["#452C1A", "#7F4A23", "#B3762A", "#D4B86A", "#EFE0B0",
              "#BCE6DB", "#7ACEB9", "#449C93", "#2A6863", "#193830"]

process:
  P1:
    funct:
      QA: [mean, "Q", {skipna: true}]
    sampling_period: "09-01"
    NApct_lim: 3
    NAyear_lim: 10
```

---

### Règle 1 — funct (le plus important)

Chaque variable de sortie est une clé dans `funct`. La valeur est un
tuple `[fonction, *colonnes, kwargs?, is_date?]` :

- 1er élément : nom de la fonction en string
- éléments string suivants : noms des colonnes d'entrée
- avant-dernier (si dict) : kwargs — `na.rm=TRUE` en R devient `{skipna: true}`
- dernier (si booléen) : `is_date: true` — omis si false

```yaml
funct:
  QA:    [mean,            "Q",     {skipna: true}]
  QJXA:  [max,             "Q",     {skipna: true}]
  tQJXA: [which.maxNA,     "Q",     true]
  VC10:  [rollmean_center, "Q",     {k: 10}]
  VCN10: [min,             "VC10",  {skipna: true}]
  upLim: [max,             "VCN10", {skipna: true}]
  dtLF:  [apply_threshold, "VC10",  {lim: upLim, where: "<=", what: length, select: longest}]
  endLF: [apply_threshold, "VC10",  {lim: upLim, where: "<=", what: last, select: longest}, true]
```

---

### Règle 2 — sampling_period adaptatif

Quand la fenêtre annuelle est calculée depuis les données
(R : `list(max, list("Q", na.rm=TRUE))`), utiliser le même
formalisme tuple que `funct` :

```yaml
sampling_period:
  type: adaptive
  funct: [max, "Q", {skipna: true}]
```

---

### Règle 3 — palette

Toujours une liste YAML de strings hex :

```yaml
palette: ["#003C30", "#01665E", "#35978F", "#80CDC1", "#C7EAE5",
          "#F6E8C3", "#DFC27D", "#BF812D", "#8C510A", "#543005"]
```

---

### Règle 3b — sampling_period : liste vs string

Dans `meta.en` / `meta.fr`, distinguer :

- **Fenêtre [début, fin]** → liste de deux strings :
  ```yaml
  sampling_period: ["09-01", "08-31"]   # en
  sampling_period: ["01-09", "31-08"]   # fr
  ```
- **Date unique** ou **texte adaptatif** → string :
  ```yaml
  sampling_period: "09-01"
  sampling_period: Month of maximum monthly flows
  ```

Dans `process.Px`, `sampling_period` est toujours une string
(date de début) ou un bloc `type: adaptive`.

---

### Règle 4 — Variables multiples (horizons)

Quand une fiche produit plusieurs variables (ex: H1, H2, H3),
`variable`, `name`, `method` deviennent des listes :

```yaml
meta:
  en:
    variable: [delta-endLF_H1, delta-endLF_H2, delta-endLF_H3]
    name:
      - "Average change ... near horizon"
      - "Average change ... middle horizon"
      - "Average change ... distant horizon"
    method: |
      1. ...
      5. average change between historical period and {horizon} horizon
    horizon_labels: {H1: near, H2: middle, H3: distant}

  fr:
    variable: [delta-finBE_H1, delta-finBE_H2, delta-finBE_H3]
    horizon_labels: {H1: proche, H2: moyen, H3: lointain}

  global:
    horizons:
      H0: ["1976-01-01", "2005-08-31"]
      H1: ["2021-01-01", "2050-12-31"]
      H2: ["2041-01-01", "2070-12-31"]
      H3: ["2070-01-01", "2099-12-31"]
```

Pour P5 avec N fonctions et args différents, les horizons sont
référencés via `$H0`, `$H1`… — le parser remplace ces symboles
par les dates définies dans `meta.global.horizons` :

```yaml
process:
  P5:
    funct:
      delta-endLF_H1: [get_deltaX, "endLF", "date", {past: $H0, futur: $H1}]
      delta-endLF_H2: [get_deltaX, "endLF", "date", {past: $H0, futur: $H2}]
      delta-endLF_H3: [get_deltaX, "endLF", "date", {past: $H0, futur: $H3}]
    time_step: none
```

---

### Règle 5 — Champs à omettre (valeurs par défaut)

Ne pas écrire un champ si sa valeur est identique au défaut :

| Champ | Défaut (ne pas écrire) |
|-------|------------------------|
| `meta.global.is_date` | `false` |
| `meta.global.to_normalise` | `true` |
| `meta.global.is_experimental` | `false` |
| `meta.global.source` | `null` |
| `meta.global.palette` | `null` |
| `meta.global.preferred_sampling_period` | `null` |
| `meta.global.input_vars` | `"X"` (écrire si `"Q"` ou autre) |
| `Px.time_step` | `"year"` |
| `Px.sampling_period` | `null` |
| `Px.period` | `null` |
| `Px.NApct_lim` | `null` |
| `Px.NAyear_lim` | `null` |
| `Px.keep` | `null` |
| `Px.compress` | `false` |
| `Px.expand` | `false` |

---

## Règles de travail

> Phase de conversion terminée — règles conservées pour toute future
> création ou modification de fiche YAML.

- **Lire le R avant de générer** : toujours lire le fichier R source avant de produire le YAML (kwargs implicites, is_date, to_normalise, etc. ne sont pas toujours visibles autrement).
- **Batches de 10** : convertir par batch de 10, mettre à jour `conversion_log.csv` et `CLAUDE.md` après chaque batch, confirmer et attendre le "go" avant de continuer.
- **Noms de fonctions** : ne jamais modifier les noms de fonctions EXstat (rollmean_center, minNA, maxNA, apply_threshold, etc.).
- **Corrections automatiques** : corriger sans demander toute incohérence à confiance élevée — grammaire (accords, pluriels), orthographe, casse (Title Case → sentence case), mot dans la mauvaise langue, incohérence de structure ou de sens entre fiches. Seul cas nécessitant validation : réécriture complète d'une métadonnée (contenu scientifique à reformuler de fond).
- **Récapitulatif de batch** : tableau avec niveau de confiance par fiche (high / medium / low), corrections appliquées, et toute réécriture complète soumise à validation.

---

## Cas particuliers et incertitudes

Tenir ici un registre des cas ambigus rencontrés lors de la conversion,
avec la fiche source et la décision prise.

| Fiche | Cas ambigu | Décision |
|-------|-----------|----------|
| alpha-QJXA | `to_normalise` varie par variable (true / false) | `to_normalise: [true, false]` comme liste dans `meta.global` |
| alpha-QJXA | Source avec 3 citations | Bloc littéral `\|` avec sauts de ligne entre chaque citation |
| delta-BFI-LH_H, delta-BFI-Wal_H | `get_deltaX` reçoit un kwarg supplémentaire `Q_for_BFI="Q"` | `{past: $H0, futur: $H1, to_normalise: false, Q_for_BFI: "Q"}` |
| delta-dtBF_H, delta-vBF_H | `to_normalise=TRUE` explicite dans R pour `get_deltaX` | Conserver `to_normalise: true` dans les kwargs (pas omis même si = défaut global) |
| delta-dtFlood_H | `divided` avec argument positionnel numérique | `[divided, "dQXA", 2, {first: true}]` — le `2` est un arg positionnel |
| delta-dtFlood_H | `select:` dans `apply_threshold` est un nom de variable (pas un string prédéfini) | `select: dQXA` sans guillemets |
| delta-fQ01/05/10A_H | `lowLim` calculé en P1 puis passé comme kwarg en P2 | `{lowLim: lowLim}` — référence à variable calculée, sans guillemets |
| median-dtRec, serie/dtRec | Fiche instable | Skipped — YAML supprimé, log = skipped |
| delta-QJXA-10_H | `returnPeriod=10, waterType="high"` dans kwargs de `get_deltaX` | Ajoutés dans le dict kwargs : `{..., returnPeriod: 10, waterType: "high"}` |
| delta-QJXA-10_H | `topic_fr` contient "Intensity" (anglais) au lieu de "Intensité" | Anomalie R signalée — corrigé en "Intensité" dans le YAML |
| delta-VCX10_H | `method_en` step 1 dit "3-day centered moving average" au lieu de "10-day" | Anomalie R signalée — à corriger dans le YAML (utilisateur a pris en charge manuellement) |
| median-dtFlood, median-tQJXA | Variable name diffère entre en et fr (median-dtFlood / mediane-dtCrue, median-tQJXA / mediane-tQJXA) | Écrit différemment dans meta.en.variable et meta.fr.variable |
| median-tQJXA | `circular_median` avec `periodicity=365.25, na.rm=TRUE` | `[circular_median, "tQJXA", {periodicity: 365.25, skipna: true}]` |
| Q10, Q01A, Q05A, Q10A (serie) | `name_fr` contient "dépassée" (féminin) au lieu de "dépassé" (masculin, accord avec "Débit") | Corrigé en "dépassé" dans les YAML |
| Q10 (criteria) | `name_fr` contient "1 années" (pluriel) au lieu de "1 an" | Corrigé en "1 an" dans le YAML |
| allLF (serie) | `topic_en = ""` (chaîne vide) dans le R pour la fiche multi-var | Rempli depuis les topics FR et les fiches individuelles (Seasonality×3, Duration, Intensity) — anomalie R signalée |
| allLF (serie) | Fiche multi-var (5 vars) avec 2 palettes distinctes : 3 violet + 2 vert | `palette:` devient une liste de 5 listes hex — nouveau pattern |
| allLF (serie) | Méthodes FR de dtBE et vBE : parenthèse ouvrante `(extraction de la série des VCN10` sans fermeture | Parenthèse `)` ajoutée après "VCN10" — anomalie R corrigée |
| Q90A, Q95A, Q99A (serie) | `name_fr` contient "dépassée" (féminin) au lieu de "dépassé" (masculin, accord avec "Débit") | Corrigé en "dépassé" dans les YAML |
| Q95A, Q99A (serie) | `description_en` "a exceedance" → grammar | Corrigé en "an exceedance" |
| Q99A (serie) | `description_en` "1th percentile" → mauvais ordinal | Corrigé en "1st percentile" |
| QMNA (serie) | P2 `sampling_period` adaptive sur `QMA` (débits mensuels) et non `Q` | `funct: [max, "QMA", {skipna: true}]` |
| QMNA (serie) | P1 `time_step = "year-month"` — nouveau time_step | Conservé tel quel sans guillemets |
| VCN10, VCN30, VCN3 (serie) | `NAyear_lim=10` placé dans P1 (moving average) plutôt que dans P2 (annual) | Conservé dans P1 — filtre de qualité sur les données journalières avant le calcul |
| vLF (serie) | `name_fr` "Volume de déficite" → typo | Corrigé en "Volume de déficit" |
| alpha-VCN10 (criteria) | `name_en`, `description_en`, `method_en` entièrement faux (copy-paste de centerBF) | Corrigés depuis le FR + pattern alpha-QJXA; `topic_en` = "Flow, Baseflow, Seasonality" (faux) → "Flow, Low Flows, Intensity" |
| delta-allLF_H (criteria) | Fiche bundle 15 vars (5×3 horizons); bug R `"\n2."` au lieu de `"\n5."` pour l'étape finale des méthodes | Corrigé en `"5."` en EN et FR; palette liste×15; méthodes explicites (pas de template) |
| delta-allLF_H (criteria) | `to_normalise=FALSE` explicite en P5 pour tous y compris vLF (alors que `CARD$P.to_normalise[vLF]=TRUE`) | Suivi le R tel quel et noté comme anomalie potentielle (delta en % mais normalisé FALSE en get_deltaX) |
| delta-allLF_H (criteria) | `name_en` pour endLF contient "the End of low flows" (E majuscule) | Corrigé en "the end of low flows" |
| n-QJXA-10_H | `apply_threshold` reçoit `Date` et `period: $Hx` pour filtrer par horizon (sans get_deltaX) | `{lim: QJXA-10_H0, ..., Date: "date", period: $H1}` — pattern nouveau |
| n-QJXA-10_H | `get_Xn` avec kwargs `Date="date"` et `period=H0` en P2, sans en P3 | `[get_Xn, "QJXA", {returnPeriod: 10, waterType: "high", Date: "date", period: $H0}]` |
| VCX10, serie et criteria | `method_en` step 1 dit "3-day centered moving average" au lieu de "10-day" | Corrigé en "10-day" dans les YAML |
| VCX10, VCX3 (serie) | `name_en` en Title Case ("Annual Maximum of...") incohérent avec les autres fiches | Corrigé en sentence case dans les YAML |
| BFI-Wal, BFM, endBF, startBF, vBF | Fonction `compute_dtRec`/`get_BFI` appelée sans colonne positionnelle | Pas de colonne positionnelle dans le tuple : `[get_BFI, {kwargs}]` |
| centerBF, endBF, startBF, delta-*BF* | Résultat de type date (jour de l'année) | `is_date: true` dans `meta.global` + booléen `true` en fin de tuple funct |
| ETPA | `input_vars: ETP` (non Q, non X) | Écrit explicitement même si non-défaut standard |
| delta-QNA_H | `topic_en = "Flow, Low Water, Intensity"` (Water au lieu de Flows) | Corrigé en "Flow, Low Flows, Intensity" — anomalie R signalée |
| delta-QMNA_H | `topic_en = "Flow, Low Flow, Intensity"` (singulier) | Corrigé en "Flow, Low Flows, Intensity" — anomalie R signalée |
| delta-startLF_H | `method_en` numérotation "4." répétée deux fois (étape 5 absente) | Corrigé : dernière étape → "5." — anomalie R signalée; FR correct |
| delta-vLF_H | `description_fr` "entre de la moyenne" — grammaticalement incorrect | Corrigé en "entre la moyenne" — anomalie R signalée |
| delta-VCN10-5_H | `palette = NULL` → champ omis (défaut) | Omis conformément aux règles de défaut |
| delta-VCN10-5_H | `returnPeriod=5, waterType="low"` dans kwargs de `get_deltaX` | Ajoutés dans le dict kwargs P3 : `{..., returnPeriod: 5, waterType: "low"}` |
| median-allLF (criteria) | Fiche bundle 5 vars; `is_date=[T,T,T,F,F]`, `to_normalise=[F,F,F,F,T]` | Encodé comme listes dans `meta.global`; `true` en fin de tuple pour les 3 vars date en P4 |
| median-allLF (criteria) | `description_fr` centreBE : "des date de" (singulier) | Corrigé en "des dates de" — anomalie R signalée |
| median-allLF (criteria) | `description_fr` / `name_fr` vBE : "entre de la moyenne" / "déficite" | Corrigé en "entre la moyenne" / "déficit" — même bugs que dans vLF (serie) |
| median-allLF (criteria) | `method_fr` dtBE et vBE step 2 : parenthèse ouvrante sans fermeture | `)` ajoutée après "VCN10" — même anomalie que delta-allLF_H |
| median-startLF (criteria) | `method_fr` step 2 : "des des VCN10" (doublon) | Corrigé en "des VCN10" — anomalie R signalée |
| median-finLF (criteria) | `method_fr` step 4 : saut de ligne au milieu de la phrase | Joint en une seule ligne dans le YAML |
| median-tVCN10 (criteria) | `topic_en = "Flow, Low Flow, Seasonality"` (singulier) | Corrigé en "Flow, Low Flows, Seasonality" — anomalie R signalée |
| median-tVCN10 (criteria) | `NAyear_lim=10` dans P1 (comme VCN10 serie, pas P2) | Conservé dans P1 — même pattern que VCN10/VCN30/VCN3 |
| median-vLF (criteria) | `topic_en = "Flow, Low Flow, Intensity"` (singulier) ; `name_fr` "déficite" ; `description_fr` "entre de la" ; `method_fr` `)` step 2 | Quatre anomalies R corrigées — mêmes bugs que vLF/delta-vLF_H |
| n-VCN10-5_H | `sampling_period_en/fr` dit "minimum" dans le texte mais le code utilise `max` | Corrigé en "maximum" pour correspondre au code — anomalie R signalée |
| n-VCN10-5_H | P2 output nommé `n-VCN10` mais P3 et P4 lisent `"VCN10"` (colonne inexistante) — **régression introduite par le commit 2f2243e** (renommage de masse nVCN10→n-VCN10 qui a touché par erreur le nom de sortie de P2) ; R rendait silencieusement tout NA | **Corrigé le 2026-07-11** dans le R (`list(VCN10=minNA)`) et le YAML (`VCN10:`) — validation croisée R↔Python identique après correction |
| Q90 (criteria) | `name_fr` "Débit dépassée" (féminin) au lieu de "dépassé" | Corrigé en "dépassé" — même accord que Q90A (serie) |
| QMNA-5 (criteria) | `topic_en = "Flow, Low Flow, Intensity"` (singulier) | Corrigé en "Flow, Low Flows, Intensity" — anomalie R signalée |
| delta-allLF_summer_H (criteria) | Même pattern que delta-allLF_H : bug `"\n2."` à l'étape finale, `to_normalise=FALSE` pour tous en P5 (y compris vLF_summer), `name_en` "the End"→"the end" | Mêmes corrections appliquées — anomalies R signalées |
| QMNA_winter, QNA_winter, delta-QMNA_winter_H (serie/criteria) | `topic_en` contient "Low Flow" (singulier) ou "Low Water" (mauvaise catégorie) | Corrigé en "Flow, Low Flows, Intensity" — anomalies R signalées |
| allLF_winter (serie) | `description_fr` vBE_hiver "entre de la moyenne" — grammaticalement incorrect | Corrigé en "entre la moyenne" — même bug que vLF et allLF_summer |
| allLF_winter (serie) | `method_fr` dtBE_hiver et vBE_hiver step 2 : parenthèse ouvrante sans fermeture | `)` ajoutée après "VCN10" — même anomalie que allLF/allLF_summer/delta-allLF_H |
| delta-QNA_winter_H (criteria) | `topic_en = "Flow, Low Water, Intensity"` (Water au lieu de Flows) | Corrigé en "Flow, Low Flows, Intensity" — anomalie R signalée |
| delta-allLF_winter_H (criteria) | Même pattern que delta-allLF_H/summer : bug `"\n2."` à l'étape finale, `to_normalise=FALSE` pour tous en P5 (y compris vLF_winter), `name_en` "the End"→"the end" | Mêmes corrections appliquées — anomalies R signalées |
| delta-allLF_winter_H (criteria) | `description_fr` vBE_hiver "entre de la moyenne" — grammaticalement incorrect | Corrigé en "entre la moyenne" — même bug récurrent |
| delta-allLF_winter_H (criteria) | `method_fr` dtBE_hiver et vBE_hiver step 2 : parenthèse ouvrante sans fermeture | `)` ajoutée après "VCN10" — même anomalie récurrente |
| Q75A (serie) | `method_fr` "probabilité au dépassement" au lieu de "probabilité de dépassement" | Corrigé en "de dépassement" — anomalie R signalée |
| mean-QA (criteria) | `topic_en = "Flow, Average Waters, Intensity"` (Waters au lieu de Flows) | Corrigé en "Flow, Mean Flows, Intensity" — anomalie R signalée |
| delta-Q75A_H (criteria) | `method_fr` step 1 "probabilité au dépassement de 75 %" au lieu de "de dépassement" | Corrigé en "probabilité de dépassement" — même bug que Q75A (serie) |
| Bias_season (Performance) | `name_en` : "Autumn Bias" pour MAM et "Winter Bias" pour SON (saisonnalités échangées) | Corrigé en "Spring Bias" (MAM) et "Autumn Bias" (SON) — anomalie R signalée |
| Bias_season (Performance) | `name_fr` : "Biais automnal" pour MAM et "Biais hivernal" pour SON (même bug) | Corrigé en "Biais printanier" (MAM) et "Biais automnal" (SON) — anomalie R signalée |
| Bias_season (Performance) | `method_en` utilise le format DD-MM (format FR) dans les dates | Corrigé en format MM-DD pour chaque saison — anomalie R signalée |
| CRS_season (Precip) | `sampling_period_fr` SON = "09-01, 11-30" (format MM-DD) au lieu de "01-09, 30-11" (format DD-MM) | Corrigé — anomalie R signalée |
| dtCWDMA_month (Precip) | `name_en = ""` (chaîne vide) pour 12 variables | Rempli par analogie avec dtCDDMA : "Maximum number of consecutive rainy days in each [Month]" — anomalie R signalée |
| dtCWDMA_month (Precip) | `topic_en = "Precipitations, Dry period, Duration"` et `topic_fr = "Période sèche"` pour une fiche sur les jours PLUVIEUX | Corrigé en "Precipitations, Low, Duration" / "Précipitations, Faibles, Durée" — copier-coller depuis dtCDD, anomalie R signalée |
| dtCWDMA_month, dtCWDSA_season (Precip) | `description_fr` "au moins de 1 mm" (×16 au total) | Corrigé en "au moins 1 mm" — anomalie R signalée |
| dtRA01mm (Precip) | `topic_fr = "Précipitations, Faible, Durée"` (singulier) alors que dtCWDA utilise "Faibles" | Corrigé en "Faibles" — anomalie R signalée |
| QJC10 (serie) | P1 utilise `"Q_obs"` comme colonne d'entrée alors que `input_vars = "Q"` | Traduit fidèlement — anomalie R signalée (probable résidu d'un ancien nommage) |
| QJC10 (serie) | `keep: c("QJC10")` — liste de noms de variables spécifiques à conserver | `keep: [QJC10]` — liste YAML (nouveau pattern) |
| QJC10 (serie) | `rollmean_center` avec `isCyclical=TRUE` | `{k: 10, isCyclical: true}` dans kwargs |
| QMA_month (serie) | Bundle 12 vars (un par mois); `sampling_period` = 12 listes distinctes (une par mois) | Chaque entrée de sampling_period est une liste `["DD-MM","DD-MM"]` — nouveau pattern liste de listes |
| QSA_season (serie) | `time_step = "year-season"` et `Seasons = c("DJF","MAM","JJA","SON")` | `time_step: year-season` + `Seasons: [DJF, MAM, JJA, SON]` au niveau Px — nouveau pattern |
| FDC, FDC_H0 (serie) | `topic_en = "Flow, Mean Flows Intensity"` (virgule manquante entre "Flows" et "Intensity") | Corrigé en "Flow, Mean Flows, Intensity" — anomalie R signalée |
| FDC, FDC_H0 (serie) | Variable EN = FDC / FDC_H0, variable FR = CDC / CDC_H0 | Noms différents EN/FR — même pattern que median-dtFlood |
| FDC (serie) | `compute_FDC_p` sans colonne positionnelle; `compute_FDC_Q` avec "Q" | `[compute_FDC_p, {n: 1000, isNormLaw: true}]` / `[compute_FDC_Q, "Q", {n: 1000, isNormLaw: true}]` |
| FDC_H0 (serie) | `period = c("1976-01-01","2005-08-31")` au niveau P1 (filtre sur la période historique) | `period: ["1976-01-01","2005-08-31"]` au niveau Px — même champ que n-QJXA-10_H mais valeur fixe (non $Hx) |
| dtRA50mm, dtRMA50mm_month, dtRSA50mm_season | `name_fr` "extrème" → faute d'accent récurrente | Corrigé en "extrême" — anomalie R signalée (×17 occurrences) |
| dtRMA01mm_month, dtRSA01mm_season | `topic_fr = "Précipitations, Faible, Durée"` (singulier) | Corrigé en "Faibles" — anomalie R signalée (même pattern que dtRA01mm) |
| mean-RSA_season | `description_en` absent dans le R (contrairement à `description_fr` renseignée) | `description_en: ""` — anomalie R signalée |
| RA_all | 3 outputs en P1 (RA, RAl, RAs) depuis 3 inputs (R, Rl, Rs) ; `meta` ne déclare que "RA" | Traduit fidèlement — `input_vars: "R, Rl, Rs"` quoté (virgule+espace) |
| RA_ratio | `name_fr` "Ratio des précipitation" (singulier) au lieu de "précipitations" | Corrigé en "précipitations" — anomalie R signalée |
| RA_ratio | `meta.variable = "RA_ratio"` mais P3 produit `Rl_ratio` et `Rs_ratio` (noms différents) | Traduit fidèlement — anomalie R signalée (incohérence meta/process) |
| RCXA1, RCXA5 | `sampling_period = list(min, list("R", na.rm=TRUE))` (minimum mensuel des précipitations) | `{type: adaptive, funct: [min, "R", {skipna: true}]}` — même pattern que maxNA mais avec `min` |
| RCXA5 | `keep = "all"` dans P1 (conserver tous les intermédiaires) | `keep: all` au niveau Px — valeur string (différent du pattern liste de QJC10) |
| RMAs_month | `to_normalise` non défini en R (défaut TRUE), contrairement à RMA_month et RMAl_month qui setent FALSE | Traduit fidèlement (omis = défaut true) — anomalie R signalée (probable oubli) |
| RMAs_month | `reverse_palette = FALSE` — champ inconnu dans le schéma CARD | Omis (FALSE vraisemblablement le défaut) — anomalie R signalée |
| Rc | `topic_en = "Sensitivity to climate variability"` (minuscule "climate") | Corrigé en "Sensitivity to Climate Variability" — anomalie R signalée |
| mean-TA | `input_vars = "Q"` (bug R — le process utilise "T") | Corrigé en `input_vars: T` — anomalie R signalée |
| RAT_ET0 | `method_en` step 1 dit "mean temperatures" au lieu de "mean reference evapotranspiration" | Traduit fidèlement — anomalie R signalée |
| RAT_R | `method_en` step 1 dit "mean temperatures" au lieu de "total precipitation" | Traduit fidèlement — anomalie R signalée |
| TSA_season | `name_fr` "Température hivernales annuelle" ×4 (singulier + accord féminin) | Corrigé en "Températures hivernales/printanières/estivales/automnales annuelles" ×4 — anomalie R signalée |
| 29 fiches Low_Flows_Summer/Winter + QSA_JJASO | **Bug de conversion détecté par la validation croisée CARD_py (2026-07-11)** : la borne de fin des fenêtres `sampling_period` process (`c("05-01","11-30")` etc.) avait été perdue (`"05-01"` seul) | Corrigé dans les 29 YAML — `sampling_period: ["05-01", "11-30"]` / `["11-01", "04-30"]` / `["06-01", "10-31"]` |
| CR, CRS_season, FDC×5, QJC10, RA_ratio, RAl_ratio, RAs_ratio | Ces 11 fiches R crashent dans le package R CARD 2.0 lui-même (erreurs EXstat internes) | YAML convertis et exécutables via CARD_py ; pas de validation croisée possible — anomalie R signalée |

---

## Migration Python (CARD_py/) — terminée et validée le 2026-07-11

Le package `CARD_py/` exécute les fiches YAML via le port Python d'EXstat
(`~/Documents/INRAE/projects/EXstat_project/EXstat_Claude/EXstat_py/`,
non packagé, chemin résolu par `card/_exstat.py` / env `EXSTAT_PY_PATH`).

### Architecture

- `card/loader.py` — remplace `sourceProcess()` : YAML → processus
  (défauts, substitution `$Hx`, sampling adaptatif, tuples funct ;
  résolution des fonctions **paresseuse** pour que `CARD_list_all`
  charge tout le corpus).
- `card/registry.py` — {nom YAML → callable}, 50 fonctions ; flags
  `is_transform` (sortie vectorielle même longueur, ex. rollmean) et
  `is_ragged` (longueur indépendante, ex. compute_FDC_p).
- `card/extraction.py` — `CARD_extraction` : chaîne P1..Pn via
  `process_extraction` d'EXstat_py + ce qu'EXstat_py n'a pas :
  sampling_period **adaptatif par station** (mois du max/min des
  moyennes mensuelles, équiv. `fix_sampling_period` R), chemins
  **transform/ragged**, résolution dynamique des **kwargs-colonnes**
  (`{lim: upLim}`) et **littéraux positionnels** (`[divided, "dQXA", 2]`),
  **compactage des colonnes creuses** issues du fan-out `keep="all"`.
- `card/functions/` — port de `R/` (aggregation, threshold, baseflow
  LH/Wallingford, return_period Gumbel/log-normale, fdc, performance
  NSE/KGE/RAT, climate, seasonal/get_deltaX, trend→tools.py d'EXstat_py).

### Validation croisée (rejouable)

```bash
cd CARD_py
python3 tests/make_test_data.py        # 2 stations 1970-2100, 12 vars d'entrée
Rscript tests/run_R_corpus.R           # référence R (toutes fiches)
python3 tests/run_py_corpus.py         # comparaison → tests/data/corpus_report.csv
CARD_ROLL_COMPAT=rcpp python3 tests/run_py_corpus.py   # mode parité RcppRoll
```

Résultat : ~506 comparaisons identiques (tol 1e-6) en mode compat ;
en mode défaut s'ajoutent les divergences attendues du rolling pandas.
Rapports conservés : `tests/data/corpus_report.csv` (défaut) et
`corpus_report_rcpp_compat.csv` (preuve de parité).

### Divergences assumées (décisions utilisateur : outil Python pur et
rigueur priment sur la réplication exacte de R)

| Sujet | R | Python | Impact |
|---|---|---|---|
| Rolling centré k pair | RcppRoll : jour excédentaire à droite | pandas `center=True` : à gauche | dates dérivées de VC10/VCX10 décalées de ±1 jour ; toggle `CARD_ROLL_COMPAT=rcpp` pour parité exacte |
| Comptage des lacunes après rolling | RcppRoll convertit NA→NaN, invisibles au NApct (`is.na_not_nan`) | compte les NaN induits | Python légèrement plus strict près du seuil NApct |
| Colonnes creuses (fan-out `keep="all"`) | distinction NA/NaN | compactage des lignes creuses + dénominateur calendaire | équivalent, plus propre |
| Index (which.*NA, first/last) | 1-based | 0-based | la chaîne complète avec conversion is_date d'EXstat_py redonne exactement les valeurs R |
| n-VCN10-5_H cassée | NA silencieux | erreur explicite | fiche corrigée depuis |

### Pièges connus (côté R, découverts pendant la validation)

- `sourceProcess()` fuit des connexions : `closeAllConnections()`
  obligatoire dans une boucle de plus de ~125 fiches.
- Les bundles 15-36 variables donnent des noms de fichiers trop longs
  si on concatène les noms de variables.
- En R, `funct_args` nommés dont la valeur matche un nom de colonne
  sont substitués par la colonne (c'est la sémantique reproduite par
  CARD_py) ; `select="longest"` passé à `compute_VolDef` ne marche que
  par appariement partiel R avec `select_longest` (ignoré dans le corps).

---

## État de la conversion — TERMINÉE (212/212, 2 skipped)

Toutes les fiches sont converties et la validation croisée Python a servi
de test de non-régression (cf. section Migration Python). Liste conservée
pour référence.

### Fiches de référence validées (dev/yaml_ref/)
- [x] QA
- [x] median-QJC5
- [x] tQJXA
- [x] dtLF
- [x] delta-endLF_H

### Evapotranspiration/
- [x] ETPA

### Flow/Baseflow/
- [x] serie/BF-LH
- [x] serie/centerBF
- [x] serie/dtBF
- [-] serie/dtRec (skipped — instable)
- [x] serie/endBF
- [x] serie/startBF
- [x] serie/vBF
- [x] criteria/BFI-Wal
- [x] criteria/BFM
- [x] criteria/delta-BFI-LH_H
- [x] criteria/delta-BFI-Wal_H
- [x] criteria/delta-centerBF_H
- [x] criteria/delta-dtBF_H
- [x] criteria/delta-endBF_H
- [x] criteria/delta-startBF_H
- [x] criteria/delta-vBF_H
- [x] criteria/median-centerBF
- [x] criteria/median-dtBF
- [-] criteria/median-dtRec (skipped — instable)
- [x] criteria/median-endBF
- [x] criteria/median-startBF
- [x] criteria/median-vBF

### Flow/High_Flows/
- [x] serie/dtFlood
- [x] serie/fQ01A
- [x] serie/fQ05A
- [x] serie/fQ10A
- [x] serie/Q01A
- [x] serie/Q05A
- [x] serie/Q10A
- [x] serie/QJXA
- [x] serie/tQJXA
- [x] serie/tVCX10
- [x] serie/tVCX3
- [x] serie/VCX10
- [x] serie/VCX3
- [x] criteria/alpha-QJXA
- [x] criteria/delta-dtFlood_H
- [x] criteria/delta-fQ01A_H
- [x] criteria/delta-fQ05A_H
- [x] criteria/delta-fQ10A_H
- [x] criteria/delta-Q01A_H
- [x] criteria/delta-Q05A_H
- [x] criteria/delta-Q10A_H
- [x] criteria/delta-QJXA-10_H
- [x] criteria/delta-QJXA_H
- [x] criteria/delta-tQJXA_H
- [x] criteria/delta-tVCX10_H
- [x] criteria/delta-tVCX3_H
- [x] criteria/delta-VCX10_H
- [x] criteria/delta-VCX3_H
- [x] criteria/median-dtFlood
- [x] criteria/median-tQJXA
- [x] criteria/n-QJXA-10_H
- [x] criteria/Q10
- [x] criteria/QJXA-10

### Flow/Low_Flows/
- [x] serie/allLF
- [x] serie/centerLF
- [x] serie/dtLF (référence)
- [x] serie/endLF
- [x] serie/Q90A
- [x] serie/Q95A
- [x] serie/Q99A
- [x] serie/QMNA
- [x] serie/QNA
- [x] serie/startLF
- [x] serie/tVCN10
- [x] serie/VCN10
- [x] serie/VCN30
- [x] serie/VCN3
- [x] serie/vLF
- [x] criteria/delta-endLF_H (référence)
- [x] criteria/alpha-VCN10
- [x] criteria/delta-allLF_H
- [x] criteria/delta-centerLF_H
- [x] criteria/delta-dtLF_H
- [x] criteria/delta-Q90A_H
- [x] criteria/delta-Q95A_H
- [x] criteria/delta-Q99A_H
- [x] criteria/delta-QMNA_H
- [x] criteria/delta-QNA_H
- [x] criteria/delta-startLF_H
- [x] criteria/delta-tVCN10_H
- [x] criteria/delta-VCN10-5_H
- [x] criteria/delta-VCN10_H
- [x] criteria/delta-VCN30_H
- [x] criteria/delta-VCN3_H
- [x] criteria/delta-vLF_H
- [x] criteria/median-allLF
- [x] criteria/median-dtLF
- [x] criteria/median-finLF
- [x] criteria/median-startLF
- [x] criteria/median-tVCN10
- [x] criteria/median-vLF
- [x] criteria/n-VCN10-5_H
- [x] criteria/Q90
- [x] criteria/QMNA-5
- [x] criteria/VCN10-5
- [x] criteria/VCN30-2

### Flow/Low_Flows_Summer/
- [x] serie/allLF_summer
- [x] serie/QMNA_summer
- [x] serie/QNA_summer
- [x] serie/tVCN10_summer
- [x] serie/VCN10_summer
- [x] serie/VCN30_summer
- [x] serie/VCN3_summer
- [x] criteria/delta-QMNA_summer_H
- [x] criteria/delta-QNA_summer_H
- [x] criteria/delta-tVCN10_summer_H
- [x] criteria/delta-VCN10_summer_H
- [x] criteria/delta-VCN30_summer_H
- [x] criteria/delta-VCN3_summer_H
- [x] criteria/delta-allLF_summer_H

### Flow/Low_Flows_Winter/
- [x] serie/allLF_winter
- [x] serie/QMNA_winter
- [x] serie/QNA_winter
- [x] serie/tVCN10_winter
- [x] serie/VCN10_winter
- [x] serie/VCN30_winter
- [x] serie/VCN3_winter
- [x] criteria/delta-QMNA_winter_H
- [x] criteria/delta-QNA_winter_H
- [x] criteria/delta-tVCN10_winter_H
- [x] criteria/delta-VCN10_winter_H
- [x] criteria/delta-VCN30_winter_H
- [x] criteria/delta-VCN3_winter_H
- [x] criteria/delta-allLF_winter_H

### Flow/Mean_Flows/
- [x] serie/median-QJC5 (référence)
- [x] serie/FDC
- [x] serie/FDC_H0
- [x] serie/Q25A
- [x] serie/Q50A
- [x] serie/Q75A
- [x] serie/QA
- [x] serie/QJC10
- [x] serie/QMA_month
- [x] serie/QSA_JJASO
- [x] serie/QSA_season
- [x] serie/FDC_H1
- [x] serie/FDC_H2
- [x] serie/FDC_H3
- [x] serie/median-QJ
- [x] serie/median-QJ_H0
- [x] serie/median-QJ_H1
- [x] serie/median-QJ_H2
- [x] serie/median-QJ_H3
- [x] serie/QM
- [x] serie/QM_H0
- [x] serie/QM_H1
- [x] serie/QM_H2
- [x] serie/QM_H3
- [x] criteria/a-FDC
- [x] criteria/alpha-QA
- [x] criteria/delta-Q25A_H
- [x] criteria/delta-Q50A_H
- [x] criteria/delta-Q75A_H
- [x] criteria/delta-QA_H
- [x] criteria/delta-QMA_month_H
- [x] criteria/delta-QSA_season_H
- [x] criteria/mean-QA
- [x] criteria/Q50

### Flow/Performance/
- [x] Bias
- [x] Bias_season
- [x] KGE
- [x] KGEsqrt
- [x] NSE
- [x] NSEinv
- [x] NSElog
- [x] NSEsqrt
- [x] STD

### Precipitations/
- [x] CR
- [x] CRS_season
- [x] dtCDDA
- [x] dtCDDMA_month
- [x] dtCDDSA_season
- [x] dtCWDA
- [x] dtCWDMA_month
- [x] dtCWDSA_season
- [x] dtRA01mm
- [x] dtRA20mm
- [x] dtRA50mm
- [x] dtRMA01mm_month
- [x] dtRMA20mm_month
- [x] dtRMA50mm_month
- [x] dtRSA01mm_season
- [x] dtRSA20mm_season
- [x] dtRSA50mm_season
- [x] mean-RA
- [x] mean-RSA_season
- [x] RA_all
- [x] RA
- [x] RAl
- [x] RAl_ratio
- [x] RA_ratio
- [x] RAs
- [x] RAs_ratio
- [x] RCXA1
- [x] RCXA5
- [x] RMAl_month
- [x] RMA_month
- [x] RMAs_month
- [x] RSAl_season
- [x] RSA_season
- [x] RSAs_season

### Sensitivity_to_Climate_Variability/
- [x] epsilon_R
- [x] epsilon_R_season
- [x] epsilon_T
- [x] epsilon_T_season
- [x] RAT_ET0
- [x] RAT_R
- [x] RAT_T
- [x] Rc

### Temperature/
- [x] mean-TA
- [x] mean-TSA_season
- [x] TA
- [x] TMA_month
- [x] TSA_season

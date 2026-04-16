# CARD [<img src="figures/flower_alt_hex.png" align="right" width=160 height=160 alt=""/>](https://github.com/lou-heraut/EXstat/)

<!-- badges: start -->
[![R-CMD-check](https://github.com/lou-heraut/CARD/actions/workflows/R-CMD-check.yaml/badge.svg)](https://github.com/lou-heraut/CARD/actions/workflows/R-CMD-check.yaml)
[![Lifecycle: stable](https://img.shields.io/badge/lifecycle-stable-green)](https://lifecycle.r-lib.org/articles/stages.html)
![](https://img.shields.io/github/last-commit/lou-heraut/CARD)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md) 
<!-- badges: end -->

**CARD** is an efficient and user-friendly solution for aggregating daily hydroclimatological time series data in R, made possible through the use of parameterization files.

More precisely, this package aims at regroup all relevant aggregated hydroclimatological variable procedures into a CARD and serves as an interface to the core aggregation process carried out by the [EXstat](https://github.com/lou-heraut/EXstat) package.

This project was carried out for National Research Institute for Agriculture, Food and the Environment (Institut National de Recherche pour l’Agriculture, l’Alimentation et l’Environnement, [INRAE](https://agriculture.gouv.fr/inrae-linstitut-national-de-recherche-pour-lagriculture-lalimentation-et-lenvironnement) in french) and is at the core of [MAKAHO](https://github.com/lou-heraut/MAKAHO) which won the [2024 Open Science Research Data Award](https://www.enseignementsup-recherche.gouv.fr/fr/remise-des-prix-science-ouverte-des-donnees-de-la-recherche-2024-98045) in the “Creating the Conditions for Reuse” category.


## Installation
For latest development version in R
``` R
remotes::install_github("lou-heraut/CARD")
```


## How to use CARD ?
For a more user-friendly aggregation process, this package regroup predefined parameterisation files called CARD. Each CARD represent one hydroclimatological aggregated variable.

That way you don't have to define complex parameters yourself to extract hydroclimatological variables. What's more, if the CARD you want doesn't exist, it's easy to [create one]() based on the others.


### Basic workflow
For example, in hydrology, if you want to extract the annual mean daily discharge QA from hydrometric data
``` R
install.packages("airGRdatasets")
library(dplyr)

data = tibble(airGRdatasets::A273011002$TS) %>%
    mutate(code="A273011002",
           Date=as.Date(Date)) %>%
    rename(Q=Qls)
```		     

you can simply run
``` R
res = CARD_extraction(data, CARD_name="QA")
```

which will return
``` R
> res
$metaEX
# A tibble: 1 × 19
  variable_en unit_en      name_en description_en method_en sampling_period_en
  <chr>       <chr>        <chr>   <chr>          <chr>     <chr>             
1 QA          m^{3}.s^{-1} Annual… ""             1. annua… 09-01, 08-31      
# ℹ 13 more variables: topic_en <chr>, variable_fr <chr>, unit_fr <chr>,
#   name_fr <chr>, description_fr <chr>, method_fr <chr>,
#   sampling_period_fr <chr>, topic_fr <chr>,
#   preferred_hydrological_month <dbl>, is_date <lgl>, to_normalise <lgl>,
#   palette <chr>, script_path <chr>

$dataEX
$dataEX$QA
# A tibble: 21 × 3
   code       Date          QA
   <chr>      <date>     <dbl>
 1 A273011002 1998-09-01   NA 
 2 A273011002 1999-09-01 7048.
 3 A273011002 2000-09-01 6409.
 4 A273011002 2001-09-01 6403.
 5 A273011002 2002-09-01 4850.
 6 A273011002 2003-09-01 3768.
 7 A273011002 2004-09-01 5044.
 8 A273011002 2005-09-01 4805.
 9 A273011002 2006-09-01 7095.
10 A273011002 2007-09-01 5575.
# ℹ 11 more rows
# ℹ Use `print(n = ...)` to see more rows
```

So the result is a list of the metadata of the extraction in the `metaEX` tibble and the result of the extraction in the `dataEX` tibble.

Many CARDs are available. If you want to have a look of every current possibilities, use the `CARD_list_all()` function
``` R
metaEX_all = CARD_list_all()
```
which gives
``` R
> metaEX_all
# A tibble: 565 × 20
   variable_en     unit_en name_en description_en method_en sampling_period_en
   <chr>           <chr>   <chr>   <chr>          <chr>     <chr>             
 1 ETPA            mm      Cumula… ""             ""        09-01, 08-31      
 2 BFI_Wal         withou… Basefl… "Ratio betwe…" "1. no …" NA                
 3 BFM             withou… Basefl… ""             "1. no …" NA                
 4 delta{BFI}_LH_… withou… Change… "Ratio betwe…" "1. no …" NA                
 5 delta{BFI}_LH_… withou… Change… "Ratio betwe…" "1. no …" NA                
 6 delta{BFI}_LH_… withou… Change… "Ratio betwe…" "1. no …" NA                
 7 delta{BFI}_Wal… withou… Change… "Ratio betwe…" "1. no …" NA                
 8 delta{BFI}_Wal… withou… Change… "Ratio betwe…" "1. no …" NA                
 9 delta{BFI}_Wal… withou… Change… "Ratio betwe…" "1. no …" NA                
10 delta{centerBF… day     Averag… "Date when 5…" "1. ann…" 09-01, 08-31      
# ℹ 555 more rows
# ℹ 14 more variables: topic_en <chr>, variable_fr <chr>, unit_fr <chr>,
#   name_fr <chr>, description_fr <chr>, method_fr <chr>,
#   sampling_period_fr <chr>, topic_fr <chr>, source <chr>,
#   preferred_hydrological_month <int>, is_date <lgl>, to_normalise <lgl>,
#   palette <chr>, script_path <chr>
# ℹ Use `print(n = ...)` to see more rows
```

Based on that, you can for example filter variables by their topic with
``` R
metaEX_low_flow = dplyr::filter(metaEX_all, grepl("Low Flow", topic_en))
```
and get the name of all those available CARDs with  
``` R
metaEX_low_flow$variable_en
```


### Complex workflow
In a similar, more complex way, you can extract multiple variables at a time with more than one discharge series,
``` R
# For one station
data1 = tibble(airGRdatasets::A273011002$TS) %>%
    mutate(code="A273011002",
           Date=as.Date(Date)) %>%
    rename(Q_obs=Qls)

# and an other
data2 = tibble(airGRdatasets::H622101001$TS) %>%
    mutate(code="H622101001",
           Date=as.Date(Date)) %>%
    rename(Q_obs=Qls)
# make one tibble
data = bind_rows(data1, data2)

# add some noise for mock simulation data
data$Q_sim = data$Q_obs + rnorm(nrow(data), mean=0, sd=100)

# and perfom an extraction
res = CARD_extraction(data,
                      CARD_name=c("QA", "QMNA", "VCN10-5"),
                      suffix=c("obs", "sim"))
```

which will return
``` R
> res
$metaEX
# A tibble: 3 × 19
  variable_en unit_en      name_en description_en method_en sampling_period_en
  <chr>       <chr>        <chr>   <chr>          <chr>     <chr>             
1 VCN10-5     m^{3}.s^{-1} Annual… ""             "1. no t…" "Month of maximum …"
2 QMNA        m^{3}.s^{-1} Annual… ""             "1. mont…" "Month of maximum …"
3 QA          m^{3}.s^{-1} Annual… ""             "1. annu…" 09-01, 08-31      
# ℹ 13 more variables: topic_en <chr>, variable_fr <chr>, unit_fr <chr>,
#   name_fr <chr>, description_fr <chr>, method_fr <chr>,
#   sampling_period_fr <chr>, topic_fr <chr>,
#   preferred_hydrological_month <dbl>, is_date <lgl>, to_normalise <lgl>,
#   script_path <chr>, palette <chr>

$dataEX
$dataEX$`VCN10-5`
# A tibble: 2 × 3
  code       `VCN10-5_obs` `VCN10-5_sim`
  <chr>              <dbl>         <dbl>
1 A273011002          914.          901.
2 H622101001         2770.         2769.

$dataEX$QMNA
# A tibble: 40 × 4
   code       Date       QMNA_obs QMNA_sim
   <chr>      <date>        <dbl>    <dbl>
 1 A273011002 1999-01-01    1050.    1070.
 2 A273011002 2000-01-01    2586.    2569.
 3 A273011002 2001-01-01    1401.    1408.
 4 A273011002 2002-01-01    1463.    1454.
 5 A273011002 2003-01-01    1182.    1167.
 6 A273011002 2004-01-01    1362.    1354.
 7 A273011002 2005-01-01    1245.    1264.
 8 A273011002 2006-01-01    1770     1778.
 9 A273011002 2007-01-01    1889.    1875.
10 A273011002 2008-01-01    1669.    1659.
# ℹ 30 more rows
# ℹ Use `print(n = ...)` to see more rows

$dataEX$QA
# A tibble: 42 × 4
   code       Date       QA_obs QA_sim
   <chr>      <date>      <dbl>  <dbl>
 1 A273011002 1998-09-01    NA     NA 
 2 A273011002 1999-09-01  7048.  7049.
 3 A273011002 2000-09-01  6409.  6419.
 4 A273011002 2001-09-01  6403.  6407.
 5 A273011002 2002-09-01  4850.  4842.
 6 A273011002 2003-09-01  3768.  3763.
 7 A273011002 2004-09-01  5044.  5045.
 8 A273011002 2005-09-01  4805.  4805.
 9 A273011002 2006-09-01  7095.  7093.
10 A273011002 2007-09-01  5575.  5562.
# ℹ 32 more rows
# ℹ Use `print(n = ...)` to see more rows
```


### Custom workflow
Maybe you can't find the CARD that you want so you want to try to customize one or even create a new one based on another example. To do so, get the example CARD you want in a local directory by running
```R  
CARD_management(CARD_name = c("VCN10-5"), CARD_path = "CARD-WIP")  
```  
This will create the `VCN10-5.R` CARD in the `"CARD-WIP"` directory of your working directory.

From there, you can open this R file and, for example, change the metadata and the return period parameter from `5` to `10` to get the `VCN10-10` CARD, which represents the annual minimum of 10-day mean daily discharge with a return period of 10 years instead of 5.

For the extraction, simply run  
```R  
res = CARD_extraction(data, CARD_name = NULL,  
                      CARD_path = "CARD-WIP")  
```  
This will perform the extraction of all the CARDs in the `CARD_path` directory.

If you want to select specific variables to extract from your custom CARD directory, just use the `CARD_name` variable as seen in the [basic workflow](#basic-workflow) section.


## What is a CARD ?

### [inst/\_\_all\_\_](https://github.com/lou-heraut/CARD/blob/main/inst/__all__) directory
In this directory, you can find all the different CARDs available, organized by topic and type of aggregation: serie or criteria. In the [EXstat](https://github.com/lou-heraut/EXstat) terminology, a criterion is an aggregated variable that does not retain any temporal extension, unlike a serie variable, which maintains a temporal extension even after the aggregation process.

All CARDs have the same structure, as exemplified by the annual average daily flow [`QA`](https://github.com/lou-heraut/CARD/blob/main/inst/__all__/Flow/Mean_Flows/serie/QA.R) in [`__all__/Flow/Mean_Flows/serie`](https://github.com/lou-heraut/CARD/tree/main/inst/__all__/Flow/Mean_Flows/serie):
``` R
#   ___                _ 
#  / __| __ _  _ _  __| |
# | (__ / _` || '_|/ _` |
#  \___|\__,_||_|  \__,_|
# Copyright 2022-2025 Louis Héraut (louis.heraut@inrae.fr)*1
#
# *1   INRAE, France
#
# This file is part of CARD R package.
#
# CARD R package is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# CARD R package is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CARD R package.
# If not, see <https://www.gnu.org/licenses/>.


## INFO ______________________________________________________________
### English __________________________________________________________
CARD$P.variable_en = "QA"
CARD$P.unit_en = "m^{3}.s^{-1}"
CARD$P.name_en = "Annual mean daily discharge"
CARD$P.description_en = ""
CARD$P.method_en = "1. annual aggregation [09-01, 08-31] - mean"
CARD$P.sampling_period_en = "09-01, 08-31"
CARD$P.topic_en = "Flow, Mean Flows, Intensity"

### French ___________________________________________________________
CARD$P.variable_fr = "QA"
CARD$P.unit_fr = "m^{3}.s^{-1}"
CARD$P.name_fr = "Moyenne annuelle du débit journalier"
CARD$P.description_fr = ""
CARD$P.method_fr = "1. agrégation annuelle [01-09, 31-08] - moyenne"
CARD$P.sampling_period_fr = "01-09, 31-08"
CARD$P.topic_fr = "Débit, Moyennes Eaux, Intensité"

### Global ___________________________________________________________
CARD$P.preferred_hydrological_month = 9
CARD$P.is_date = FALSE
CARD$P.to_normalise = TRUE
CARD$P.palette = "#452C1A #7F4A23 #B3762A #D4B86A #EFE0B0 #BCE6DB #7ACEB9 #449C93 #2A6863 #193830"


## PROCESS ___________________________________________________________
### P1 _______________________________________________________________
CARD$P1.funct = list(QA=mean)
CARD$P1.funct_args = list("Q", na.rm=TRUE)
CARD$P1.time_step = "year"
CARD$P1.sampling_period = "09-01"
CARD$P1.NApct_lim = 3
CARD$P1.NAyear_lim = 10
```

CARDs are separated into 2 main parts: `INFO` and `PROCESS`.

##### INFO
In this part, you can find all the necessary information about the variable represented by this CARD. There are English and French versions for parameters such as the unit, the name, and the description. Global info are general info that do not need translation.

This information is not merely informational; it serves as metadata for [EXstat](https://github.com/lou-heraut/EXstat).

All of these parameters are optional because each of them has a default value based on the [`__default__.R`](https://github.com/lou-heraut/CARD/blob/main/inst/__default__.R) CARD, which you can find in the [inst](https://github.com/lou-heraut/CARD/blob/main/inst) directory. However, you are definitely encouraged to fill out most of them.

##### PROCESS
In the PROCESS part, you will find steps needed to extract the desired variable. The parameters listed here are parameters that you can use in [EXstat](https://github.com/lou-heraut/EXstat)'s [`process_extraction()`](https://github.com/lou-heraut/EXstat/blob/main/R/process_extraction.R) function. Here, there is only one step because we only need to calculate a yearly mean and no other type of aggregation. However, for example, we can add another step like:

``` R
### P2 _______________________________________________________________
CARD$P2.funct = list("meanQA"=mean)
CARD$P2.funct_args = list("QA", na.rm=TRUE)
CARD$P2.time_step = "none"
```

And that will now be the modulus of the flow, which is the average of the annual average daily flow, labeled as `meanQA`.

### [R/](https://github.com/lou-heraut/CARD/tree/main/R) directory
In this directory, you can find all the different functions needed for the aggregation process in CARDs. They are ordered by type of application, but it may take some time to search and understand what is available or not. This is where you can modify or add your own function.

This directory also contains the core functions for [CARD management](https://github.com/lou-heraut/CARD/blob/main/R/CARD_management.R) and [CARD extraction](https://github.com/lou-heraut/CARD/blob/main/R/CARD_process.R), which allow users to interact with the CARD formatting in connection with the [EXstat](https://github.com/lou-heraut/EXstat) package.


### You need a new CARD ?
- **Good Solution** : Search existing request in the issue list and if no one has asked for it, create a new issue.
- **Better Solution** : Along with the issue submission, provide a minimal CARD file with informative metadata filled out.
- **Best Solution** : Create and test a CARD by your own and submit a pull request. This is the fastest way to get a new CARD.


## FAQ
📬 — **I would like an upgrade / I have a question / Need to reach me**  
Feel free to [open an issue](https://github.com/lou-heraut/CARD/issues) ! I’m actively maintaining this project, so I’ll do my best to respond quickly.  
I’m also reachable on my institutional INRAE [email](mailto:louis.heraut@inrae.fr?subject=%5BCARD%5D) for more in-depth discussions.

🛠️ — **I found a bug**  
- *Good Solution* : Search the existing issue list, and if no one has reported it, create a new issue !  
- *Better Solution* : Along with the issue submission, provide a minimal reproducible code sample.  
- *Best Solution* : Fix the issue and submit a pull request. This is the fastest way to get a bug fixed.

🚀 — **Want to contribute ?**  
If you don't know where to start, [open an issue](https://github.com/lou-heraut/CARD/issues).

If you want to try by yourself, why not start by also [opening an issue](https://github.com/lou-heraut/CARD/issues) to let me know you're working on something ? Then:

- Fork this repository  
- Clone your fork locally and make changes (or even better, create a new branch for your modifications)
- Push to your fork and verify everything works as expected
- Open a Pull Request on GitHub and describe what you did and why
- Wait for review
- For future development, keep your fork updated using the GitHub “Sync fork” functionality or by pulling changes from the original repo (or even via remote upstream if you're comfortable with Git). Otherwise, feel free to delete your fork to keep things tidy ! 

If we’re connected through work, why not reach out via email to see if we can collaborate more closely on this repo by adding you as a collaborator !

Refer to the [CONTRIBUTING file](.github/CONTRIBUTING.md) for contribution guidelines and help.


## Code of Conduct
Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

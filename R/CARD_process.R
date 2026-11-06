# Copyright 2021-2025 Louis, Héraut <louis.heraut@inrae.fr>*1
#           2025      David, Dorchies <david.dorchies@inrae.fr>*2
#
# *1 INRAE, UR RiverLy, Villeurbanne, France
# *2 INRAE, UMR G-Eau, Montpellier, France
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


reduce_process = function (data, id, Process,
                           period_default=NULL,
                           suffix=NULL,
                           suffix_delimiter="_",
                           cancel_lim=FALSE,
                           expand_overwrite=NULL,
                           sampling_period_overwrite=NULL,
                           rmNApct=TRUE,
                           rm_duplicates=FALSE,
                           dev=FALSE,
                           verbose=FALSE) {

    if (verbose) {
        print(paste0("Process ", id, "/", length(Process)-1))
    }

    process = Process[[paste0("P", id)]]
    process_names = names(process)
    for (pp in 1:length(process)) {
        assign(process_names[pp], process[[pp]])
    }

    rm ("process")
    gc()

    if (!is.null(expand_overwrite) & id == (length(Process)-1)) {
        expand = expand_overwrite
    }

    if (is.null(sampling_period_overwrite)) {
        if (is.function(sampling_period[[1]])) {
            sampling_period = dplyr::tibble(sp=list(sampling_period[[1]]),
                                            args=sampling_period[2])
        }
    } else {
        sampling_period = sampling_period_overwrite
    }

    if (is.null(period)) {
        period = period_default
    }

    if (cancel_lim) {
        NApct_lim = NULL
        NAyear_lim = NULL
    }

    # EXtraction
    data = EXstat::process_extraction(data=data,
                                      funct=funct,
                                      funct_args=funct_args,
                                      time_step=time_step,
                                      sampling_period=sampling_period,
                                      period=period,
                                      is_date=is_date,
                                      NApct_lim=NApct_lim,
                                      NAyear_lim=NAyear_lim,
                                      Seasons=Seasons,
                                      nameEX=nameEX,
                                      suffix=suffix,
                                      suffix_delimiter=suffix_delimiter,
                                      keep=keep,
                                      compress=compress,
                                      expand=expand,
                                      rmNApct=rmNApct,
                                      rm_duplicates=rm_duplicates,
                                      dev=dev,
                                      verbose=verbose)
    return (data)
}


get_last_Process = function (Process) {
    nProcess = length(Process) - 1
    for (i in 1:nProcess) {
        process = Process[[paste0("P", i)]]
        process_names = names(process)
        for (pp in 1:length(process)) {
            assign(process_names[pp], process[[pp]])
        }
    }
    res = list(compress=compress, time_step=time_step, Seasons=Seasons)
    return (res)
}


split_path = function (path) {
    if (dirname(path) %in% c(".", path)) return(basename(path))
    return(c(basename(path), split_path(dirname(path))))
}


#' @title CARD_extraction
#' @description Extracts variables from time series (for example, the yearly mean of a time series) using CARD parameterization files.
#' @param data Input data format is a [tibble][tibble::tibble()] from the tibble package. It needs to have :
#' * Only one column of [Date][base::Date] that are regularly spaced and unique for each time serie.
#' * If there is more than one time serie, at least one column needs to be of [character][base::character] string for names of time series in order to identify them. If more than one column of identifier is given, they will all be used in order to identify a unique time serie.
#' * At least one column of [numeric][base::numeric] (or [logical][base::logical]) on which the process of variable extraction will be perform. More numerical column can be leave but if they are useless, they will be suppressed.
#'
#' e.g.
#' ```
#' > data
#' A tibble: 201 × 4
#'    time         Q_obs  Q_sim  ID
#'    <date>       <dbl>  <dbl>  <chr>
#' 1   2000-02-10   10     97.8  serie 1
#' 2   2000-02-11   19    -20.5  serie 1
#' 3   2000-02-12   13    -76.9  serie 1
#' 4   2000-02-13   15    -86.0  serie 1
#'     ...
#' 103 2001-01-01  1.3     1988  serie 2
#' 104 2001-01-02  1.2      109  serie 2
#' 105 2001-01-03  1.0       90  serie 2
#' 106 2001-01-04  1.1       91  serie 2
#'     ...
#' ```
#' @param CARD_name A [vector][base::c()] of [character][base::character] strings to specify which variables you want to extract. See [CARD_list_all()] to get the variable names. By default, `c("QA", "QJXA")`. If `NULL`, all the variable will be extracted, so avoid this value except with `extract_only_metadata = TRUE` or your custom `CARD_path` directory.
#' @param CARD_path An optional [character][base::character] string for the path where to search for custom CARDs that have been created by the [CARD_management] function. By default, `NULL` in order to get the default CARD variable parameters.
#' @param period_default A [vector][base::c()] of two [dates][base::Date] (or two unambiguous [character][base::character] strings that can be coerced to [dates][base::Date]) to restrict the period of analysis. As an example, it can be `c("1950-01-01", "2020-12-31")` to select data from the 1st January of 1950 to the end of December of 2020. Some CARD can have a specific `period` parameter that overide this `period_default` argument. The default option is `period_default=NULL`, which considers all available data for each time serie.
#' @param suffix A [character][base::character] string [vector][base::c()] representing suffixes to be appended to the column names of the extracted variables. This parameter allows handling multiple extraction scenarios. For example, a cumbersome case can be to have a unique function to apply to a multiple list of column. It is possible to give `funct=list(QA_obs=mean, QA_sim=mean)` and `funct_args=list(list("Q_obs", na.rm=TRUE), list("Q_sim", na.rm=TRUE))` or simply `funct=list(QA=mean)` and `funct_args=list("Q", na.rm=TRUE)` with `suffix=c("obs", "sim")`. The two approach give the same result. Default `NULL`.
#' @param suffix_delimiter [character][base::character] string specifies the delimiter to use between the variable name and the suffix if not `NULL`. The default is `"_"`.
#' @param cancel_lim A [logical][base::logical] to specify whether to cancel the NA percentage limits in the CARDs. Default is `FALSE`.
#' @param simplify A [logical][base::logical] to specify whether to simplify the extracted data by joining each [tibble][tibble::tibble()] extracted from each CARDs. Usefull when the extracted variable has no temporal extension. Default `"FALSE"`.
#' @param expand_overwrite [logical][base::logical] or `NULL`. If `TRUE`, expand the output [tibble][tibble::tibble()] as a [list][base::list()] of [tibble][tibble::tibble()] for each extracted variable by `suffix`.
#' Default `NULL` to conserve the value specified in the CARDs used.
#' @param sampling_period_overwrite A [character][base::character] string or a [vector][base::c()] of two [character][base::character] strings that will indicate how to sample the data for each time step defined by `time_step`. Hence, the choice of this argument needs to be link with the choice of the time step. For example, for a yearly extraction so if `time_step` is set to `"year"`, `sampling_period` needs to be formated as `%m-%d` (a month - a day of the year) in order to indicate the start of the sampling of data for the current year. More precisly, if `time_step="year"` and `sampling_period="03-19"`, `funct` will be apply on every data from the 3rd march of each year to the 2nd march of the following one. In this way, it is possible to create a sub-year sampling with a [vector][base::c()] of two [character][base::character] strings as `sampling_period=c("02-01", "07-31")` in order to process data only if the date is between the 1st february and the 31th jully of each year.
#' *not available for now* For a monthly (or seasonal) extraction, `sampling_period` needs to give only day in each month, so for example `sampling_period="10"` to extract data from the 10th of each month to the 9th of each following month.
#' Default `NULL` to conserve the value specified in the CARDs used.
#' @param rmNApct [logical][base::logical]. Should the `NApct` column, which shows the percentage of missing values in the output, be removed ? Default `TRUE`.
#' @param rm_duplicates [logical][base::logical]. Should duplicate time series values be automatically removed ? Default `FALSE`.
#' @param extract_only_metadata [logical][base::logical]. If TRUE, only metadata of CARD will be extracted. In that case, use `data=NULL`. Default FALSE.
#' @param dev [logical][base::logical] If `TRUE`, development mode is enabled. Default is `FALSE`.
#' @param verbose [logical][base::logical]. Should intermediate messages be printed during the execution of the function ? Default `FALSE`.
#' @return A [list][base::list()] of two [tibbles][tibble::tibble()].
#' - The `dataEX` [tibble][tibble::tibble()], which contains the extracted variable, or a named [list][base::list()] of [tibbles][tibble::tibble()] for each extracted variable if `expand_overwrite` is `TRUE`.
#' - The `metaEX` [tibble][tibble::tibble()], which contains the metadata of the extraction from CARDs.
#' @seealso
#' 1. [CARD_list_all()] list all available CARD.
#' 2. [CARD_management()] for managing CARD parameterization files.
#' - 3. [CARD_extraction()] for extracting variables using CARD.
#' @examples
#' library(CARD)
#'
#' # Get all the available variables
#' metaEX_all = CARD_list_all()
#' metaEX_all
#'
#' # Create mock data
#' Start = as.Date("2001-03-02")
#' End = as.Date("2024-11-30")
#' Date = seq.Date(Start, End, by="day")
#' data = dplyr::tibble(time=Date,
#'                      Q=as.numeric(Date),
#'                      id="serie 1")
#'
#' # Do a direct extraction
#' res = CARD_extraction(data, CARD_name=c("QA", "QMNA"), verbose=TRUE)
#' res
#'
#' # Or find the closest CARD variable that interests you
#' CARD_management(CARD_name=c("VCN10-5"),
#'                 CARD_path="CARD-WIP",
#'                 overwrite=TRUE)
#' # Personalise it in the created  `"CARD-WIP"` directory (for example change the return period)
#' # And perform a custom extraction
#' res = CARD_extraction(data, CARD_name=NULL,
#'                       CARD_path="CARD-WIP",
#'                       verbose=TRUE)
#' res$dataEX
#' @export
#' @md
CARD_extraction = function (data,
                            CARD_name=c("QA", "QJXA"),
                            CARD_path=NULL,
                            period_default=NULL,
                            suffix=NULL,
                            suffix_delimiter="_",
                            cancel_lim=FALSE,
                            simplify=FALSE,
                            expand_overwrite=NULL,
                            sampling_period_overwrite=NULL,
                            rmNApct=TRUE,
                            rm_duplicates=FALSE,
                            extract_only_metadata=FALSE,
                            dev=FALSE,
                            verbose=FALSE) {

    CARD_path_system = system.file(package="CARD")

    if (is.null(CARD_path)) {
        CARD_path = file.path(CARD_path_system, "__all__")
    }

    script_to_analyse = list.files(CARD_path,
                                   pattern=".R$",
                                   recursive=TRUE,
                                   include.dirs=FALSE,
                                   full.names=FALSE)

    if (!is.null(CARD_name)) {
        script_to_analyse =
            script_to_analyse[gsub("^[[:digit:]]+[_]", "",
                                   basename(script_to_analyse)) %in%
                              paste0(CARD_name, ".R")]
    }

    script_to_analyse = script_to_analyse[!grepl("__default__.R",
                                                 script_to_analyse)]

    topic_to_analyse = list.dirs(CARD_path,
                                 recursive=TRUE, full.names=FALSE)
    topic_to_analyse = topic_to_analyse[topic_to_analyse != ""]
    topic_to_analyse = gsub('.*_', '', topic_to_analyse)

    variable_analyse = c()

    nScript = length(script_to_analyse)
    metaEX = dplyr::tibble()
    dataEX = replicate(nScript, list(NULL))

    for (ss in 1:nScript) {
        script = script_to_analyse[ss]

        Process_default = sourceProcess(
            file.path(CARD_path_system, "__default__.R"))

        Process = sourceProcess(
            file.path(CARD_path, script),
            default=Process_default)

        principal = Process$P
        principal_names = names(principal)
        for (pp in 1:length(principal)) {
            assign(principal_names[pp], principal[[pp]])
        }

        variable = variable_en
        split_script = split_path(script)

        if (any(variable %in% variable_analyse)) {
            next
        }

        variable_analyse = c(variable_analyse, variable)

        if (verbose) {
            print(paste0('Computes ', Process$P$variable_en))
        }

        nProcess = length(Process) - 1

        if (!extract_only_metadata) {
            dataEX[[ss]] =
                purrr::reduce(1:nProcess,
                              reduce_process,
                              Process=Process,
                              period_default=period_default,
                              suffix=suffix,
                              suffix_delimiter=suffix_delimiter,
                              cancel_lim=cancel_lim,
                              expand_overwrite=expand_overwrite,
                              sampling_period_overwrite=sampling_period_overwrite[[ss]],
                              rmNApct=rmNApct,
                              rm_duplicates=rm_duplicates,
                              dev=dev,
                              verbose=verbose,
                              .init=data)


            if (tibble::is_tibble(dataEX[[ss]])) {
                dataEX[[ss]] = list(dataEX[[ss]])
                if (!simplify) {
                    variable = paste0(variable, collapse=" ")
                    names(dataEX[[ss]]) = variable
                }
            }
        }

        res = get_last_Process(Process)
        rm ("Process")
        gc()

        compress = res$compress
        time_step = res$time_step
        Seasons = res$Seasons

        if (!is.null(sampling_period_overwrite[[ss]])) {
            sampling_period_en = sampling_period_overwrite[[ss]]
            sampling_period_fr = sapply(
                lapply(strsplit(sampling_period_en, "-"), rev),
                paste0, collapse="-")
            sampling_period_en = paste0(sampling_period_en,
                                        collapse=", ")
            sampling_period_fr = paste0(sampling_period_fr,
                                        collapse=", ")
        }

        metaEX =
            dplyr::bind_rows(
                       metaEX,
                       dplyr::tibble(
                                  ### English ___
                                  variable_en=variable_en,
                                  unit_en=unit_en,
                                  name_en=name_en,
                                  description_en=description_en,
                                  method_en=method_en,
                                  sampling_period_en=sampling_period_en,
                                  topic_en=topic_en,
                                  ### French ___
                                  variable_fr=variable_fr,
                                  unit_fr=unit_fr,
                                  name_fr=name_fr,
                                  description_fr=description_fr,
                                  method_fr=method_fr,
                                  sampling_period_fr=sampling_period_fr,
                                  topic_fr=topic_fr,
                                  ### Global ___
                                  is_experimental=is_experimental,
                                  input_vars=input_vars,
                                  source=source,
                                  preferred_sampling_period=preferred_sampling_period,
                                  is_date=is_date,
                                  to_normalise=to_normalise,
                                  palette=palette,
                                  script_path=script))
    }
    rm ("data")
    gc()

    if ("preferred_sampling_period" %in% names(metaEX)) {
        metaEX = dplyr::relocate(metaEX, preferred_sampling_period, .after=input_vars)
    }
    if ("source" %in% names(metaEX)) {
        metaEX = dplyr::relocate(metaEX, source, .after=input_vars)
    }
    if ("is_experimental" %in% names(metaEX)) {
        metaEX = dplyr::relocate(metaEX, is_experimental, .before=input_vars)
    }

    if (extract_only_metadata) {
        return (list(metaEX=metaEX))

    } else {
        dataEX = unlist(dataEX, recursive=FALSE)
        if (simplify) {
            by = names(dplyr::select(dataEX[[1]],
                                     dplyr::where(is.character)))
            dataEX = purrr::reduce(.x=dataEX,
                                   .f=dplyr::full_join,
                                   by=by)
        }
        return (list(metaEX=metaEX, dataEX=dataEX))
    }
}


#' @title sourceProcess
#' @description Allows read CARD with is formatism and convert it to a `Process` variable that explain all the step necessary for the extraction of [process_extraction()].
#'
#' @param path  A [character][base::character] string as a path to the CARD file.
#' @param default The default process loaded by `Process_default = sourceProcess(file.path(CARD_path, "__default__.R"))` to load the default parameters of every extraction process. Default `NULL`.
#' @return A `Process` variable which is a list of general parameters, and sub list for each extraction process parameters.
#' @seealso
#' - [process_extraction()] for extracting variables.
#' - [process_trend()] for performing trend analysis on extracted variables.
#' - [CARD_management()] for managing CARD parameterization files.
#' - [CARD_extraction()] for extracting variables using CARD parameterization files.
#'
#' @examples
#' \dontrun{
#' Process_default = sourceProcess(path="path/to/CARD/__default__.R")
#' Process = sourceProcess(path="path/to/CARD/script.R",
#'                         default=Process_default)
#' }
#' @export
#' @md
sourceProcess = function (path, default=NULL) {
    CARD = new.env()
    source(path, local=CARD, encoding='UTF-8')
    lsCARD = ls(envir=CARD)

    Process_def = lsCARD[grepl("P[.]", lsCARD)]
    Process = lapply(Process_def, get, envir=CARD)
    names(Process) = gsub("P[.]", "", Process_def)
    Process = list(Process)
    names(Process) = "P"

    if (!is.null(default)) {
        nOK = !(names(default$P) %in% names(Process$P))
        Process$P = append(Process$P, default$P[nOK])
    }

    process_allAtt = lsCARD[grepl("P[[:digit:]][.]", lsCARD)]
    process_allNames = stringr::str_extract(process_allAtt,
                                            "P[[:digit:]]")
    process_names = process_allNames[!duplicated(process_allNames)]
    Nprocess = length(process_names)

    for (i in 1:Nprocess) {
        process_name = paste0("P", i)
        IDprocess = grepl(paste0(process_name, "[.]"),
                          process_allAtt)

        process_att = process_allAtt[IDprocess]
        process = lapply(process_att, get, envir=CARD)

        names(process) = gsub("P[[:digit:]][.]", "",
                              process_att)
        process = list(process)
        names(process) = process_name

        if (!is.null(default)) {
            nOK = !(names(default$P1) %in%
                    names(process[[process_name]]))
            process[[process_name]] =
                append(process[[process_name]], default$P1[nOK])
        }
        Process = append(Process, process)
    }

    rm (list=ls(envir=CARD), envir=CARD)
    return (Process)
}

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


#' @title CARD_list_all
#' @description List all the CARD parametrization files in a [tibble][tibble::tibble()] to get all the metadata of the aggregation variables available.
#' @seealso
#' - 1. [CARD_list_all()] list all available CARD.
#' 2. [CARD_management()] for managing CARD parameterization files.
#' 3. [CARD_extraction()] for extracting variables using CARD.
#' @examples
#' # Get all the available variables
#' metaEX_all = CARD_list_all()
#' # And why note filter it by topic
#' dplyr::filter(metaEX_all, grepl("Low Flow", topic_en))
#' @export
#' @md
CARD_list_all = function (include_experimental=FALSE) {
    inst_dir = system.file(package="CARD")
    CARD_path_all = file.path(inst_dir, "extdata", "metaEX_all.csv")
    metaEX = dplyr::tibble(read.csv(CARD_path_all))
    if (!include_experimental) {
        metaEX = dplyr::filter(metaEX, !is_experimental)    
    }
    return (metaEX)
}


#' @title CARD_management
#' @description Manage your different sets of variables to extract. For CARD advanced users, this function manages the CARD directory structure by performing automatic file operations to get the CARD parameterization files to your wanted directory in order to custom them or create yours to use them in a second step with [CARD_extraction()]. If you want to submit request for new CARD see the [GitHub repo](https://github.com/lou-heraut/CARD)<https://github.com/lou-heraut/CARD>.
#' @param CARD_name A [vector][base::c()] of [character][base::character] strings to specify which variables you want to extract. See [CARD_list_all()] to get the variable names. By default, `c("QA", "QJXA")`. If `NULL`, all the variable will be extracted, so avoid this value except with `extract_only_metadata = TRUE`.
#' @param CARD_path An optional [character][base::character] string for the path where to search for custom CARDs that have been created by the [CARD_management] function. By default, `NULL` in order to get the default CARD variable parameters.
#' @param add_id [logical][base::logical]. If `TRUE`, numerical IDs will be added to the start of the copied and pasted CARD names to maintain the input order. Default is `TRUE`.
#' @param overwrite [logical][base::logical]. If `TRUE`, existing CARD files in the analysis directory will be overwritten. Default is `TRUE`.
#' @param verbose [logical][base::logical]. Should intermediate messages be printed during the execution of the function ? Default `FALSE`.
#' @return Selected CARD parameterization files will be created in the `CARD_path` directory.
#' @seealso
#' 1. [CARD_list_all()] list all available CARD.
#' - 2. [CARD_management()] for managing CARD parameterization files.
#' 3. [CARD_extraction()] for extracting variables using CARD.
#' @examples
#' # Get the QA and QMNA CARD variables in your local CARD_path directory
#' CARD_management(CARD_name=c("QA", "QMNA"),
#'                 CARD_path="CARD-WIP",
#'                 overwrite = TRUE)
#' @export
#' @md
CARD_management = function (CARD_name=c("QA", "QJXA"),
                            CARD_path="./WIP",
                            add_id=TRUE,
                            overwrite=FALSE,
                            verbose=FALSE) {

    CARD_path_system = system.file(package="CARD")
    
    if (dir.exists(CARD_path)) {
        if (overwrite) {
            unlink(CARD_path, recursive=TRUE)
            dir.create(CARD_path)
        } else {
            stop(paste0("Directory ", CARD_path, " already exists, use the parameter `overwrite=TRUE` if you want to overwrite it."))
        }
    } else {
        dir.create(CARD_path)
    }

    source_dir = file.path(CARD_path_system, "__all__")

    Paths = list.files(source_dir, recursive=TRUE, full.names=TRUE)
    Files = basename(Paths)
    names(Paths) = gsub("[.].*", "", Files)

    if (!is.list(CARD_name)) {
        CARD_name = list(CARD_name)
    }
    
    manage_hide = function(CARD_name, CARD_path, id_dir=1) {
        if (is.list(CARD_name)) {
            for (i in 1:length(CARD_name)) {

                X = CARD_name[[i]]
                X_name = names(CARD_name)[i]

                if (is.character(X) | is.list(X)) {
                    if (!is.null(X_name)) {
                        if (nchar(X_name) > 0) {
                            CARD_dir_tmp = paste0(formatC(id_dir,
                                                          width=3,
                                                          flag="0"),
                                                  "_",
                                                  X_name)
                        } else {
                            CARD_dir_tmp = X_name
                        }
                        CARD_path_tmp = file.path(CARD_path,
                                                  CARD_dir_tmp)
                    } else {
                        CARD_path_tmp = CARD_path
                    }

                    if (!dir.exists(CARD_path_tmp)) {
                        dir.create(CARD_path_tmp)
                        id_dir = id_dir + 1
                    }
                }
                
                if (is.character(X)) {
                    nCARD = length(X)
                    for (j in 1:nCARD) {
                        card_name = X[j]
                        from = Paths[names(Paths) == card_name]
                        id_card_name = paste0(formatC(j, width=3,
                                                      flag="0"),
                                              "_",
                                              card_name, ".R")
                        to = file.path(CARD_path_tmp, id_card_name)
                        file.copy(from, to)
                    }
                }

                manage_hide(X, CARD_path_tmp, id_dir=1)
            }
        }
    }
    manage_hide(CARD_name, CARD_path)
}

remind = function (args) {
    print("PARAMETERS:")
    n = length(args)
    args_name = names(args)
    for (i in 1:n) {
        print(paste0("    --", args_name[i], " ",
                     paste0(args[[i]], collapse=" ")))
    }
}


# CARD_path = "/home/louis/Documents/bouleau/INRAE/project/CARD_project/CARD"
# CARD_tmp = "/home/louis/Téléchargements/clara"
# CARD_dir = "analyse_1"
# CARD_name = c("QMNA-5", "BFI_Wal")

# CARD_management(CARD_path=CARD_path,
#                 CARD_tmp=NULL,
#                 CARD_dir=CARD_dir,
#                 CARD_name=CARD_name,
#                 layout=c(CARD_dir, "[", "QMNA-5", "BFI_Wal", "]"),
#                 verbose=TRUE)

# Exécute les 5 fiches de référence via le package R CARD (fiches .R du repo)
# et écrit les dataEX en CSV pour comparaison avec CARD_py.

library(CARD)

args = commandArgs(trailingOnly=TRUE)
tests_dir = dirname(sub("--file=", "", grep("--file=", commandArgs(), value=TRUE)))
repo = normalizePath(file.path(tests_dir, "..", ".."))

data = dplyr::tibble(read.csv(file.path(tests_dir, "data", "test_data.csv")))
data$date = as.Date(data$date)

CARD_name = c("QA", "median-QJC5", "tQJXA", "dtLF", "delta-endLF_H")

res = CARD_extraction(data,
                      CARD_name=CARD_name,
                      CARD_path=file.path(repo, "inst", "__all__"),
                      verbose=TRUE)

out_dir = file.path(tests_dir, "data", "R_out")
dir.create(out_dir, showWarnings=FALSE, recursive=TRUE)

for (name in names(res$dataEX)) {
    safe = gsub("[ ]", "__", name)
    write.csv(res$dataEX[[name]],
              file.path(out_dir, paste0(safe, ".csv")),
              row.names=FALSE)
    print(paste0("written: ", safe))
}

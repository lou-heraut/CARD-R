# Exécute TOUTES les fiches R (inst/__all__) sur le jeu de test et écrit
# les sorties par fiche dans tests/data/R_corpus/<fiche>/, plus un log
# de statut _status.csv.

library(CARD)

tests_dir = dirname(sub("--file=", "", grep("--file=", commandArgs(), value=TRUE)))
repo = normalizePath(file.path(tests_dir, "..", ".."))
CARD_path = file.path(repo, "inst", "__all__")
out_root = file.path(tests_dir, "data", "R_corpus")
dir.create(out_root, showWarnings=FALSE, recursive=TRUE)

data = dplyr::tibble(read.csv(file.path(tests_dir, "data", "test_data.csv")))
data$date = as.Date(data$date)

scripts = list.files(CARD_path, pattern="[.]R$", recursive=TRUE)
card_names = unique(gsub("[.]R$", "", basename(scripts)))

status = data.frame(card=character(), status=character(),
                    n_out=integer(), message=character())

for (name in card_names) {
    out_dir = file.path(out_root, name)
    res = tryCatch({
        r = CARD_extraction(data, CARD_name=name,
                            CARD_path=CARD_path, verbose=FALSE)
        dir.create(out_dir, showWarnings=FALSE)
        n_out = 0
        for (vn in names(r$dataEX)) {
            safe = gsub("[ /]", "__", vn)
            write.csv(r$dataEX[[vn]],
                      file.path(out_dir, paste0(safe, ".csv")),
                      row.names=FALSE)
            n_out = n_out + 1
        }
        list(status="ok", n_out=n_out, message="")
    }, error=function(e) {
        list(status="error", n_out=0L,
             message=substr(conditionMessage(e), 1, 200))
    })
    status = rbind(status,
                   data.frame(card=name, status=res$status,
                              n_out=res$n_out, message=res$message))
    cat(sprintf("[%s] %s\n", res$status, name))
    # source() de sourceProcess fuit des connexions : sans fermeture, R
    # atteint sa limite (~125) au fil du corpus
    closeAllConnections()
}

write.csv(status, file.path(out_root, "_status.csv"), row.names=FALSE)
cat(sprintf("\n%d fiches : %d ok, %d erreurs\n",
            nrow(status), sum(status$status == "ok"),
            sum(status$status == "error")))

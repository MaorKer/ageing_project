# Export WPP 2024 age-specific death rates (mx) to parquet.
#
# Output: data/raw/wpp_mx.parquet with columns:
#   iso3, year, sex, age, mx
#
# Notes:
# - This script relies on the `wpp2024` R package.
# - The exact column names in wpp2024 objects may change; this script tries to
#   auto-detect reasonable defaults and will print helpful errors if it cannot.
#
# Run:
#   Rscript scripts/30_export_wpp_from_r.R

suppressPackageStartupMessages({
  library(dplyr)
})

if (!requireNamespace("wpp2024", quietly = TRUE)) {
  stop("Missing R package 'wpp2024'. Install it, e.g.: install.packages('wpp2024') or follow its GitHub instructions.")
}

# wpp2024 may ship datasets that are loaded via `data()` (not necessarily exported
# into the namespace). Prefer mx1dt; fall back to mx* datasets.
mx_name <- NULL
ds <- tryCatch(utils::data(package = "wpp2024")$results, error = function(e) NULL)
if (!is.null(ds) && "Item" %in% colnames(ds)) {
  items <- as.character(ds[, "Item"])
  if ("mx1dt" %in% items) {
    mx_name <- "mx1dt"
  } else if ("mx5dt" %in% items) {
    mx_name <- "mx5dt"
  } else {
    mx_candidates <- items[grepl("^mx", items)]
    if (length(mx_candidates) > 0) {
      mx_name <- mx_candidates[[1]]
    }
  }
}

if (is.null(mx_name)) {
  # Last resort: try mx1dt by name anyway.
  mx_name <- "mx1dt"
}

ok <- tryCatch({
  utils::data(list = mx_name, package = "wpp2024", envir = environment())
  TRUE
}, error = function(e) FALSE)

if (!ok || !exists(mx_name, envir = environment())) {
  stop(paste0(
    "Could not load wpp2024 dataset '", mx_name, "'. ",
    "Run `data(package='wpp2024')` and update scripts/30_export_wpp_from_r.R to point at the correct mx dataset."
  ))
}

mx <- as.data.frame(get(mx_name, envir = environment()))

cat("Loaded wpp2024 mx table with columns:\n")
print(names(mx))

col_pick <- function(candidates) {
  hit <- candidates[candidates %in% names(mx)]
  if (length(hit) == 0) return(NA_character_)
  hit[[1]]
}

iso_col <- col_pick(c("iso3", "ISO3", "iso3_code", "countryiso3code", "country_code", "iso3c"))
year_col <- col_pick(c("year", "Year", "time", "Time"))
sex_col <- col_pick(c("sex", "Sex"))
age_col <- col_pick(c("age", "Age", "age_start", "AgeStart", "x"))
mx_col  <- col_pick(c("mx", "nMx", "value", "Value"))

# Common wide format in wpp2024: mxM, mxF, mxB columns.
mxm_col <- col_pick(c("mxM", "mXm", "MXM"))
mxf_col <- col_pick(c("mxF", "mXf", "MXF"))
mxb_col <- col_pick(c("mxB", "mXb", "MXB"))

if (is.na(year_col)) {
  stop("Could not infer year column from the wpp2024 mx dataset. Please edit scripts/30_export_wpp_from_r.R and map columns explicitly.")
}

if (is.na(iso_col)) {
  stop("Could not infer iso3 column. If wpp2024 uses numeric location codes, add a join to its location mapping and produce ISO3.")
}

# If dataset is wide by sex (mxM/mxF/mxB), reshape without extra deps.
if (is.na(sex_col) || is.na(mx_col)) {
  if (is.na(mxm_col) || is.na(mxf_col) || is.na(mxb_col)) {
    stop("Could not infer sex/mx columns (long) or mxM/mxF/mxB columns (wide). Please edit scripts/30_export_wpp_from_r.R.")
  }
  base_cols <- mx %>%
    rename(
      iso3 = !!iso_col,
      year = !!year_col
    )
  if (!is.na(age_col) && age_col %in% names(base_cols)) {
    base_cols <- base_cols %>% rename(age = !!age_col)
  } else if (all(c("age_start", "age_end") %in% names(base_cols))) {
    base_cols <- base_cols %>% mutate(age = (age_start + age_end) / 2.0)
  } else {
    stop("Could not infer age column. Ensure output includes 'age' or ('age_start','age_end').")
  }

  out_m <- base_cols %>% mutate(sex = "Male", mx = .data[[mxm_col]])
  out_f <- base_cols %>% mutate(sex = "Female", mx = .data[[mxf_col]])
  out_b <- base_cols %>% mutate(sex = "Both", mx = .data[[mxb_col]])
  out <- bind_rows(out_f, out_m, out_b)
} else {
  out <- mx %>%
    rename(
      iso3 = !!iso_col,
      year = !!year_col,
      sex = !!sex_col,
      mx = !!mx_col
    )
}

if (!is.na(age_col) && age_col %in% names(out)) {
  out <- out %>% rename(age = !!age_col)
} else if (all(c("age_start", "age_end") %in% names(out))) {
  out <- out %>% mutate(age = (age_start + age_end) / 2.0)
} else {
  stop("Could not infer age column. Ensure output includes 'age' or ('age_start','age_end').")
}

out <- out %>%
  mutate(
    iso3 = toupper(as.character(iso3)),
    year = as.integer(as.character(year)),
    sex = as.character(sex),
    age = as.numeric(as.character(age)),
    mx = as.numeric(as.character(mx))
  ) %>%
  filter(!is.na(iso3), !is.na(year), !is.na(sex), !is.na(age), !is.na(mx))

# If "iso3" isn't actually ISO3 (common when wpp2024 uses numeric UN codes),
# attempt mapping from country name -> iso3c.
bad_iso <- out %>% filter(nchar(iso3) != 3 | !grepl("^[A-Z]{3}$", iso3))
if (nrow(bad_iso) > 0) {
  if (!("name" %in% names(out))) {
    stop("The inferred 'iso3' values do not look like ISO3 codes and there is no 'name' column to map from.")
  }
  if (!requireNamespace("countrycode", quietly = TRUE)) {
    stop("Install R package 'countrycode' to map WPP country names to ISO3 (e.g., install.packages('countrycode')).")
  }
  iso3_strict <- countrycode::countrycode(out$name, origin = "country.name", destination = "iso3c", warn = FALSE)
  iso3_regex <- countrycode::countrycode(out$name, origin = "country.name.en.regex", destination = "iso3c", warn = FALSE)
  out$iso3 <- toupper(ifelse(is.na(iso3_strict), iso3_regex, iso3_strict))
  out <- out %>% filter(!is.na(iso3))
}

out <- out %>%
  select(iso3, year, sex, age, mx) %>%
  filter(!is.na(iso3), !is.na(year), !is.na(sex), !is.na(age), !is.na(mx))

# Optional: filter to project.yml countries/years/sexes if yaml is available.
cfg_path <- "config/project.yml"
if (file.exists(cfg_path) && requireNamespace("yaml", quietly = TRUE)) {
  cfg <- yaml::read_yaml(cfg_path)
  start_year <- cfg$project$start_year
  end_year <- cfg$project$end_year
  sexes_keep <- cfg$project$sexes
  countries_keep <- unique(c(
    vapply(cfg$cases, function(x) x$iso3, character(1)),
    unlist(lapply(cfg$cases, function(x) x$controls))
  ))
  out <- out %>%
    filter(
      iso3 %in% countries_keep,
      year >= start_year,
      year <= end_year,
      sex %in% sexes_keep
    )
  cat("Filtered to config/project.yml: ", length(countries_keep), "countries,", start_year, "-", end_year, "\n")
} else {
  cat("Note: Install R package 'yaml' to auto-filter to config/project.yml.\n")
}

dir.create("data/raw", recursive = TRUE, showWarnings = FALSE)

# Always write CSV (no extra dependencies).
utils::write.csv(out, "data/raw/wpp_mx.csv", row.names = FALSE)
cat("Wrote data/raw/wpp_mx.csv with", nrow(out), "rows\n")

# If arrow is installed, also write parquet for faster downstream reads.
if (requireNamespace("arrow", quietly = TRUE)) {
  arrow::write_parquet(out, "data/raw/wpp_mx.parquet")
  cat("Wrote data/raw/wpp_mx.parquet with", nrow(out), "rows\n")
} else {
  cat("Note: R package 'arrow' not installed; skipped parquet output.\n")
}

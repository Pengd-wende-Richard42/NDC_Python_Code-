from pathlib import Path
from functools import reduce

import numpy as np
import pandas as pd
import country_converter as coco


working_dir = Path(r"C:\Users\richm\Desktop\NDC DATA NEW\NDC Completed")
Final_dir = Path(r"C:\Users\richm\Desktop\NDC DATA NEW\NDC Completed\Final Data")

year_start = 1990
year_end = 2050


# =========================================================
# Fonctions utilitaires
# =========================================================

def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie les colonnes texte pour éviter les problèmes à l'export Stata.
    """
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(lambda x: None if pd.isna(x) else str(x).strip())
            df[col] = df[col].replace("", None)

            if df[col].isna().all():
                df[col] = [""] * len(df)

            df[col] = df[col].astype(object)

    return df


def force_numeric(series: pd.Series) -> pd.Series:
    """
    Conversion robuste vers numérique.
    """
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    s = series.astype(str).str.strip()

    s = s.replace(
        {
            "": np.nan,
            " ": np.nan,
            "NA": np.nan,
            "N/A": np.nan,
            "n/a": np.nan,
            "nan": np.nan,
            "None": np.nan,
            ".": np.nan,
        }
    )

    s = (
        s.str.replace("\xa0", "", regex=False)
         .str.replace("%", "", regex=False)
         .str.replace(" ", "", regex=False)
         .str.replace(",", ".", regex=False)
    )

    s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
    s = s.replace("", np.nan)

    return pd.to_numeric(s, errors="coerce")


# =========================================================
# NDC
# =========================================================

def build_ndc_dataset():
    input_file = working_dir / "NDC.xlsx"
    output_file = working_dir / "NDC.dta"

    ndc_types = ["INDC", "First_NDC", "Second_NDC", "Third_NDC"]

    df = pd.read_excel(input_file, engine="openpyxl")

    df.columns = (
        df.columns.astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )

    df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]

    rename_map = {
        "Country": "country",
        "NDCs_number": "ndcnum",
        "Submission-date": "subdate",
        "Target in percent": "tgt_pct",
        "Target_in_value_GgCO₂eq": "tgt_ggco2",
        "Unconditional_target in percent": "untgt_pct",
        "Unconditional_target in value_GgCO₂eq": "untgt_gg",
        "Conditional_target in percent": "ctgt_pct",
        "Conditional_target in value_GgCO₂eq": "ctgt_gg",
        "interim_target in percent": "itgt_pct",
        "Reference": "ref",
        "Base_year": "baseyr",
        "Target_year": "tgtyr",
        "interim_target_year": "itgtyr",
        "Timeframe for implementation": "timeimpl",
        "Neutrality": "neut",
        "Neutrality_year": "neutyr",
        "Neutrality-target in percent": "neut_pct",
        "Neutrality target in value": "neut_val",
        "Sectors": "sectors",
        "Sectoral Policies": "secpol",
        "Mitigation_policies": "mitpol",
        "Target_type": "tgttype",
        "Conditional to external support": "extsup",
        "Adaptation included": "adaptinc",
        "GHG_target_type": "ghgtype",
        "Financial_Mitigation": "finmit",
        "Financial_adaptation": "finadapt",
        "Non financial support needs": "nonfinsup",
        "Additional infomation": "addinfo",
    }

    df = df.rename(columns=rename_map)

    required_cols = ["country", "ndcnum"]
    missing_required = [c for c in required_cols if c not in df.columns]
    if missing_required:
        raise ValueError(f"Colonnes manquantes dans NDC : {missing_required}")

    df["country"] = df["country"].astype(str).str.strip()

    country_for_iso = df["country"].replace({"European Union (27)": "European Union"})
    cc = coco.CountryConverter()

    df["iso3"] = cc.convert(names=country_for_iso, to="ISO3", not_found=np.nan)
    df.loc[df["country"].eq("European Union (27)"), "iso3"] = "EUU"

    numeric_vars = [
        "tgt_pct",
        "tgt_ggco2",
        "untgt_pct",
        "untgt_gg",
        "ctgt_pct",
        "ctgt_gg",
        "itgt_pct",
        "baseyr",
        "tgtyr",
        "itgtyr",
        "neut",
        "neutyr",
        "neut_pct",
        "neut_val",
        "extsup",
        "adaptinc",
    ]

    for col in numeric_vars:
        if col in df.columns:
            df[col] = force_numeric(df[col])

    vars_to_rename = [
        "subdate",
        "tgt_pct",
        "tgt_ggco2",
        "untgt_pct",
        "untgt_gg",
        "ctgt_pct",
        "ctgt_gg",
        "itgt_pct",
        "ref",
        "baseyr",
        "tgtyr",
        "itgtyr",
        "timeimpl",
        "neut",
        "neutyr",
        "neut_pct",
        "neut_val",
        "sectors",
        "secpol",
        "mitpol",
        "tgttype",
        "extsup",
        "adaptinc",
        "ghgtype",
        "finmit",
        "finadapt",
        "nonfinsup",
        "addinfo",
    ]

    suffix_map = {
        "INDC": "indc",
        "First_NDC": "n1",
        "Second_NDC": "n2",
        "Third_NDC": "n3",
    }

    base_labels = {
        "country": "Country name",
        "iso3": "ISO3 country code",
        "subdate": "Submission date",
        "tgt_pct": "Target in percent",
        "tgt_ggco2": "Target in value GgCO2eq",
        "untgt_pct": "Unconditional target in percent",
        "untgt_gg": "Unconditional target in value GgCO2eq",
        "ctgt_pct": "Conditional target in percent",
        "ctgt_gg": "Conditional target in value GgCO2eq",
        "itgt_pct": "Interim target in percent",
        "ref": "Reference",
        "baseyr": "Base year",
        "tgtyr": "Target year",
        "itgtyr": "Interim target year",
        "timeimpl": "Timeframe for implementation",
        "neut": "Neutrality",
        "neutyr": "Neutrality year",
        "neut_pct": "Neutrality target in percent",
        "neut_val": "Neutrality target in value",
        "sectors": "Sectors",
        "secpol": "Sectoral policies",
        "mitpol": "Mitigation policies",
        "tgttype": "Target type",
        "extsup": "Conditional to external support",
        "adaptinc": "Adaptation included",
        "ghgtype": "GHG target type",
        "finmit": "Financial mitigation",
        "finadapt": "Financial adaptation",
        "nonfinsup": "Non financial support needs",
        "addinfo": "Additional information",
    }

    cycle_dfs = []
    final_var_labels = {
        "country": "Country name",
        "iso3": "ISO3 country code"
    }

    for ndc in ndc_types:
        temp_df = df[df["ndcnum"] == ndc].copy()
        suf = suffix_map[ndc]

        keep_cols = ["country", "iso3"] + [c for c in vars_to_rename if c in temp_df.columns]
        temp_df = temp_df[keep_cols].copy()

        dup_mask = temp_df.duplicated(subset=["country", "iso3"], keep=False)
        if dup_mask.any():
            print(f"\nDoublons détectés dans {ndc} sur country-iso3 :")
            print(temp_df.loc[dup_mask, ["country", "iso3"]].sort_values(["country", "iso3"]))
            temp_df = temp_df.drop_duplicates(subset=["country", "iso3"], keep="first")

        rename_dict = {}
        for col in vars_to_rename:
            if col in temp_df.columns:
                rename_dict[col] = f"{col}_{suf}"

        temp_df = temp_df.rename(columns=rename_dict)

        for old_col, new_col in rename_dict.items():
            final_var_labels[new_col] = f"{base_labels.get(old_col, old_col)} ({ndc})"

        numeric_cols_in_temp = [rename_dict[col] for col in numeric_vars if col in rename_dict]

        for col in temp_df.columns:
            if col not in numeric_cols_in_temp:
                temp_df[col] = temp_df[col].apply(lambda x: None if pd.isna(x) else str(x).strip())
                temp_df[col] = temp_df[col].replace("", None)

                if temp_df[col].isna().all():
                    temp_df[col] = [""] * len(temp_df)

                temp_df[col] = temp_df[col].astype(object)

        cycle_dfs.append(temp_df)

    merged_df = reduce(
        lambda left, right: pd.merge(left, right, on=["country", "iso3"], how="outer"),
        cycle_dfs
    )

    merged_df = merged_df.sort_values(["country", "iso3"]).reset_index(drop=True)
    merged_df = clean_text_columns(merged_df)

    merged_df.to_stata(
        output_file,
        write_index=False,
        version=118,
        variable_labels=final_var_labels
    )

    print(f"\nFichier NDC sauvegardé : {output_file}")
    return merged_df, final_var_labels


# =========================================================
# EDGAR
# =========================================================

def build_edgar_dataset():
    input_file = working_dir / "EDGAR_AR5_GHG_1970_2024.xlsx"
    output_file = working_dir / "EDGAR_2025_GHG.dta"
    sheet_name = "TOTALS BY COUNTRY"

    preview = pd.read_excel(
        input_file,
        sheet_name=sheet_name,
        header=None,
        engine="openpyxl"
    )

    header_row = None
    for i in range(len(preview)):
        row_values = preview.iloc[i].astype(str).str.strip().tolist()
        if "IPCC_annex" in row_values and "Country_code_A3" in row_values:
            header_row = i
            break

    if header_row is None:
        raise ValueError("Impossible de détecter la ligne d'en-tête dans EDGAR.")

    df = pd.read_excel(
        input_file,
        sheet_name=sheet_name,
        header=header_row,
        engine="openpyxl"
    )

    df.columns = (
        df.columns.astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )

    required_cols = ["IPCC_annex", "Country_code_A3"]
    missing_required = [c for c in required_cols if c not in df.columns]
    if missing_required:
        raise ValueError(f"Colonnes manquantes dans EDGAR : {missing_required}")

    year_cols = [c for c in df.columns if str(c).startswith("Y_")]
    if not year_cols:
        raise ValueError("Aucune colonne annuelle Y_#### n'a été trouvée dans EDGAR.")

    df = df[["IPCC_annex", "Country_code_A3"] + year_cols].copy()

    df["IPCC_annex"] = df["IPCC_annex"].astype(str).str.strip()
    df["annex1"] = np.where(df["IPCC_annex"].eq("Annex_I"), 1, 0).astype("int8")
    df["iso3"] = df["Country_code_A3"].astype(str).str.strip().str.upper()

    df_long = df.melt(
        id_vars=["iso3", "annex1"],
        value_vars=year_cols,
        var_name="year",
        value_name="EdgarGgCO2eq"
    )

    df_long["year"] = (
        df_long["year"]
        .astype(str)
        .str.replace("Y_", "", regex=False)
        .astype(int)
    )

    df_long["EdgarGgCO2eq"] = force_numeric(df_long["EdgarGgCO2eq"])

    df_long = df_long[df_long["iso3"].str.match(r"^[A-Z]{3}$", na=False)].copy()
    df_long = df_long[~df_long["iso3"].isin(["AIR", "SEA"])].copy()
    df_long = df_long[(df_long["year"] >= year_start) & (df_long["year"] <= year_end)].copy()

    df_long = df_long[["year", "iso3", "annex1", "EdgarGgCO2eq"]].copy()
    df_long["year"] = df_long["year"].astype("int32")
    df_long["annex1"] = df_long["annex1"].astype("int8")
    df_long = df_long.sort_values(["iso3", "year"]).reset_index(drop=True)

    var_labels = {
        "year": "Year",
        "iso3": "ISO3 country code",
        "annex1": "Annex I dummy: 1=Annex I, 0=otherwise",
        "EdgarGgCO2eq": "EDGAR total GHG emissions in Gg CO2 equivalent"
    }

    df_long.to_stata(
        output_file,
        write_index=False,
        version=118,
        variable_labels=var_labels
    )

    print(f"\nFichier EDGAR sauvegardé : {output_file}")
    return df_long, var_labels


# =========================================================
# OWID
# =========================================================

def build_owid_dataset():
    input_file = working_dir / "owid-co2-data.csv"
    output_file = working_dir / "OWID_GHG.dta"

    df = pd.read_csv(input_file)

    required_cols = ["country", "year", "iso_code"]
    missing_required = [c for c in required_cols if c not in df.columns]
    if missing_required:
        raise ValueError(f"Colonnes manquantes dans OWID : {missing_required}")

    df = df.rename(columns={"iso_code": "iso3"})
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[(df["year"] >= year_start) & (df["year"] <= year_end)].copy()

    df["iso3"] = df["iso3"].astype(str).str.strip().str.upper()
    df = df[df["iso3"].str.match(r"^[A-Z]{3}$", na=False)].copy()

    vars_to_keep = [
        "country",
        "year",
        "iso3",
        "population",
        "gdp",
        "co2",
        "consumption_co2",
        "total_ghg",
        "total_ghg_excluding_lucf",
        "methane",
        "nitrous_oxide"
    ]

    existing_vars = [c for c in vars_to_keep if c in df.columns]
    df = df[existing_vars].copy()

    numeric_vars = [c for c in df.columns if c not in ["country", "iso3"]]
    for col in numeric_vars:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "co2" in df.columns:
        df["co2_Gg"] = df["co2"] * 1000

    if "consumption_co2" in df.columns:
        df["consumption_co2_Gg"] = df["consumption_co2"] * 1000

    if "total_ghg" in df.columns:
        df["total_ghg_GgCO2eq"] = df["total_ghg"] * 1000

    if "total_ghg_excluding_lucf" in df.columns:
        df["total_ghg_excl_lucf_GgCO2eq"] = df["total_ghg_excluding_lucf"] * 1000

    if "methane" in df.columns:
        df["methane_GgCO2eq"] = df["methane"] * 1000

    if "nitrous_oxide" in df.columns:
        df["nitrous_oxide_GgCO2eq"] = df["nitrous_oxide"] * 1000

    if "total_ghg_GgCO2eq" in df.columns and "gdp" in df.columns:
        df["GHG_intensity"] = np.where(
            (df["gdp"].notna()) & (df["gdp"] != 0) & (df["total_ghg_GgCO2eq"].notna()),
            df["total_ghg_GgCO2eq"] / df["gdp"],
            np.nan
        )

    if "total_ghg_excl_lucf_GgCO2eq" in df.columns and "gdp" in df.columns:
        df["GHG_intensity_excl_lucf"] = np.where(
            (df["gdp"].notna()) & (df["gdp"] != 0) & (df["total_ghg_excl_lucf_GgCO2eq"].notna()),
            df["total_ghg_excl_lucf_GgCO2eq"] / df["gdp"],
            np.nan
        )

    final_vars = [
        "country",
        "year",
        "iso3",
        "population",
        "gdp",
        "co2_Gg",
        "consumption_co2_Gg",
        "total_ghg_GgCO2eq",
        "total_ghg_excl_lucf_GgCO2eq",
        "methane_GgCO2eq",
        "nitrous_oxide_GgCO2eq",
        "GHG_intensity",
        "GHG_intensity_excl_lucf"
    ]

    final_vars = [c for c in final_vars if c in df.columns]
    df = df[final_vars].copy()

    df["year"] = df["year"].astype("int32")
    df = df[df["iso3"].notna()].copy()
    df = df.sort_values(["iso3", "year"]).reset_index(drop=True)

    var_labels = {
        "country": "Country name",
        "year": "Year",
        "iso3": "ISO3 country code",
        "population": "Population",
        "gdp": "Gross domestic product",
        "co2_Gg": "Production-based CO2 emissions in Gg",
        "consumption_co2_Gg": "Consumption-based CO2 emissions in Gg",
        "total_ghg_GgCO2eq": "Total greenhouse gas emissions in Gg CO2eq",
        "total_ghg_excl_lucf_GgCO2eq": "Total greenhouse gas emissions excluding LUCF in Gg CO2eq",
        "methane_GgCO2eq": "Methane emissions in Gg CO2eq",
        "nitrous_oxide_GgCO2eq": "Nitrous oxide emissions in Gg CO2eq",
        "GHG_intensity": "Greenhouse gas intensity of GDP (Gg CO2eq per unit of GDP)",
        "GHG_intensity_excl_lucf": "Greenhouse gas intensity of GDP excluding LUCF (Gg CO2eq per unit of GDP)"
    }

    var_labels = {k: v for k, v in var_labels.items() if k in df.columns}

    df.to_stata(
        output_file,
        write_index=False,
        version=118,
        variable_labels=var_labels
    )

    print(f"\nFichier OWID sauvegardé : {output_file}")
    return df, var_labels


# =========================================================
# NGFS
# =========================================================

def build_ngfs_dataset():
    input_file = working_dir / "PMRCPBIE_04Feb20.csv"
    output_file = working_dir / "NGFS_BAU_CO2eq_WIDE.dta"

    ngfs = pd.read_csv(input_file, low_memory=False)

    ngfs_long = ngfs.melt(
        id_vars=["source", "scenario", "country", "category", "entity", "unit"],
        var_name="year",
        value_name="value"
    )

    ngfs_long = ngfs_long[
        ngfs_long["year"].astype(str).str.match(r"^\d{4}$", na=False)
    ].copy()

    ngfs_long["year"] = ngfs_long["year"].astype(int)

    ngfs_wide = ngfs_long.pivot_table(
        index=["source", "scenario", "country", "category", "unit", "year"],
        columns="entity",
        values="value",
        aggfunc="mean"
    ).reset_index()

    ngfs_wide.columns.name = None
    ngfs_wide = ngfs_wide[(ngfs_wide["year"] >= year_start) & (ngfs_wide["year"] <= year_end)].copy()

    scenarios_bau = [
        "RCP85SSP2IIASA", "RCP85SSP2OECD", "RCP85SSP2PIK",
        "RCP85SSP3IIASA", "RCP85SSP3OECD", "RCP85SSP3PIK",
        "RCP85SSP5IIASA", "RCP85SSP5OECD", "RCP85SSP5PIK"
    ]

    ngfs_wide = ngfs_wide[ngfs_wide["scenario"].isin(scenarios_bau)].copy()
    ngfs_wide = ngfs_wide[ngfs_wide["unit"] == "Gg"].copy()

    gases = ["CO2", "CH4", "N2O"]
    for gas in gases:
        if gas not in ngfs_wide.columns:
            ngfs_wide[gas] = 0.0
        ngfs_wide[gas] = pd.to_numeric(ngfs_wide[gas], errors="coerce").fillna(0)

    gwp_ar5 = {"CO2": 1, "CH4": 28, "N2O": 265}

    ngfs_wide["CO2eq_CO2"] = ngfs_wide["CO2"] * gwp_ar5["CO2"]
    ngfs_wide["CO2eq_CH4"] = ngfs_wide["CH4"] * gwp_ar5["CH4"]
    ngfs_wide["CO2eq_N2O"] = ngfs_wide["N2O"] * gwp_ar5["N2O"]

    ngfs_wide["Total_CO2eq_Scenario"] = (
        ngfs_wide["CO2eq_CO2"] +
        ngfs_wide["CO2eq_CH4"] +
        ngfs_wide["CO2eq_N2O"]
    ).round(2)

    ngfs_wide["country"] = ngfs_wide["country"].astype(str).str.strip().str.upper()
    ngfs_wide = ngfs_wide[ngfs_wide["country"].str.match(r"^[A-Z]{3}$", na=False)].copy()
    ngfs_wide = ngfs_wide.rename(columns={"country": "iso3"})

    ngfs_final_long = ngfs_wide[["year", "iso3", "scenario", "Total_CO2eq_Scenario"]].copy()

    dup_mask = ngfs_final_long.duplicated(subset=["year", "iso3", "scenario"], keep=False)
    if dup_mask.any():
        print("\nDoublons détectés dans NGFS sur year-iso3-scenario :")
        print(
            ngfs_final_long.loc[dup_mask]
            .sort_values(["iso3", "scenario", "year"])
            .head(20)
        )
        ngfs_final_long = ngfs_final_long.drop_duplicates(
            subset=["year", "iso3", "scenario"],
            keep="first"
        ).copy()

    ngfs_final_long["varname"] = "TOTAL_CO2eq_" + ngfs_final_long["scenario"]

    ngfs_final = ngfs_final_long.pivot_table(
        index=["year", "iso3"],
        columns="varname",
        values="Total_CO2eq_Scenario",
        aggfunc="mean"
    ).reset_index()

    ngfs_final.columns.name = None
    ngfs_final["year"] = ngfs_final["year"].astype("int32")
    ngfs_final["iso3"] = ngfs_final["iso3"].astype(str)
    ngfs_final = ngfs_final.sort_values(["iso3", "year"]).reset_index(drop=True)

    var_labels = {
        "year": "Year",
        "iso3": "ISO3 country code"
    }

    for col in ngfs_final.columns:
        if col.startswith("TOTAL_CO2eq_"):
            scenario_name = col.replace("TOTAL_CO2eq_", "")
            var_labels[col] = f"Projected total emissions in Gg CO2 equivalent - {scenario_name}"

    ngfs_final.to_stata(
        output_file,
        write_index=False,
        version=118,
        variable_labels=var_labels
    )

    print(f"\nFichier NGFS sauvegardé : {output_file}")
    return ngfs_final, var_labels


# =========================================================
# Base maître
# =========================================================

def build_master_panel(
    ndc_df: pd.DataFrame,
    ndc_labels: dict,
    edgar_df: pd.DataFrame,
    edgar_labels: dict,
    owid_df: pd.DataFrame,
    owid_labels: dict,
    ngfs_df: pd.DataFrame,
    ngfs_labels: dict
):
    output_file = Final_dir / "Data.dta"

    iso_sets = []

    for df in [ndc_df, edgar_df, owid_df, ngfs_df]:
        if "iso3" in df.columns:
            iso_sets.append(set(df["iso3"].dropna().astype(str).unique()))

    all_iso3 = sorted(set().union(*iso_sets))

    year_grid = pd.DataFrame({"year": np.arange(year_start, year_end + 1, dtype=np.int32)})
    iso_grid = pd.DataFrame({"iso3": all_iso3})

    master = iso_grid.assign(_tmp=1).merge(year_grid.assign(_tmp=1), on="_tmp").drop(columns="_tmp")

    master = master.merge(edgar_df, on=["iso3", "year"], how="left")
    master = master.merge(owid_df.drop(columns=["country"], errors="ignore"), on=["iso3", "year"], how="left")
    master = master.merge(ngfs_df, on=["iso3", "year"], how="left")
    master = master.merge(ndc_df.drop(columns=["country"], errors="ignore"), on="iso3", how="left")

    # -----------------------------
    # Kyoto targets
    # -----------------------------
    cc = coco.CountryConverter()

    kyoto_dict = {
        -8: [
            "Austria", "Belgium", "Denmark", "Finland", "France", "Germany", "Greece",
            "Ireland", "Italy", "Luxembourg", "Netherlands", "Portugal", "Spain",
            "Sweden", "United Kingdom",
            "Bulgaria", "Czech Republic", "Estonia", "Latvia", "Lithuania",
            "Liechtenstein", "Monaco", "Romania", "Slovakia", "Slovenia", "Switzerland"
        ],
        -7: ["United States"],
        -6: ["Canada", "Hungary", "Japan", "Poland"],
        -5: ["Croatia"],
        0: ["New Zealand", "Russian Federation", "Ukraine"],
        1: ["Norway"],
        8: ["Australia"],
        10: ["Iceland"]
    }

    kyoto_rows = []
    for target, countries in kyoto_dict.items():
        for country in countries:
            kyoto_rows.append({
                "country": country,
                "kyoto_target_pct": target
            })

    kyoto_df = pd.DataFrame(kyoto_rows)

    kyoto_df["iso3"] = cc.convert(names=kyoto_df["country"], to="ISO3")
    kyoto_df.loc[kyoto_df["country"] == "Russian Federation", "iso3"] = "RUS"
    kyoto_df.loc[kyoto_df["country"] == "United States", "iso3"] = "USA"

    kyoto_df = kyoto_df[["iso3", "kyoto_target_pct"]].drop_duplicates(subset=["iso3"])

    master = master.merge(kyoto_df, on="iso3", how="left")

    master["kyoto_dummy"] = np.where(master["kyoto_target_pct"].notna(), 1, 0).astype("int8")

    master["kyoto_period"] = np.where(
        (master["year"] >= 2008) & (master["year"] <= 2012),
        1,
        0
    ).astype("int8")

    # -----------------------------
    # Variable simple pour distinguer historique et projection
    # -----------------------------
    master["data_period"] = np.where(master["year"] <= 2024, "historical", "projection")

    master = master.sort_values(["iso3", "year"]).reset_index(drop=True)
    master = clean_text_columns(master)

    master_labels = {
        "iso3": "ISO3 country code",
        "year": "Year",
        "data_period": "Historical if year <= 2024, projection otherwise",
        "kyoto_target_pct": "Kyoto Protocol target (% change from 1990 baseline, Annex B)",
        "kyoto_dummy": "Dummy =1 if country has Kyoto target (Annex B)",
        "kyoto_period": "Dummy =1 for Kyoto commitment period (2008-2012)"
    }

    for label_dict in [edgar_labels, owid_labels, ngfs_labels, ndc_labels]:
        master_labels.update(label_dict)

    master_labels = {k: v for k, v in master_labels.items() if k in master.columns}

    master.to_stata(
        output_file,
        write_index=False,
        version=118,
        variable_labels=master_labels
    )

    print(f"\nFichier maître sauvegardé : {output_file}")
    print("\nDimensions de la base maître :")
    print(master.shape)

    

    return master, master_labels

# =========================================================
# Exécution
# =========================================================

if __name__ == "__main__":
    print("\nConstruction de la base NDC")
    ndc_df, ndc_labels = build_ndc_dataset()

    print("\nConstruction de la base EDGAR")
    edgar_df, edgar_labels = build_edgar_dataset()

    print("\nConstruction de la base OWID")
    owid_df, owid_labels = build_owid_dataset()

    print("\nConstruction de la base NGFS")
    ngfs_df, ngfs_labels = build_ngfs_dataset()

    print("\nConstruction de la base maître 1990-2050")
    master_df, master_labels = build_master_panel(
        ndc_df=ndc_df,
        ndc_labels=ndc_labels,
        edgar_df=edgar_df,
        edgar_labels=edgar_labels,
        owid_df=owid_df,
        owid_labels=owid_labels,
        ngfs_df=ngfs_df,
        ngfs_labels=ngfs_labels
    )

    print("\nTraitement terminé avec succès.")



from pathlib import Path
import numpy as np
import pandas as pd
from pandas.io.stata import StataReader


# =========================================================
# PATHS
# =========================================================

working_dir = Path(r"C:\Users\richm\Desktop\NDC DATA NEW\NDC Completed\Final Data")
input_file = working_dir / "Data.dta"
output_analysis = working_dir / "Data_analysis_gap_only.dta"
audit_file_xlsx = working_dir / "Audit_targets.xlsx"
audit_file_dta = working_dir / "Audit_targets.dta"

problem_countries = ["BGD", "ALB", "CRI", "GAB"]


# =========================================================
# LOAD DATA
# =========================================================

df = pd.read_stata(input_file)

with StataReader(str(input_file)) as reader:
    existing_var_labels = reader.variable_labels()

print("Dimensions initiales :", df.shape)


# =========================================================
# BASIC CLEANING
# =========================================================

df = df.copy()

df["iso3"] = df["iso3"].astype(str).str.strip().str.upper()
df["year"] = pd.to_numeric(df["year"], errors="coerce")

df = df[df["year"].between(1990, 2050)].copy()
df = df[
    ~df["iso3"].isin(
        ["", "AIR", "SEA", "ZZB", "SCG", "PSG", "SML", "CHI", "ANT"]
        + problem_countries
    )
].copy()

df = df.dropna(subset=["iso3", "year"])
df["year"] = df["year"].astype(int)

df = df.drop_duplicates(subset=["iso3", "year"], keep="first").copy()
df = df[~df["iso3"].isin(problem_countries)].copy()

print("Dimensions après nettoyage :", df.shape)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_value_at_year(data, year_col, value_col, out_col):
    if year_col not in data.columns or value_col not in data.columns:
        data[out_col] = np.nan
        return data

    tmp = data[["iso3", "year", value_col]].copy()
    tmp = tmp.rename(columns={"year": year_col, value_col: out_col})
    tmp = tmp.drop_duplicates(subset=["iso3", year_col], keep="first")

    return data.merge(tmp, on=["iso3", year_col], how="left")


def build_parallel_target(
    data,
    pct_col,
    abs_col,
    intensity_flag_col,
    base_em_col,
    base_intensity_col,
    gdp_target_col,
    bau_target_col,
    ghgtype_col,
    out_target_col,
    out_method_col
):
    data[out_target_col] = np.nan
    data[out_method_col] = None

    if abs_col in data.columns:
        mask = data[abs_col].notna()
        data.loc[mask, out_target_col] = data.loc[mask, abs_col]
        data.loc[mask, out_method_col] = "absolute"

    if {pct_col, base_em_col, intensity_flag_col}.issubset(data.columns):
        mask = (
            data[out_target_col].isna()
            & data[pct_col].notna()
            & data[base_em_col].notna()
            & (~data[intensity_flag_col])
        )
        data.loc[mask, out_target_col] = (
            data.loc[mask, base_em_col] * (1 - data.loc[mask, pct_col] / 100)
        )
        data.loc[mask, out_method_col] = "base_year_percent"

    if {pct_col, bau_target_col, ghgtype_col}.issubset(data.columns):
        mask = (
            data[out_target_col].isna()
            & data[pct_col].notna()
            & data[bau_target_col].notna()
            & data[ghgtype_col].astype(str).str.lower().str.contains("baseline", na=False)
        )
        data.loc[mask, out_target_col] = (
            data.loc[mask, bau_target_col] * (1 - data.loc[mask, pct_col] / 100)
        )
        data.loc[mask, out_method_col] = "bau_percent"

    if {pct_col, intensity_flag_col, base_intensity_col, gdp_target_col}.issubset(data.columns):
        mask = (
            data[out_target_col].isna()
            & data[intensity_flag_col]
            & data[pct_col].notna()
            & data[base_intensity_col].notna()
            & data[gdp_target_col].notna()
            & (data[gdp_target_col] != 0)
        )
        data.loc[mask, out_target_col] = (
            data.loc[mask, base_intensity_col]
            * (1 - data.loc[mask, pct_col] / 100)
            * data.loc[mask, gdp_target_col]
        )
        data.loc[mask, out_method_col] = "intensity_percent"

    return data


def build_gap_from_emissions(data, emission_col, target_col, gap_col, gap_pct_col):
    if {emission_col, target_col}.issubset(data.columns):
        data[gap_col] = data[emission_col] - data[target_col]
        data[gap_pct_col] = np.where(
            data[target_col].notna() & (data[target_col] != 0),
            data[gap_col] / data[target_col],
            np.nan
        )
    else:
        data[gap_col] = np.nan
        data[gap_pct_col] = np.nan

    return data


def build_dynamic_gap(
    data,
    gap_col,
    gap_pct_col,
    target_year_col,
    years_left_col,
    dyn_gap_col,
    dyn_gap_pct_col
):
    if target_year_col not in data.columns:
        data[years_left_col] = np.nan
        data[dyn_gap_col] = np.nan
        data[dyn_gap_pct_col] = np.nan
        return data

    data[years_left_col] = pd.to_numeric(data[target_year_col], errors="coerce") - data["year"]
    valid_time = data[years_left_col].notna() & (data[years_left_col] > 0)

    data[dyn_gap_col] = np.where(
        valid_time & data[gap_col].notna(),
        data[gap_col] / data[years_left_col],
        np.nan
    )

    data[dyn_gap_pct_col] = np.where(
        valid_time & data[gap_pct_col].notna(),
        data[gap_pct_col] / data[years_left_col],
        np.nan
    )

    return data


def build_feasibility_abs(data, observed_reduction_col, gap_abs_col, out_feasibility_col):
    if {observed_reduction_col, gap_abs_col}.issubset(data.columns):
        data[out_feasibility_col] = np.where(
            data[gap_abs_col].notna() & (data[gap_abs_col] != 0),
            data[observed_reduction_col] / data[gap_abs_col],
            np.nan
        )
    else:
        data[out_feasibility_col] = np.nan

    return data


def build_feasibility_dyn(data, observed_reduction_col, dyn_gap_abs_col, out_feasibility_col):
    if {observed_reduction_col, dyn_gap_abs_col}.issubset(data.columns):
        data[out_feasibility_col] = np.where(
            data[dyn_gap_abs_col].notna() & (data[dyn_gap_abs_col] != 0),
            data[observed_reduction_col] / data[dyn_gap_abs_col],
            np.nan
        )
    else:
        data[out_feasibility_col] = np.nan

    return data


def build_bau_robustness_target_full(
    data,
    bau_target_col,
    baseline_target_col,
    baseline_method_col,
    pct_col,
    ghgtype_col,
    emission_col,
    out_target_col,
    out_method_col,
    out_gap_col,
    out_gap_pct_col,
    bau_label
):
    """
    Full-sample BAU robustness.

    Non-BAU pledges keep their baseline harmonized target.
    BAU pledges are recalculated using the alternative BAU projection.
    """
    data[out_target_col] = data[baseline_target_col] if baseline_target_col in data.columns else np.nan
    data[out_method_col] = data[baseline_method_col] if baseline_method_col in data.columns else None

    required = {
        bau_target_col,
        baseline_target_col,
        baseline_method_col,
        pct_col,
        ghgtype_col,
        emission_col
    }

    if required.issubset(data.columns):
        mask_bau = (
            data[ghgtype_col].astype(str).str.lower().str.contains("baseline", na=False)
            & data[pct_col].notna()
            & data[bau_target_col].notna()
        )

        data.loc[mask_bau, out_target_col] = (
            data.loc[mask_bau, bau_target_col]
            * (1 - data.loc[mask_bau, pct_col] / 100)
        )

        data.loc[mask_bau, out_method_col] = f"bau_percent_{bau_label}"

        data = build_gap_from_emissions(
            data,
            emission_col,
            out_target_col,
            out_gap_col,
            out_gap_pct_col
        )
    else:
        data[out_gap_col] = np.nan
        data[out_gap_pct_col] = np.nan

    return data


# =========================================================
# BAU VARIABLES: SHORT NAMES COMPATIBLE WITH STATA
# =========================================================

bau_variant_map = {
    "r85s2m": [
        "TOTAL_CO2eq_RCP85SSP2IIASA",
        "TOTAL_CO2eq_RCP85SSP2OECD",
        "TOTAL_CO2eq_RCP85SSP2PIK"
    ],
    "r85s3m": [
        "TOTAL_CO2eq_RCP85SSP3IIASA",
        "TOTAL_CO2eq_RCP85SSP3OECD",
        "TOTAL_CO2eq_RCP85SSP3PIK"
    ],
    "r85s5m": [
        "TOTAL_CO2eq_RCP85SSP5IIASA",
        "TOTAL_CO2eq_RCP85SSP5OECD",
        "TOTAL_CO2eq_RCP85SSP5PIK"
    ],
    "r85s2i": ["TOTAL_CO2eq_RCP85SSP2IIASA"],
    "r85s2o": ["TOTAL_CO2eq_RCP85SSP2OECD"],
    "r85s2p": ["TOTAL_CO2eq_RCP85SSP2PIK"],
    "r85s3i": ["TOTAL_CO2eq_RCP85SSP3IIASA"],
    "r85s3o": ["TOTAL_CO2eq_RCP85SSP3OECD"],
    "r85s3p": ["TOTAL_CO2eq_RCP85SSP3PIK"],
    "r85s5i": ["TOTAL_CO2eq_RCP85SSP5IIASA"],
    "r85s5o": ["TOTAL_CO2eq_RCP85SSP5OECD"],
    "r85s5p": ["TOTAL_CO2eq_RCP85SSP5PIK"],
}

bau_robustness_variants = {
    "r85s2m": "RCP8.5 SSP2 mean",
    "r85s3m": "RCP8.5 SSP3 mean",
    "r85s5m": "RCP8.5 SSP5 mean",
    "r85s2i": "RCP8.5 SSP2 IIASA",
    "r85s2o": "RCP8.5 SSP2 OECD",
    "r85s2p": "RCP8.5 SSP2 PIK",
    "r85s3i": "RCP8.5 SSP3 IIASA",
    "r85s3o": "RCP8.5 SSP3 OECD",
    "r85s3p": "RCP8.5 SSP3 PIK",
    "r85s5i": "RCP8.5 SSP5 IIASA",
    "r85s5o": "RCP8.5 SSP5 OECD",
    "r85s5p": "RCP8.5 SSP5 PIK",
}

all_bau_cols = sorted(set(sum(bau_variant_map.values(), [])))
existing_all_bau_cols = [c for c in all_bau_cols if c in df.columns]

df["bau_mean"] = (
    df[existing_all_bau_cols].mean(axis=1, skipna=True)
    if existing_all_bau_cols else np.nan
)

for bau_name, cols in bau_variant_map.items():
    existing_cols = [c for c in cols if c in df.columns]
    df[f"bau_{bau_name}"] = (
        df[existing_cols].mean(axis=1, skipna=True)
        if existing_cols else np.nan
    )


# =========================================================
# BASE YEAR CORRECTIONS
# =========================================================

if "baseyr_n2" in df.columns:
    df.loc[df["iso3"] == "CAN", "baseyr_n2"] = 2005
    df.loc[df["iso3"] == "JPN", "baseyr_n2"] = 2013
    df.loc[df["iso3"] == "TUN", "baseyr_n2"] = 2010


# =========================================================
# KEEP COUNTRIES WITH TARGET INFORMATION
# =========================================================

possible_target_cols = [
    "tgt_pct_n1", "tgt_ggco2_n1", "tgt_pct_n2", "tgt_ggco2_n2",
    "untgt_pct_n1", "untgt_gg_n1", "untgt_pct_n2", "untgt_gg_n2",
    "ctgt_pct_n1", "ctgt_gg_n1", "ctgt_pct_n2", "ctgt_gg_n2",
    "tgttype_n1", "ghgtype_n1", "tgttype_n2", "ghgtype_n2"
]

existing_target_cols = [c for c in possible_target_cols if c in df.columns]

if existing_target_cols:
    mask_no_target = df[existing_target_cols].isna().all(axis=1)
    df = df[~mask_no_target].copy()


# =========================================================
# REFERENCE VALUES
# =========================================================

if "baseyr_n1" in df.columns and "EdgarGgCO2eq" in df.columns:
    df = get_value_at_year(df, "baseyr_n1", "EdgarGgCO2eq", "base_em_n1_edgar")

if "baseyr_n2" in df.columns and "EdgarGgCO2eq" in df.columns:
    df = get_value_at_year(df, "baseyr_n2", "EdgarGgCO2eq", "base_em_n2_edgar")

if "baseyr_n1" in df.columns and "GHG_intensity" in df.columns:
    df = get_value_at_year(df, "baseyr_n1", "GHG_intensity", "base_intensity_n1")

if "baseyr_n2" in df.columns and "GHG_intensity" in df.columns:
    df = get_value_at_year(df, "baseyr_n2", "GHG_intensity", "base_intensity_n2")

if "baseyr_n1" in df.columns and "gdp" in df.columns:
    df = get_value_at_year(df, "baseyr_n1", "gdp", "base_gdp_n1")

if "baseyr_n2" in df.columns and "gdp" in df.columns:
    df = get_value_at_year(df, "baseyr_n2", "gdp", "base_gdp_n2")

if "tgtyr_n1" in df.columns:
    df = get_value_at_year(df, "tgtyr_n1", "bau_mean", "bau_target_n1")
    for bau_name in bau_variant_map.keys():
        df = get_value_at_year(
            df,
            "tgtyr_n1",
            f"bau_{bau_name}",
            f"bau_{bau_name}_target_n1"
        )

if "tgtyr_n2" in df.columns:
    df = get_value_at_year(df, "tgtyr_n2", "bau_mean", "bau_target_n2")
    for bau_name in bau_variant_map.keys():
        df = get_value_at_year(
            df,
            "tgtyr_n2",
            f"bau_{bau_name}",
            f"bau_{bau_name}_target_n2"
        )

if "tgtyr_n1" in df.columns and "gdp" in df.columns:
    df = get_value_at_year(df, "tgtyr_n1", "gdp", "gdp_target_n1")

if "tgtyr_n2" in df.columns and "gdp" in df.columns:
    df = get_value_at_year(df, "tgtyr_n2", "gdp", "gdp_target_n2")


# =========================================================
# INTENSITY TARGET DETECTION
# =========================================================

for col in ["tgttype_n1", "ghgtype_n1", "tgttype_n2", "ghgtype_n2"]:
    if col in df.columns:
        df[col] = df[col].astype(str)

df["is_intensity_n1"] = False
df["is_intensity_n2"] = False

intensity_keywords = [
    "intensity",
    "gdp",
    "per unit gdp",
    "emissions intensity",
    "emission intensity",
    "carbon intensity"
]

if "tgttype_n1" in df.columns:
    for kw in intensity_keywords:
        df["is_intensity_n1"] = (
            df["is_intensity_n1"]
            | df["tgttype_n1"].str.lower().str.contains(kw, na=False)
        )

if "ghgtype_n1" in df.columns:
    for kw in intensity_keywords:
        df["is_intensity_n1"] = (
            df["is_intensity_n1"]
            | df["ghgtype_n1"].str.lower().str.contains(kw, na=False)
        )

if "tgttype_n2" in df.columns:
    for kw in intensity_keywords:
        df["is_intensity_n2"] = (
            df["is_intensity_n2"]
            | df["tgttype_n2"].str.lower().str.contains(kw, na=False)
        )

if "ghgtype_n2" in df.columns:
    for kw in intensity_keywords:
        df["is_intensity_n2"] = (
            df["is_intensity_n2"]
            | df["ghgtype_n2"].str.lower().str.contains(kw, na=False)
        )


# =========================================================
# TARGET CONSTRUCTION
# =========================================================

df = build_parallel_target(
    df, "tgt_pct_n1", "tgt_ggco2_n1", "is_intensity_n1",
    "base_em_n1_edgar", "base_intensity_n1", "gdp_target_n1",
    "bau_target_n1", "ghgtype_n1",
    "target_n1_edgar", "target_method_n1"
)

df = build_parallel_target(
    df, "tgt_pct_n2", "tgt_ggco2_n2", "is_intensity_n2",
    "base_em_n2_edgar", "base_intensity_n2", "gdp_target_n2",
    "bau_target_n2", "ghgtype_n2",
    "target_n2_edgar", "target_method_n2"
)

df = build_parallel_target(
    df, "untgt_pct_n1", "untgt_gg_n1", "is_intensity_n1",
    "base_em_n1_edgar", "base_intensity_n1", "gdp_target_n1",
    "bau_target_n1", "ghgtype_n1",
    "target_n1_uncond_edgar", "target_method_n1_uncond"
)

df = build_parallel_target(
    df, "untgt_pct_n2", "untgt_gg_n2", "is_intensity_n2",
    "base_em_n2_edgar", "base_intensity_n2", "gdp_target_n2",
    "bau_target_n2", "ghgtype_n2",
    "target_n2_uncond_edgar", "target_method_n2_uncond"
)

df = build_parallel_target(
    df, "ctgt_pct_n1", "ctgt_gg_n1", "is_intensity_n1",
    "base_em_n1_edgar", "base_intensity_n1", "gdp_target_n1",
    "bau_target_n1", "ghgtype_n1",
    "target_n1_cond_edgar", "target_method_n1_cond"
)

df = build_parallel_target(
    df, "ctgt_pct_n2", "ctgt_gg_n2", "is_intensity_n2",
    "base_em_n2_edgar", "base_intensity_n2", "gdp_target_n2",
    "bau_target_n2", "ghgtype_n2",
    "target_n2_cond_edgar", "target_method_n2_cond"
)


# =========================================================
# MANUAL CORRECTIONS
# =========================================================

manual_targets_n1 = {
    "ZAF": (398000 + 614000) / 2,
    "ARG": 483000,
    "BTN": 6300,
    "GUY": 52000,
}

manual_targets_n2 = {
    "ZAF": (350000 + 420000) / 2,
    "ARG": 449000,
    "BTN": 6300,
    "GUY": 52000,
}

for iso, value in manual_targets_n1.items():
    df.loc[df["iso3"] == iso, "target_n1_edgar"] = value
    df.loc[df["iso3"] == iso, "target_method_n1"] = "manual_absolute"
    df.loc[df["iso3"] == iso, "target_n1_uncond_edgar"] = value
    df.loc[df["iso3"] == iso, "target_method_n1_uncond"] = "manual_absolute"
    df.loc[df["iso3"] == iso, "target_n1_cond_edgar"] = value
    df.loc[df["iso3"] == iso, "target_method_n1_cond"] = "manual_absolute"

for iso, value in manual_targets_n2.items():
    df.loc[df["iso3"] == iso, "target_n2_edgar"] = value
    df.loc[df["iso3"] == iso, "target_method_n2"] = "manual_absolute"
    df.loc[df["iso3"] == iso, "target_n2_uncond_edgar"] = value
    df.loc[df["iso3"] == iso, "target_method_n2_uncond"] = "manual_absolute"
    df.loc[df["iso3"] == iso, "target_n2_cond_edgar"] = value
    df.loc[df["iso3"] == iso, "target_method_n2_cond"] = "manual_absolute"


# =========================================================
# MAIN TARGETS
# =========================================================

df["target_main_edgar"] = df["target_n2_edgar"].where(
    df["target_n2_edgar"].notna(),
    df["target_n1_edgar"]
)

df["target_main_uncond_edgar"] = df["target_n2_uncond_edgar"].where(
    df["target_n2_uncond_edgar"].notna(),
    df["target_n1_uncond_edgar"]
)

df["target_main_cond_edgar"] = df["target_n2_cond_edgar"].where(
    df["target_n2_cond_edgar"].notna(),
    df["target_n1_cond_edgar"]
)

df["target_method_main"] = np.where(
    df["target_n2_edgar"].notna(),
    df["target_method_n2"],
    df["target_method_n1"]
)

df["target_method_main_uncond"] = np.where(
    df["target_n2_uncond_edgar"].notna(),
    df["target_method_n2_uncond"],
    df["target_method_n1_uncond"]
)

df["target_method_main_cond"] = np.where(
    df["target_n2_cond_edgar"].notna(),
    df["target_method_n2_cond"],
    df["target_method_n1_cond"]
)

df["ndc_cycle_main"] = np.where(
    df["target_n2_edgar"].notna(),
    "NDC2",
    np.where(df["target_n1_edgar"].notna(), "NDC1", None)
)

if "tgtyr_n2" in df.columns and "tgtyr_n1" in df.columns:
    df["tgtyr_main"] = np.where(
        df["target_n2_edgar"].notna(),
        df["tgtyr_n2"],
        df["tgtyr_n1"]
    )

    df["tgtyr_main_uncond"] = np.where(
        df["target_n2_uncond_edgar"].notna(),
        df["tgtyr_n2"],
        df["tgtyr_n1"]
    )

    df["tgtyr_main_cond"] = np.where(
        df["target_n2_cond_edgar"].notna(),
        df["tgtyr_n2"],
        df["tgtyr_n1"]
    )
else:
    df["tgtyr_main"] = np.nan
    df["tgtyr_main_uncond"] = np.nan
    df["tgtyr_main_cond"] = np.nan


# =========================================================
# PRODUCTION-BASED GAPS
# =========================================================

gap_specs = [
    ("EdgarGgCO2eq", "target_n1_edgar", "gap_n1_edgar", "gap_n1_edgar_pct"),
    ("EdgarGgCO2eq", "target_n2_edgar", "gap_n2_edgar", "gap_n2_edgar_pct"),
    ("EdgarGgCO2eq", "target_main_edgar", "gap_main_edgar", "gap_main_edgar_pct"),

    ("EdgarGgCO2eq", "target_n1_uncond_edgar", "gap_n1_uncond_edgar", "gap_n1_uncond_edgar_pct"),
    ("EdgarGgCO2eq", "target_n2_uncond_edgar", "gap_n2_uncond_edgar", "gap_n2_uncond_edgar_pct"),
    ("EdgarGgCO2eq", "target_main_uncond_edgar", "gap_main_uncond_edgar", "gap_main_uncond_edgar_pct"),

    ("EdgarGgCO2eq", "target_n1_cond_edgar", "gap_n1_cond_edgar", "gap_n1_cond_edgar_pct"),
    ("EdgarGgCO2eq", "target_n2_cond_edgar", "gap_n2_cond_edgar", "gap_n2_cond_edgar_pct"),
    ("EdgarGgCO2eq", "target_main_cond_edgar", "gap_main_cond_edgar", "gap_main_cond_edgar_pct"),
]

for spec in gap_specs:
    df = build_gap_from_emissions(df, *spec)


# =========================================================
# CONSUMPTION-BASED GAPS
# =========================================================

consumption_gap_specs = [
    ("consumption_co2_Gg", "target_n1_edgar", "gap_n1_cons", "gap_n1_cons_pct"),
    ("consumption_co2_Gg", "target_n2_edgar", "gap_n2_cons", "gap_n2_cons_pct"),
    ("consumption_co2_Gg", "target_main_edgar", "gap_main_cons", "gap_main_cons_pct"),

    ("consumption_co2_Gg", "target_n1_uncond_edgar", "gap_n1_uncond_cons", "gap_n1_uncond_cons_pct"),
    ("consumption_co2_Gg", "target_n2_uncond_edgar", "gap_n2_uncond_cons", "gap_n2_uncond_cons_pct"),
    ("consumption_co2_Gg", "target_main_uncond_edgar", "gap_main_uncond_cons", "gap_main_uncond_cons_pct"),

    ("consumption_co2_Gg", "target_n1_cond_edgar", "gap_n1_cond_cons", "gap_n1_cond_cons_pct"),
    ("consumption_co2_Gg", "target_n2_cond_edgar", "gap_n2_cond_cons", "gap_n2_cond_cons_pct"),
    ("consumption_co2_Gg", "target_main_cond_edgar", "gap_main_cond_cons", "gap_main_cond_cons_pct"),
]

for spec in consumption_gap_specs:
    df = build_gap_from_emissions(df, *spec)


# =========================================================
# BAU ROBUSTNESS FULL-SAMPLE: NDC1 AND NDC2
# =========================================================

for ndc in ["n1", "n2"]:
    for bau_name, bau_label in bau_robustness_variants.items():
        df = build_bau_robustness_target_full(
            data=df,
            bau_target_col=f"bau_{bau_name}_target_{ndc}",
            baseline_target_col=f"target_{ndc}_edgar",
            baseline_method_col=f"target_method_{ndc}",
            pct_col=f"tgt_pct_{ndc}",
            ghgtype_col=f"ghgtype_{ndc}",
            emission_col="EdgarGgCO2eq",
            out_target_col=f"targ_{ndc}_{bau_name}",
            out_method_col=f"meth_{ndc}_{bau_name}",
            out_gap_col=f"gap_{ndc}_{bau_name}",
            out_gap_pct_col=f"gappct_{ndc}_{bau_name}",
            bau_label=bau_name
        )


# =========================================================
# KYOTO
# =========================================================

if {"kyoto_target_pct", "EdgarGgCO2eq"}.issubset(df.columns):
    kyoto_base = (
        df.loc[df["year"] == 1990, ["iso3", "EdgarGgCO2eq"]]
        .drop_duplicates(subset=["iso3"])
        .rename(columns={"EdgarGgCO2eq": "kyoto_base_edgar"})
    )

    df = df.merge(kyoto_base, on="iso3", how="left")

    df["target_kyoto_edgar"] = np.where(
        df["kyoto_target_pct"].notna() & df["kyoto_base_edgar"].notna(),
        df["kyoto_base_edgar"] * (1 + df["kyoto_target_pct"] / 100),
        np.nan
    )

    df = build_gap_from_emissions(
        df,
        "EdgarGgCO2eq",
        "target_kyoto_edgar",
        "gap_kyoto_edgar",
        "gap_kyoto_edgar_pct"
    )


# =========================================================
# DYNAMIC GAPS
# =========================================================

dynamic_specs = [
    ("gap_n1_edgar", "gap_n1_edgar_pct", "tgtyr_n1", "years_to_target_n1", "dyn_gap_n1_edgar", "dyn_gap_n1_edgar_pct"),
    ("gap_n2_edgar", "gap_n2_edgar_pct", "tgtyr_n2", "years_to_target_n2", "dyn_gap_n2_edgar", "dyn_gap_n2_edgar_pct"),
    ("gap_main_edgar", "gap_main_edgar_pct", "tgtyr_main", "years_to_target_main", "dyn_gap_main_edgar", "dyn_gap_main_edgar_pct"),

    ("gap_n1_uncond_edgar", "gap_n1_uncond_edgar_pct", "tgtyr_n1", "years_to_target_n1_uncond", "dyn_gap_n1_uncond_edgar", "dyn_gap_n1_uncond_edgar_pct"),
    ("gap_n2_uncond_edgar", "gap_n2_uncond_edgar_pct", "tgtyr_n2", "years_to_target_n2_uncond", "dyn_gap_n2_uncond_edgar", "dyn_gap_n2_uncond_edgar_pct"),
    ("gap_main_uncond_edgar", "gap_main_uncond_edgar_pct", "tgtyr_main_uncond", "years_to_target_main_uncond", "dyn_gap_main_uncond_edgar", "dyn_gap_main_uncond_edgar_pct"),

    ("gap_n1_cond_edgar", "gap_n1_cond_edgar_pct", "tgtyr_n1", "years_to_target_n1_cond", "dyn_gap_n1_cond_edgar", "dyn_gap_n1_cond_edgar_pct"),
    ("gap_n2_cond_edgar", "gap_n2_cond_edgar_pct", "tgtyr_n2", "years_to_target_n2_cond", "dyn_gap_n2_cond_edgar", "dyn_gap_n2_cond_edgar_pct"),
    ("gap_main_cond_edgar", "gap_main_cond_edgar_pct", "tgtyr_main_cond", "years_to_target_main_cond", "dyn_gap_main_cond_edgar", "dyn_gap_main_cond_edgar_pct"),

    ("gap_n1_cons", "gap_n1_cons_pct", "tgtyr_n1", "years_to_target_n1_cons", "dyn_gap_n1_cons", "dyn_gap_n1_cons_pct"),
    ("gap_n2_cons", "gap_n2_cons_pct", "tgtyr_n2", "years_to_target_n2_cons", "dyn_gap_n2_cons", "dyn_gap_n2_cons_pct"),
    ("gap_main_cons", "gap_main_cons_pct", "tgtyr_main", "years_to_target_main_cons", "dyn_gap_main_cons", "dyn_gap_main_cons_pct"),

    ("gap_n1_uncond_cons", "gap_n1_uncond_cons_pct", "tgtyr_n1", "years_to_target_n1_uncond_cons", "dyn_gap_n1_uncond_cons", "dyn_gap_n1_uncond_cons_pct"),
    ("gap_n2_uncond_cons", "gap_n2_uncond_cons_pct", "tgtyr_n2", "years_to_target_n2_uncond_cons", "dyn_gap_n2_uncond_cons", "dyn_gap_n2_uncond_cons_pct"),
    ("gap_main_uncond_cons", "gap_main_uncond_cons_pct", "tgtyr_main_uncond", "years_to_target_main_uncond_cons", "dyn_gap_main_uncond_cons", "dyn_gap_main_uncond_cons_pct"),

    ("gap_n1_cond_cons", "gap_n1_cond_cons_pct", "tgtyr_n1", "years_to_target_n1_cond_cons", "dyn_gap_n1_cond_cons", "dyn_gap_n1_cond_cons_pct"),
    ("gap_n2_cond_cons", "gap_n2_cond_cons_pct", "tgtyr_n2", "years_to_target_n2_cond_cons", "dyn_gap_n2_cond_cons", "dyn_gap_n2_cond_cons_pct"),
    ("gap_main_cond_cons", "gap_main_cond_cons_pct", "tgtyr_main_cond", "years_to_target_main_cond_cons", "dyn_gap_main_cond_cons", "dyn_gap_main_cond_cons_pct"),
]

for ndc in ["n1", "n2"]:
    for bau_name in bau_robustness_variants.keys():
        dynamic_specs.append(
            (
                f"gap_{ndc}_{bau_name}",
                f"gappct_{ndc}_{bau_name}",
                f"tgtyr_{ndc}",
                f"yrs_{ndc}_{bau_name}",
                f"dgap_{ndc}_{bau_name}",
                f"dgappct_{ndc}_{bau_name}"
            )
        )

for spec in dynamic_specs:
    gap_col, gap_pct_col, target_year_col, years_left_col, dyn_gap_col, dyn_gap_pct_col = spec
    if gap_col in df.columns and gap_pct_col in df.columns:
        df = build_dynamic_gap(
            df,
            gap_col,
            gap_pct_col,
            target_year_col,
            years_left_col,
            dyn_gap_col,
            dyn_gap_pct_col
        )


# =========================================================
# OBSERVED REDUCTIONS
# =========================================================

df = df.sort_values(["iso3", "year"]).reset_index(drop=True)

if "EdgarGgCO2eq" in df.columns:
    df["AbsReductionEdgar"] = df.groupby("iso3")["EdgarGgCO2eq"].diff()
    df["RelaReductionEdgar"] = df.groupby("iso3")["EdgarGgCO2eq"].pct_change()
    df["ObservedReductionEdgar"] = (
        df.groupby("iso3")["EdgarGgCO2eq"].shift(1) - df["EdgarGgCO2eq"]
    )

if "consumption_co2_Gg" in df.columns:
    df["AbsReductionCons"] = df.groupby("iso3")["consumption_co2_Gg"].diff()
    df["RelaReductionCons"] = df.groupby("iso3")["consumption_co2_Gg"].pct_change()
    df["ObservedReductionCons"] = (
        df.groupby("iso3")["consumption_co2_Gg"].shift(1) - df["consumption_co2_Gg"]
    )


# =========================================================
# ABSOLUTE FEASIBILITY
# =========================================================

feasibility_abs_specs = [
    ("ObservedReductionEdgar", "gap_n1_edgar", "feasabs_n1_edgar"),
    ("ObservedReductionEdgar", "gap_n2_edgar", "feasabs_n2_edgar"),
    ("ObservedReductionEdgar", "gap_main_edgar", "feasabs_main_edgar"),

    ("ObservedReductionEdgar", "gap_n1_uncond_edgar", "feasabs_n1_uncond_edgar"),
    ("ObservedReductionEdgar", "gap_n2_uncond_edgar", "feasabs_n2_uncond_edgar"),
    ("ObservedReductionEdgar", "gap_main_uncond_edgar", "feasabs_main_uncond_edgar"),

    ("ObservedReductionEdgar", "gap_n1_cond_edgar", "feasabs_n1_cond_edgar"),
    ("ObservedReductionEdgar", "gap_n2_cond_edgar", "feasabs_n2_cond_edgar"),
    ("ObservedReductionEdgar", "gap_main_cond_edgar", "feasabs_main_cond_edgar"),

    ("ObservedReductionCons", "gap_n1_cons", "feasabs_n1_cons"),
    ("ObservedReductionCons", "gap_n2_cons", "feasabs_n2_cons"),
    ("ObservedReductionCons", "gap_main_cons", "feasabs_main_cons"),

    ("ObservedReductionCons", "gap_n1_uncond_cons", "feasabs_n1_uncond_cons"),
    ("ObservedReductionCons", "gap_n2_uncond_cons", "feasabs_n2_uncond_cons"),
    ("ObservedReductionCons", "gap_main_uncond_cons", "feasabs_main_uncond_cons"),

    ("ObservedReductionCons", "gap_n1_cond_cons", "feasabs_n1_cond_cons"),
    ("ObservedReductionCons", "gap_n2_cond_cons", "feasabs_n2_cond_cons"),
    ("ObservedReductionCons", "gap_main_cond_cons", "feasabs_main_cond_cons"),
]

for ndc in ["n1", "n2"]:
    for bau_name in bau_robustness_variants.keys():
        feasibility_abs_specs.append(
            (
                "ObservedReductionEdgar",
                f"gap_{ndc}_{bau_name}",
                f"feasabs_{ndc}_{bau_name}"
            )
        )

for spec in feasibility_abs_specs:
    df = build_feasibility_abs(df, *spec)


# =========================================================
# DYNAMIC FEASIBILITY
# =========================================================

feasibility_dyn_specs = [
    ("ObservedReductionEdgar", "dyn_gap_n1_edgar", "feas_n1_edgar"),
    ("ObservedReductionEdgar", "dyn_gap_n2_edgar", "feas_n2_edgar"),
    ("ObservedReductionEdgar", "dyn_gap_main_edgar", "feas_main_edgar"),

    ("ObservedReductionEdgar", "dyn_gap_n1_uncond_edgar", "feas_n1_uncond_edgar"),
    ("ObservedReductionEdgar", "dyn_gap_n2_uncond_edgar", "feas_n2_uncond_edgar"),
    ("ObservedReductionEdgar", "dyn_gap_main_uncond_edgar", "feas_main_uncond_edgar"),

    ("ObservedReductionEdgar", "dyn_gap_n1_cond_edgar", "feas_n1_cond_edgar"),
    ("ObservedReductionEdgar", "dyn_gap_n2_cond_edgar", "feas_n2_cond_edgar"),
    ("ObservedReductionEdgar", "dyn_gap_main_cond_edgar", "feas_main_cond_edgar"),

    ("ObservedReductionCons", "dyn_gap_n1_cons", "feas_n1_cons"),
    ("ObservedReductionCons", "dyn_gap_n2_cons", "feas_n2_cons"),
    ("ObservedReductionCons", "dyn_gap_main_cons", "feas_main_cons"),

    ("ObservedReductionCons", "dyn_gap_n1_uncond_cons", "feas_n1_uncond_cons"),
    ("ObservedReductionCons", "dyn_gap_n2_uncond_cons", "feas_n2_uncond_cons"),
    ("ObservedReductionCons", "dyn_gap_main_uncond_cons", "feas_main_uncond_cons"),

    ("ObservedReductionCons", "dyn_gap_n1_cond_cons", "feas_n1_cond_cons"),
    ("ObservedReductionCons", "dyn_gap_n2_cond_cons", "feas_n2_cond_cons"),
    ("ObservedReductionCons", "dyn_gap_main_cond_cons", "feas_main_cond_cons"),
]

for ndc in ["n1", "n2"]:
    for bau_name in bau_robustness_variants.keys():
        feasibility_dyn_specs.append(
            (
                "ObservedReductionEdgar",
                f"dgap_{ndc}_{bau_name}",
                f"feasdyn_{ndc}_{bau_name}"
            )
        )

for spec in feasibility_dyn_specs:
    df = build_feasibility_dyn(df, *spec)


# =========================================================
# FINAL RESTRICTION
# =========================================================

df = df[df["year"].between(1997, 2024)].copy()
df = df.sort_values(["iso3", "year"]).reset_index(drop=True)

print("\nDimensions après restriction 1997-2024 :", df.shape)


# =========================================================
# QUICK CHECKS
# =========================================================

print("\nRépartition des méthodes de construction de cible principale :")
if "target_method_main" in df.columns:
    print(df["target_method_main"].value_counts(dropna=False))

print("\nRobustesses BAU full-sample : NDC1 et NDC2")
for ndc in ["n1", "n2"]:
    print(f"\n--- {ndc.upper()} ---")
    baseline_col = f"gap_{ndc}_edgar"

    if baseline_col in df.columns:
        print(
            baseline_col,
            "| obs =", df[baseline_col].notna().sum(),
            "| countries =", df.loc[df[baseline_col].notna(), "iso3"].nunique()
        )

    for bau_name in bau_robustness_variants.keys():
        col = f"gap_{ndc}_{bau_name}"
        if col in df.columns:
            print(
                col,
                "| obs =", df[col].notna().sum(),
                "| countries =", df.loc[df[col].notna(), "iso3"].nunique()
            )


# =========================================================
# AUDIT TABLE
# =========================================================

audit_df = df.copy()

audit_cols = [
    "iso3", "year",
    "ndc_cycle_main",
    "target_main_edgar",
    "target_method_main",
    "target_n1_edgar",
    "target_method_n1",
    "target_n2_edgar",
    "target_method_n2",
    "tgtyr_main",
    "tgtyr_n1",
    "tgtyr_n2",
    "baseyr_n1",
    "baseyr_n2",
    "EdgarGgCO2eq",
    "gap_main_edgar",
    "gap_main_edgar_pct",
    "gap_n1_edgar",
    "gap_n1_edgar_pct",
    "gap_n2_edgar",
    "gap_n2_edgar_pct",
    "bau_target_n1",
    "bau_target_n2",
    "gdp_target_n1",
    "gdp_target_n2",
    "is_intensity_n1",
    "is_intensity_n2",
]

for ndc in ["n1", "n2"]:
    for bau_name in bau_robustness_variants.keys():
        audit_cols += [
            f"targ_{ndc}_{bau_name}",
            f"meth_{ndc}_{bau_name}",
            f"gap_{ndc}_{bau_name}",
            f"gappct_{ndc}_{bau_name}",
        ]

audit_cols = [c for c in audit_cols if c in audit_df.columns]
audit_df = audit_df[audit_cols].copy()

audit_df["flag_missing_inputs"] = 0

if {"target_method_main", "baseyr_n2", "baseyr_n1"}.issubset(audit_df.columns):
    audit_df.loc[
        (audit_df["target_method_main"] == "base_year_percent")
        & audit_df["baseyr_n2"].isna()
        & audit_df["baseyr_n1"].isna(),
        "flag_missing_inputs"
    ] = 1

bau_cols_audit = [c for c in ["bau_target_n1", "bau_target_n2"] if c in audit_df.columns]

if "target_method_main" in audit_df.columns and len(bau_cols_audit) > 0:
    audit_df.loc[
        (audit_df["target_method_main"] == "bau_percent")
        & audit_df[bau_cols_audit].isna().all(axis=1),
        "flag_missing_inputs"
    ] = 1

gdp_cols_audit = [c for c in ["gdp_target_n1", "gdp_target_n2"] if c in audit_df.columns]

if "target_method_main" in audit_df.columns and len(gdp_cols_audit) > 0:
    audit_df.loc[
        (audit_df["target_method_main"] == "intensity_percent")
        & audit_df[gdp_cols_audit].isna().all(axis=1),
        "flag_missing_inputs"
    ] = 1

audit_df["flag_negative_target"] = 0
if "target_main_edgar" in audit_df.columns:
    audit_df["flag_negative_target"] = (audit_df["target_main_edgar"] < 0).astype(int)

audit_df["flag_extreme_gap"] = 0
if "gap_main_edgar_pct" in audit_df.columns:
    audit_df["flag_extreme_gap"] = (audit_df["gap_main_edgar_pct"].abs() > 5).astype(int)

audit_df["flag_method_mismatch"] = 0
if {"target_method_main", "is_intensity_n1", "is_intensity_n2"}.issubset(audit_df.columns):
    audit_df.loc[
        (audit_df["target_method_main"] == "absolute")
        & (audit_df["is_intensity_n1"] | audit_df["is_intensity_n2"]),
        "flag_method_mismatch"
    ] = 1

audit_df["audit_flag"] = (
    audit_df["flag_missing_inputs"]
    + audit_df["flag_negative_target"]
    + audit_df["flag_extreme_gap"]
    + audit_df["flag_method_mismatch"]
)

audit_df.to_excel(audit_file_xlsx, index=False)
audit_df.to_stata(audit_file_dta, write_index=False, version=118)

print("\nTable d’audit sauvegardée :", audit_file_xlsx)
print("Table d’audit Stata sauvegardée :", audit_file_dta)


# =========================================================
# LABELS
# =========================================================

new_var_labels = {
    "iso3": "ISO3 country code",
    "year": "Year",
    "ndc_cycle_main": "Main NDC cycle retained for target construction",

    "bau_mean": "Mean BAU emissions across all selected RCP8.5 SSP scenarios",

    "base_em_n1_edgar": "EDGAR emissions at First NDC base year",
    "base_em_n2_edgar": "EDGAR emissions at Second NDC base year",
    "base_intensity_n1": "GHG intensity at First NDC base year",
    "base_intensity_n2": "GHG intensity at Second NDC base year",
    "gdp_target_n1": "GDP at First NDC target year",
    "gdp_target_n2": "GDP at Second NDC target year",

    "target_n1_edgar": "Harmonized target for First NDC",
    "target_n2_edgar": "Harmonized target for Second NDC",
    "target_main_edgar": "Main harmonized target from latest NDC",

    "target_method_n1": "Method used for First NDC target",
    "target_method_n2": "Method used for Second NDC target",
    "target_method_main": "Method used for main target",

    "gap_n1_edgar": "Absolute Gap-to-Target for First NDC, production-based",
    "gap_n2_edgar": "Absolute Gap-to-Target for Second NDC, production-based",
    "gap_main_edgar": "Main absolute Gap-to-Target, production-based",

    "gap_n1_edgar_pct": "Relative Gap-to-Target for First NDC, production-based",
    "gap_n2_edgar_pct": "Relative Gap-to-Target for Second NDC, production-based",
    "gap_main_edgar_pct": "Main relative Gap-to-Target, production-based",

    "ObservedReductionEdgar": "Observed annual reduction in production-based emissions",
    "ObservedReductionCons": "Observed annual reduction in consumption-based emissions",
}

bau_robustness_label_map = {}

for ndc in ["n1", "n2"]:
    ndc_label = "First NDC" if ndc == "n1" else "Second NDC"

    for bau_name, bau_label in bau_robustness_variants.items():

        bau_robustness_label_map[f"bau_{bau_name}"] = (
            f"Projected BAU emissions under {bau_label}"
        )

        bau_robustness_label_map[f"bau_{bau_name}_target_{ndc}"] = (
            f"{bau_label} BAU emissions at {ndc_label} target year"
        )

        bau_robustness_label_map[f"targ_{ndc}_{bau_name}"] = (
            f"{ndc_label} target using {bau_label} for BAU pledges"
        )

        bau_robustness_label_map[f"meth_{ndc}_{bau_name}"] = (
            f"Target method for {ndc_label}, {bau_label} robustness"
        )

        bau_robustness_label_map[f"gap_{ndc}_{bau_name}"] = (
            f"Absolute Gap-to-Target for {ndc_label}, {bau_label}"
        )

        bau_robustness_label_map[f"gappct_{ndc}_{bau_name}"] = (
            f"Relative Gap-to-Target for {ndc_label}, {bau_label}"
        )

        bau_robustness_label_map[f"yrs_{ndc}_{bau_name}"] = (
            f"Years to target for {ndc_label}, {bau_label}"
        )

        bau_robustness_label_map[f"dgap_{ndc}_{bau_name}"] = (
            f"Dynamic absolute gap for {ndc_label}, {bau_label}"
        )

        bau_robustness_label_map[f"dgappct_{ndc}_{bau_name}"] = (
            f"Dynamic relative gap for {ndc_label}, {bau_label}"
        )

        bau_robustness_label_map[f"feasabs_{ndc}_{bau_name}"] = (
            f"Absolute feasibility ratio for {ndc_label}, {bau_label}"
        )

        bau_robustness_label_map[f"feasdyn_{ndc}_{bau_name}"] = (
            f"Dynamic feasibility ratio for {ndc_label}, {bau_label}"
        )

dynamic_label_map = {
    "years_to_target_n1": "Years to First NDC target year",
    "years_to_target_n2": "Years to Second NDC target year",
    "years_to_target_main": "Years to main NDC target year",

    "dyn_gap_n1_edgar": "Dynamic absolute gap for First NDC, production-based",
    "dyn_gap_n1_edgar_pct": "Dynamic relative gap for First NDC, production-based",
    "dyn_gap_n2_edgar": "Dynamic absolute gap for Second NDC, production-based",
    "dyn_gap_n2_edgar_pct": "Dynamic relative gap for Second NDC, production-based",
    "dyn_gap_main_edgar": "Dynamic main absolute gap, production-based",
    "dyn_gap_main_edgar_pct": "Dynamic main relative gap, production-based",

    "feas_n1_edgar": "Dynamic feasibility ratio, First NDC, production-based",
    "feas_n2_edgar": "Dynamic feasibility ratio, Second NDC, production-based",
    "feas_main_edgar": "Dynamic feasibility ratio, main target, production-based",
}

feas_abs_label_map = {
    "feasabs_n1_edgar": "Absolute-gap feasibility ratio, First NDC, production-based",
    "feasabs_n2_edgar": "Absolute-gap feasibility ratio, Second NDC, production-based",
    "feasabs_main_edgar": "Absolute-gap feasibility ratio, main target, production-based",

    "feasabs_n1_uncond_edgar": "Absolute-gap feasibility ratio, First unconditional, production-based",
    "feasabs_n2_uncond_edgar": "Absolute-gap feasibility ratio, Second unconditional, production-based",
    "feasabs_main_uncond_edgar": "Absolute-gap feasibility ratio, main unconditional, production-based",

    "feasabs_n1_cond_edgar": "Absolute-gap feasibility ratio, First conditional, production-based",
    "feasabs_n2_cond_edgar": "Absolute-gap feasibility ratio, Second conditional, production-based",
    "feasabs_main_cond_edgar": "Absolute-gap feasibility ratio, main conditional, production-based",

    "feasabs_n1_cons": "Absolute-gap feasibility ratio, First NDC, consumption-based",
    "feasabs_n2_cons": "Absolute-gap feasibility ratio, Second NDC, consumption-based",
    "feasabs_main_cons": "Absolute-gap feasibility ratio, main target, consumption-based",
}

all_labels = dict(existing_var_labels)
all_labels.update(new_var_labels)
all_labels.update(dynamic_label_map)
all_labels.update(feas_abs_label_map)
all_labels.update(bau_robustness_label_map)

all_labels = {k: str(v)[:80] for k, v in all_labels.items() if k in df.columns}


# =========================================================
# ANALYSIS-READY DATASET
# =========================================================

df_analysis = df.copy()
df_analysis = df_analysis[~df_analysis["iso3"].isin(problem_countries)].copy()

gap_vars_keep = [col for col in df_analysis.columns if "gap" in col.lower()]

feas_vars_keep = [
    col for col in df_analysis.columns
    if col.lower().startswith("feas_")
    or col.lower().startswith("feasabs_")
    or col.lower().startswith("feasdyn_")
]

target_robust_vars_keep = [
    col for col in df_analysis.columns
    if col.startswith("targ_")
    or col.startswith("meth_")
    or col.startswith("gappct_")
    or col.startswith("dgap_")
    or col.startswith("dgappct_")
    or col.startswith("yrs_")
]

keep_cols = ["iso3", "year"] + gap_vars_keep + target_robust_vars_keep + feas_vars_keep
keep_cols = [col for col in keep_cols if col in df_analysis.columns]

df_analysis = df_analysis[keep_cols].copy()

required_gap_cols = [c for c in ["gap_n1_edgar", "gap_n2_edgar"] if c in df_analysis.columns]

if required_gap_cols:
    valid_countries = (
        df_analysis.groupby("iso3")[required_gap_cols]
        .apply(lambda x: x.notna().any().any())
    )
    valid_countries = valid_countries[valid_countries].index
    df_analysis = df_analysis[df_analysis["iso3"].isin(valid_countries)].copy()

df_analysis = df_analysis.sort_values(["iso3", "year"]).reset_index(drop=True)

print("\nDimensions base analysis-ready :", df_analysis.shape)
print("Nombre de pays conservés :", df_analysis["iso3"].nunique())

analysis_labels = {
    k: str(v)[:80]
    for k, v in all_labels.items()
    if k in df_analysis.columns
}


# =========================================================
# SECURITY CHECK BEFORE STATA EXPORT
# Remove duplicated column names
# =========================================================

duplicated_cols = df_analysis.columns[df_analysis.columns.duplicated()].tolist()

if duplicated_cols:
    print("\nColonnes dupliquées détectées avant export Stata :")
    print(duplicated_cols)

    df_analysis = df_analysis.loc[:, ~df_analysis.columns.duplicated()].copy()

    print("\nColonnes dupliquées supprimées. Nouvelle dimension :")
    print(df_analysis.shape)

# garder seulement les labels des colonnes restantes
analysis_labels = {
    k: str(v)[:80]
    for k, v in all_labels.items()
    if k in df_analysis.columns
}


# =========================================================
# LABELS COMPLETS + FALLBACK AUTOMATIQUE
# =========================================================

all_labels = dict(existing_var_labels)

# -----------------------------
# Labels généraux
# -----------------------------
manual_labels = {
    "iso3": "ISO3 country code",
    "year": "Year",
    "ndc_cycle_main": "Main NDC cycle retained for target construction",

    "bau_mean": "Mean BAU emissions across all selected RCP8.5 SSP scenarios",

    "base_em_n1_edgar": "EDGAR emissions at First NDC base year",
    "base_em_n2_edgar": "EDGAR emissions at Second NDC base year",
    "base_intensity_n1": "GHG intensity at First NDC base year",
    "base_intensity_n2": "GHG intensity at Second NDC base year",
    "base_gdp_n1": "GDP at First NDC base year",
    "base_gdp_n2": "GDP at Second NDC base year",
    "gdp_target_n1": "GDP at First NDC target year",
    "gdp_target_n2": "GDP at Second NDC target year",

    "ObservedReductionEdgar": "Observed annual reduction in production-based emissions",
    "ObservedReductionCons": "Observed annual reduction in consumption-based emissions",
    "AbsReductionEdgar": "Annual change in production-based emissions",
    "AbsReductionCons": "Annual change in consumption-based emissions",
    "RelaReductionEdgar": "Relative annual change in production-based emissions",
    "RelaReductionCons": "Relative annual change in consumption-based emissions",
}

all_labels.update(manual_labels)


# -----------------------------
# Labels des cibles, gaps, dyn gaps et faisabilité
# -----------------------------
cycles = {
    "n1": "First NDC",
    "n2": "Second NDC",
    "main": "main target",
}

variants = {
    "": "",
    "_uncond": " unconditional",
    "_cond": " conditional",
}

emissions_types = {
    "edgar": "production-based",
    "cons": "consumption-based",
}

for cyc, cyc_label in cycles.items():
    for suffix, suffix_label in variants.items():

        # Targets only for production-based harmonized target names
        target_col = f"target_{cyc}{suffix}_edgar"
        method_col = f"target_method_{cyc}{suffix}"

        if target_col in df.columns:
            all_labels[target_col] = f"Harmonized{suffix_label} target for {cyc_label}"

        if method_col in df.columns:
            all_labels[method_col] = f"Method used to construct {cyc_label}{suffix_label} target"

        for emtype, em_label in emissions_types.items():

            if emtype == "edgar":
                gap_col = f"gap_{cyc}{suffix}_edgar"
                gap_pct_col = f"gap_{cyc}{suffix}_edgar_pct"
                dyn_gap_col = f"dyn_gap_{cyc}{suffix}_edgar"
                dyn_gap_pct_col = f"dyn_gap_{cyc}{suffix}_edgar_pct"
                feasabs_col = f"feasabs_{cyc}{suffix}_edgar"
                feasdyn_col = f"feas_{cyc}{suffix}_edgar"
            else:
                gap_col = f"gap_{cyc}{suffix}_cons"
                gap_pct_col = f"gap_{cyc}{suffix}_cons_pct"
                dyn_gap_col = f"dyn_gap_{cyc}{suffix}_cons"
                dyn_gap_pct_col = f"dyn_gap_{cyc}{suffix}_cons_pct"
                feasabs_col = f"feasabs_{cyc}{suffix}_cons"
                feasdyn_col = f"feas_{cyc}{suffix}_cons"

            if gap_col in df.columns:
                all_labels[gap_col] = f"Absolute Gap-to-Target for {cyc_label}{suffix_label}, {em_label}"

            if gap_pct_col in df.columns:
                all_labels[gap_pct_col] = f"Relative Gap-to-Target for {cyc_label}{suffix_label}, {em_label}"

            if dyn_gap_col in df.columns:
                all_labels[dyn_gap_col] = f"Dynamic absolute gap for {cyc_label}{suffix_label}, {em_label}"

            if dyn_gap_pct_col in df.columns:
                all_labels[dyn_gap_pct_col] = f"Dynamic relative gap for {cyc_label}{suffix_label}, {em_label}"

            if feasabs_col in df.columns:
                all_labels[feasabs_col] = f"Absolute-gap feasibility ratio for {cyc_label}{suffix_label}, {em_label}"

            if feasdyn_col in df.columns:
                all_labels[feasdyn_col] = f"Dynamic feasibility ratio for {cyc_label}{suffix_label}, {em_label}"


# -----------------------------
# Labels Kyoto
# -----------------------------
kyoto_labels = {
    "kyoto_base_edgar": "Production emissions in 1990 for Kyoto target",
    "target_kyoto_edgar": "Kyoto target from 1990 production emissions",
    "gap_kyoto_edgar": "Absolute Gap-to-Target for Kyoto Protocol",
    "gap_kyoto_edgar_pct": "Relative Gap-to-Target for Kyoto Protocol",
}

for k, v in kyoto_labels.items():
    if k in df.columns:
        all_labels[k] = v


# -----------------------------
# Labels BAU robustesse full-sample
# -----------------------------
for ndc in ["n1", "n2"]:
    ndc_label = "First NDC" if ndc == "n1" else "Second NDC"

    for bau_name, bau_label in bau_robustness_variants.items():

        label_dict = {
            f"bau_{bau_name}": f"Projected BAU emissions under {bau_label}",
            f"bau_{bau_name}_target_{ndc}": f"{bau_label} BAU emissions at {ndc_label} target year",

            f"targ_{ndc}_{bau_name}": f"{ndc_label} target using {bau_label} for BAU pledges",
            f"meth_{ndc}_{bau_name}": f"Target method for {ndc_label}, {bau_label} robustness",

            f"gap_{ndc}_{bau_name}": f"Absolute Gap-to-Target for {ndc_label}, {bau_label}",
            f"gappct_{ndc}_{bau_name}": f"Relative Gap-to-Target for {ndc_label}, {bau_label}",

            f"yrs_{ndc}_{bau_name}": f"Years to target for {ndc_label}, {bau_label}",
            f"dgap_{ndc}_{bau_name}": f"Dynamic absolute gap for {ndc_label}, {bau_label}",
            f"dgappct_{ndc}_{bau_name}": f"Dynamic relative gap for {ndc_label}, {bau_label}",

            f"feasabs_{ndc}_{bau_name}": f"Absolute feasibility ratio for {ndc_label}, {bau_label}",
            f"feasdyn_{ndc}_{bau_name}": f"Dynamic feasibility ratio for {ndc_label}, {bau_label}",
        }

        for k, v in label_dict.items():
            if k in df.columns:
                all_labels[k] = v


# =========================================================
# ANALYSIS-READY DATASET
# =========================================================

df_analysis = df.copy()
df_analysis = df_analysis[~df_analysis["iso3"].isin(problem_countries)].copy()

gap_vars_keep = [col for col in df_analysis.columns if "gap" in col.lower()]

feas_vars_keep = [
    col for col in df_analysis.columns
    if col.lower().startswith("feas_")
    or col.lower().startswith("feasabs_")
    or col.lower().startswith("feasdyn_")
]

target_robust_vars_keep = [
    col for col in df_analysis.columns
    if col.startswith("targ_")
    or col.startswith("meth_")
    or col.startswith("gappct_")
    or col.startswith("dgap_")
    or col.startswith("dgappct_")
    or col.startswith("yrs_")
]

target_main_vars_keep = [
    col for col in df_analysis.columns
    if col.startswith("target_")
    or col.startswith("bau_")
]

keep_cols = (
    ["iso3", "year"]
    + target_main_vars_keep
    + gap_vars_keep
    + target_robust_vars_keep
    + feas_vars_keep
)

keep_cols = [col for col in keep_cols if col in df_analysis.columns]

# supprimer doublons dans la liste keep_cols
keep_cols = list(dict.fromkeys(keep_cols))

df_analysis = df_analysis[keep_cols].copy()

required_gap_cols = [c for c in ["gap_n1_edgar", "gap_n2_edgar"] if c in df_analysis.columns]

if required_gap_cols:
    valid_countries = (
        df_analysis.groupby("iso3")[required_gap_cols]
        .apply(lambda x: x.notna().any().any())
    )
    valid_countries = valid_countries[valid_countries].index
    df_analysis = df_analysis[df_analysis["iso3"].isin(valid_countries)].copy()

df_analysis = df_analysis.sort_values(["iso3", "year"]).reset_index(drop=True)

print("\nDimensions base analysis-ready :", df_analysis.shape)
print("Nombre de pays conservés :", df_analysis["iso3"].nunique())


# =========================================================
# SECURITY CHECK BEFORE STATA EXPORT
# =========================================================

duplicated_cols = df_analysis.columns[df_analysis.columns.duplicated()].tolist()

if duplicated_cols:
    print("\nColonnes dupliquées détectées avant export Stata :")
    print(duplicated_cols)
    df_analysis = df_analysis.loc[:, ~df_analysis.columns.duplicated()].copy()
    print("\nColonnes dupliquées supprimées. Nouvelle dimension :")
    print(df_analysis.shape)


# =========================================================
# FALLBACK LABELS : GARANTIR 100% DES LABELS
# =========================================================

missing_labels = [col for col in df_analysis.columns if col not in all_labels]

if missing_labels:
    print("\nVariables sans label détectées et labellisées automatiquement :")
    print(missing_labels)

    for col in missing_labels:
        label = col.replace("_", " ")

        label = label.replace("n1", "First NDC")
        label = label.replace("n2", "Second NDC")
        label = label.replace("main", "main target")
        label = label.replace("edgar", "production-based")
        label = label.replace("cons", "consumption-based")
        label = label.replace("uncond", "unconditional")
        label = label.replace("cond", "conditional")
        label = label.replace("pct", "relative")
        label = label.replace("dyn", "dynamic")
        label = label.replace("feasabs", "absolute feasibility")
        label = label.replace("feasdyn", "dynamic feasibility")
        label = label.replace("gap", "Gap-to-Target")

        all_labels[col] = label.capitalize()


analysis_labels = {
    k: str(v)[:80]
    for k, v in all_labels.items()
    if k in df_analysis.columns
}

# contrôle final
still_missing = [col for col in df_analysis.columns if col not in analysis_labels]

if still_missing:
    print("\nATTENTION : variables encore sans label :")
    print(still_missing)
else:
    print("\nToutes les variables exportées ont un label.")


df_analysis.to_stata(
    output_analysis,
    write_index=False,
    version=118,
    variable_labels=analysis_labels
)

print("\nBase analysis sauvegardée :", output_analysis)



df_analysis.to_stata(
    output_analysis,
    write_index=False,
    version=118,
    variable_labels=analysis_labels
)

print("\nBase analysis sauvegardée :", output_analysis)

preview_cols = [
    "iso3", "year",
    "gap_n1_edgar",
    "gap_n2_edgar",
    "gap_main_edgar",
    "gap_n1_r85s2m",
    "gap_n1_r85s2i",
    "gap_n1_r85s2o",
    "gap_n1_r85s2p",
    "gap_n2_r85s2m",
    "gap_n2_r85s2i",
    "gap_n2_r85s2o",
    "gap_n2_r85s2p",
    "gappct_n1_r85s2m",
    "gappct_n2_r85s2m",
    "dgap_n1_r85s2m",
    "dgap_n2_r85s2m",
    "feasabs_n1_edgar",
    "feasabs_n2_edgar",
    "feasabs_n1_r85s2m",
    "feasabs_n2_r85s2m",
    "feasdyn_n1_r85s2m",
    "feasdyn_n2_r85s2m",
]

preview_cols = [c for c in preview_cols if c in df_analysis.columns]

print("\nAperçu :")
print(df_analysis[preview_cols].head(20))
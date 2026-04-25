from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.colors import TwoSlopeNorm
import matplotlib.patches as mpatches


# =========================================================
# 0. PATHS
# =========================================================
working_dir = Path(r"C:\\Users\\richm\\Desktop\\NDC DATA NEW\\NDC Completed\\Final Data")
input_file = working_dir / "Data_analysis_gap_only.dta"
graph_dir = working_dir / "Graphs"
graph_dir.mkdir(exist_ok=True)

# =========================================================
# 1. LOAD DATA
# =========================================================
data = pd.read_excel(working_dir / "ICR.xlsx")
df = pd.read_stata(input_file)

# Harmoniser iso3 avant fusion
df["iso3"] = df["iso3"].astype(str).str.strip().str.upper()
data["iso3"] = data["iso3"].astype(str).str.strip().str.upper()

# Sécuriser les doublons dans ICR
data = data.drop_duplicates(subset=["iso3"], keep="first").copy()

# Fusion
df = df.merge(data, on="iso3", how="left")

print("Dimensions :", df.shape)
print("Colonnes disponibles :")
print(df.columns.tolist())

# =========================================================
# 2. BASIC SETTINGS
# =========================================================
country_col = "iso3"
year_col = "year"
income_col = "Incomegroup"
region_col = "Region"

PARIS_START = 2015
KYOTO_END = 2015

# =========================================================
# 3. VARIABLES
# =========================================================

# --- Gaps absolus pour la dynamique globale
gap_abs_global = {
    "Gap to Kyoto target": "gap_kyoto_edgar",
    "Gap to First target": "gap_n1_edgar",
    "Gap to Second target": "gap_n2_edgar",
    "Gap to Main target": "gap_main_edgar",
    "Gap to First target (Unconditional)": "gap_n1_uncond_edgar",
    "Gap to Second target (Unconditional)": "gap_n2_uncond_edgar",
    "Gap to First target (Conditional)": "gap_n1_cond_edgar",
    "Gap to Second target (Conditional)": "gap_n2_cond_edgar",
}

# --- Gaps relatifs principaux
gap_rel_main = {
    "Kyoto": "gap_kyoto_edgar_pct",
    "First NDC": "gap_n1_edgar_pct",
    "Second NDC": "gap_n2_edgar_pct",
    "Main target": "gap_main_edgar_pct",
}

# --- Faisabilité
feas_vars = {
    "First NDC": "feas_n1_edgar",
    "Second NDC": "feas_n2_edgar",
    "Main target": "feas_main_edgar",
}

# --- Couleurs
color_map_global = {
    "Gap to Kyoto target": "#1f77b4",
    "Gap to First target": "#ff7f0e",
    "Gap to Second target": "#2ca02c",
    "Gap to Main target": "#17becf",
    "Gap to First target (Unconditional)": "#d62728",
    "Gap to Second target (Unconditional)": "#9467bd",
    "Gap to First target (Conditional)": "#8c564b",
    "Gap to Second target (Conditional)": "#e377c2",
}

color_map_rel = {
    "Kyoto": "#1b9e77",
    "First NDC": "#d95f02",
    "Second NDC": "#7570b3",
    "Main target": "#1f78b4",
}

feas_color_map = {
    "First NDC": "#4daf4a",
    "Second NDC": "#984ea3",
    "Main target": "#377eb8",
}

income_order = [
    "Low income",
    "Lower middle income",
    "Upper middle income",
    "High income"
]

# =========================================================
# 4. TIME FILTERS
# =========================================================
df_kyoto = df[df[year_col] <= KYOTO_END].copy()
df_paris = df[df[year_col] >= PARIS_START].copy()

cycle_df_map = {
    "Kyoto": df_kyoto,
    "First NDC": df_paris,
    "Second NDC": df_paris,
    "Main target": df_paris,
}

# =========================================================
# 4.b. HELPER FUNCTIONS
# =========================================================
def winsorize_series(s, lower_q=0.05, upper_q=0.95):
    s = s.copy()
    if s.dropna().empty:
        return s
    lo = s.quantile(lower_q)
    hi = s.quantile(upper_q)
    return s.clip(lower=lo, upper=hi)

def symmetric_ylim_from_df(df_plot, margin=0.15, min_span=0.5):
    vals = df_plot.to_numpy().astype(float).ravel()
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return (-1, 1)

    max_abs = np.max(np.abs(vals))
    max_abs = max(max_abs, min_span)
    lim = max_abs * (1 + margin)
    return (-lim, lim)

def add_value_labels(ax, bars, fmt="{:.2f}", fontsize=8):
    for bar in bars:
        h = bar.get_height()
        if np.isnan(h):
            continue
        ax.annotate(
            fmt.format(h),
            xy=(bar.get_x() + bar.get_width()/2, h),
            xytext=(0, 3 if h >= 0 else -10),
            textcoords="offset points",
            ha="center",
            va="bottom" if h >= 0 else "top",
            fontsize=fontsize
        )

# =========================================================
# 5. GLOBAL DYNAMIC OF COMMITMENT ALIGNMENT (ABSOLUTE GAPS)
# =========================================================
plt.figure(figsize=(12, 6))

for label, var in gap_abs_global.items():
    if var not in df.columns:
        continue

    if "Kyoto" in label:
        temp = df_kyoto.groupby(year_col)[var].mean().reset_index()
    else:
        temp = df_paris.groupby(year_col)[var].mean().reset_index()

    if not temp.empty:
        plt.plot(
            temp[year_col],
            temp[var],
            label=label,
            linewidth=2.0,
            color=color_map_global[label]
        )

plt.axvline(PARIS_START, color="#74c476", linestyle="--", linewidth=1.2)
plt.xlabel("Year", fontsize=12)
plt.ylabel("Gap to target (Gg CO$_2$eq)", fontsize=12)
plt.title("Global Dynamic of Commitment Alignment", fontsize=14)
plt.legend(fontsize=9, loc="upper left", frameon=True, ncol=2)
plt.grid(axis="both", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(graph_dir / "Global_Dynamic_Commitment_Alignment_absolute.png", dpi=300, bbox_inches="tight")
plt.show()

# =========================================================
# 6. DISTRIBUTION OF RELATIVE GAPS (ONE VALUE PER COUNTRY, CYCLE-CONSISTENT)
# =========================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharey=True)

plot_specs = [
    ("Kyoto", "gap_kyoto_edgar_pct", color_map_rel["Kyoto"], df_kyoto),
    ("First NDC", "gap_n1_edgar_pct", color_map_rel["First NDC"], df_paris),
    ("Second NDC", "gap_n2_edgar_pct", color_map_rel["Second NDC"], df_paris),
    ("Main target", "gap_main_edgar_pct", color_map_rel["Main target"], df_paris),
]

for ax, (title, var, color, data_use) in zip(axes.flatten(), plot_specs):
    if var in data_use.columns:
        series = data_use.groupby(country_col)[var].mean().dropna()

        if len(series) > 0:
            q01 = series.quantile(0.01)
            q99 = series.quantile(0.99)
            series = series.clip(lower=q01, upper=q99)

            ax.hist(series, bins=20, color=color, edgecolor="white")
            ax.axvline(0, color="black", linestyle="--", linewidth=1)

        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Relative gap-to-target", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

axes[0, 0].set_ylabel("Number of countries", fontsize=10)
axes[1, 0].set_ylabel("Number of countries", fontsize=10)

plt.tight_layout()
plt.savefig(graph_dir / "Distribution_relative_gaps.png", dpi=300, bbox_inches="tight")
plt.show()

# =========================================================
# 7. GAP RELATIF PAR GROUPE DE REVENU (SCALE-CORRECTED)
# =========================================================
if income_col in df.columns:
    country_income = (
        df[[country_col, income_col]]
        .dropna(subset=[income_col])
        .drop_duplicates(subset=[country_col])
    )

    agg_kyoto = df_kyoto.groupby(country_col)[["gap_kyoto_edgar_pct"]].mean().reset_index()
    agg_n1 = df_paris.groupby(country_col)[["gap_n1_edgar_pct"]].mean().reset_index()
    agg_n2 = df_paris.groupby(country_col)[["gap_n2_edgar_pct"]].mean().reset_index()
    agg_main = df_paris.groupby(country_col)[["gap_main_edgar_pct"]].mean().reset_index()

    agg_rel_income = (
        agg_kyoto
        .merge(agg_n1, on=country_col, how="outer")
        .merge(agg_n2, on=country_col, how="outer")
        .merge(agg_main, on=country_col, how="outer")
    )

    df_inc = agg_rel_income.merge(country_income, on=country_col, how="left").dropna(subset=[income_col])

    for col in ["gap_kyoto_edgar_pct", "gap_n1_edgar_pct", "gap_n2_edgar_pct", "gap_main_edgar_pct"]:
        if col in df_inc.columns:
            df_inc[col + "_plot"] = winsorize_series(df_inc[col], lower_q=0.05, upper_q=0.95)

    group_means_income = (
        df_inc.groupby(income_col)[
            ["gap_kyoto_edgar_pct_plot", "gap_n1_edgar_pct_plot", "gap_n2_edgar_pct_plot", "gap_main_edgar_pct_plot"]
        ]
        .mean()
        .reindex(income_order)
        .dropna(how="all")
    )

    x = np.arange(len(group_means_income))
    width = 0.2

    fig, ax = plt.subplots(figsize=(11, 5))
    b1 = ax.bar(x - 1.5*width, group_means_income["gap_kyoto_edgar_pct_plot"], width=width, label="Kyoto", color=color_map_rel["Kyoto"])
    b2 = ax.bar(x - 0.5*width, group_means_income["gap_n1_edgar_pct_plot"], width=width, label="First NDC", color=color_map_rel["First NDC"])
    b3 = ax.bar(x + 0.5*width, group_means_income["gap_n2_edgar_pct_plot"], width=width, label="Second NDC", color=color_map_rel["Second NDC"])
    b4 = ax.bar(x + 1.5*width, group_means_income["gap_main_edgar_pct_plot"], width=width, label="Main target", color=color_map_rel["Main target"])

    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(group_means_income.index, rotation=15)
    ax.set_ylabel("Average relative gap-to-target", fontsize=12)
    ax.set_title("Gap-to-Target Across Income Groups", fontsize=14)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    ymin, ymax = symmetric_ylim_from_df(group_means_income)
    ax.set_ylim(ymin, ymax)

    plt.tight_layout()
    plt.savefig(graph_dir / "Gap_by_income_group_relative.png", dpi=300, bbox_inches="tight")
    plt.show()

# =========================================================
# 8. GAP RELATIF PAR REGION (SCALE-CORRECTED)
# =========================================================
if region_col in df.columns:
    country_region = (
        df[[country_col, region_col]]
        .dropna(subset=[region_col])
        .drop_duplicates(subset=[country_col])
    )

    agg_kyoto = df_kyoto.groupby(country_col)[["gap_kyoto_edgar_pct"]].mean().reset_index()
    agg_n1 = df_paris.groupby(country_col)[["gap_n1_edgar_pct"]].mean().reset_index()
    agg_n2 = df_paris.groupby(country_col)[["gap_n2_edgar_pct"]].mean().reset_index()
    agg_main = df_paris.groupby(country_col)[["gap_main_edgar_pct"]].mean().reset_index()

    agg_rel_region = (
        agg_kyoto
        .merge(agg_n1, on=country_col, how="outer")
        .merge(agg_n2, on=country_col, how="outer")
        .merge(agg_main, on=country_col, how="outer")
    )

    df_reg = agg_rel_region.merge(country_region, on=country_col, how="left").dropna(subset=[region_col])

    for col in ["gap_kyoto_edgar_pct", "gap_n1_edgar_pct", "gap_n2_edgar_pct", "gap_main_edgar_pct"]:
        if col in df_reg.columns:
            df_reg[col + "_plot"] = winsorize_series(df_reg[col], lower_q=0.05, upper_q=0.95)

    group_means_region = (
        df_reg.groupby(region_col)[
            ["gap_kyoto_edgar_pct_plot", "gap_n1_edgar_pct_plot", "gap_n2_edgar_pct_plot", "gap_main_edgar_pct_plot"]
        ]
        .mean()
        .sort_index()
    )

    x = np.arange(len(group_means_region))
    width = 0.2

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(x - 1.5*width, group_means_region["gap_kyoto_edgar_pct_plot"], width=width, label="Kyoto", color=color_map_rel["Kyoto"])
    ax.bar(x - 0.5*width, group_means_region["gap_n1_edgar_pct_plot"], width=width, label="First NDC", color=color_map_rel["First NDC"])
    ax.bar(x + 0.5*width, group_means_region["gap_n2_edgar_pct_plot"], width=width, label="Second NDC", color=color_map_rel["Second NDC"])
    ax.bar(x + 1.5*width, group_means_region["gap_main_edgar_pct_plot"], width=width, label="Main target", color=color_map_rel["Main target"])

    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(group_means_region.index, rotation=20, ha="right")
    ax.set_ylabel("Average relative gap-to-target", fontsize=12)
    ax.set_title("Gap-to-Target Across Regions", fontsize=14)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    ymin, ymax = symmetric_ylim_from_df(group_means_region)
    ax.set_ylim(ymin, ymax)

    plt.tight_layout()
    plt.savefig(graph_dir / "Gap_by_region_relative.png", dpi=300, bbox_inches="tight")
    plt.show()

# =========================================================
# 9. TOP / BOTTOM PERFORMERS (RELATIVE GAPS, CYCLE-CONSISTENT)
# =========================================================
def plot_top_bottom(df_country, var, title, filename, winsorize_top=True):
    sub = df_country[[country_col, var]].dropna().copy()

    if sub.empty:
        return

    top10 = sub.nsmallest(10, var).copy()
    bottom10 = sub.nlargest(10, var).copy()

    if winsorize_top:
        upper_cap = bottom10[var].quantile(0.90)
        bottom10[var + "_plot"] = bottom10[var].clip(upper=upper_cap)
    else:
        bottom10[var + "_plot"] = bottom10[var]

    top10[var + "_plot"] = top10[var]

    top10 = top10.set_index(country_col).sort_values(var + "_plot")
    bottom10 = bottom10.set_index(country_col).sort_values(var + "_plot")

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))

    top10[var + "_plot"].plot.barh(
        ax=axes[0],
        color="#2E8B57",
        edgecolor="black"
    )
    axes[0].set_title(f"Top 10 Countries – {title}", fontsize=13)
    axes[0].set_xlabel("Relative gap-to-target", fontsize=11)
    axes[0].set_ylabel("Countries", fontsize=11)
    axes[0].grid(axis="x", linestyle="--", alpha=0.4)

    bottom10[var + "_plot"].plot.barh(
        ax=axes[1],
        color="#C0392B",
        edgecolor="black"
    )
    axes[1].set_title(f"Bottom 10 Countries – {title}", fontsize=13)
    axes[1].set_xlabel("Relative gap-to-target", fontsize=11)
    axes[1].set_ylabel("Countries", fontsize=11)
    axes[1].grid(axis="x", linestyle="--", alpha=0.4)

    for i, (idx, row) in enumerate(bottom10.iterrows()):
        axes[1].text(
            row[var + "_plot"],
            i,
            f"  {row[var]:.1f}",
            va="center",
            fontsize=9
        )

    plt.tight_layout()
    plt.savefig(graph_dir / filename, dpi=300, bbox_inches="tight")
    plt.show()

df_country_kyoto = df_kyoto.groupby(country_col)[["gap_kyoto_edgar_pct"]].mean().reset_index()
df_country_n1 = df_paris.groupby(country_col)[["gap_n1_edgar_pct"]].mean().reset_index()
df_country_n2 = df_paris.groupby(country_col)[["gap_n2_edgar_pct"]].mean().reset_index()
df_country_main = df_paris.groupby(country_col)[["gap_main_edgar_pct"]].mean().reset_index()

plot_top_bottom(df_country_kyoto, "gap_kyoto_edgar_pct", "Kyoto Protocol", "Top_Bottom_Kyoto.png")
plot_top_bottom(df_country_n1, "gap_n1_edgar_pct", "First NDC Cycle", "Top_Bottom_First_NDC.png")
plot_top_bottom(df_country_n2, "gap_n2_edgar_pct", "Second NDC Cycle", "Top_Bottom_Second_NDC.png")
plot_top_bottom(df_country_main, "gap_main_edgar_pct", "Main Target", "Top_Bottom_Main_Target.png")

# =========================================================
# 10. WORLD MAPS (RELATIVE GAPS)
# =========================================================
world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
world = world[world["name"] != "Antarctica"].copy()

years_map = {
    "Kyoto": 2012,
    "First NDC": 2023,
    "Second NDC": 2023,
    "Main target": 2023
}

map_specs = {
    "Kyoto": ("gap_kyoto_edgar_pct", df_kyoto),
    "First NDC": ("gap_n1_edgar_pct", df_paris),
    "Second NDC": ("gap_n2_edgar_pct", df_paris),
    "Main target": ("gap_main_edgar_pct", df_paris),
}

all_vals = []
for label, (var, data_use) in map_specs.items():
    if var in data_use.columns:
        year_sel = years_map[label]
        tmp = data_use.loc[data_use[year_col] == year_sel, [country_col, var]].dropna()
        tmp = tmp.groupby(country_col, as_index=False)[var].mean()
        if not tmp.empty:
            all_vals.append(tmp[var])

if len(all_vals) > 0:
    all_vals_concat = pd.concat(all_vals)
    vmin = min(all_vals_concat.quantile(0.05), 0)
    vmax = max(all_vals_concat.quantile(0.95), 0)
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    for label, (var, data_use) in map_specs.items():
        if var not in data_use.columns:
            continue

        year_sel = years_map[label]
        tmp = data_use.loc[data_use[year_col] == year_sel, [country_col, var]].dropna()
        tmp = tmp.groupby(country_col, as_index=False)[var].mean()

        map_df = world.merge(tmp, how="left", left_on="iso_a3", right_on=country_col)

        fig, ax = plt.subplots(figsize=(14, 8))
        map_df.plot(
            column=var,
            cmap="RdBu_r",
            linewidth=0.3,
            edgecolor="black",
            ax=ax,
            legend=True,
            norm=norm,
            missing_kwds={
                "color": "lightgrey",
                "edgecolor": "white",
                "hatch": "///"
            },
            legend_kwds={
                "label": "Relative gap-to-target",
                "shrink": 0.7
            }
        )

        missing_patch = mpatches.Patch(facecolor="lightgrey", hatch="///", label="No data")
        ax.legend(handles=[missing_patch], loc="lower left", fontsize=10, frameon=True)

        ax.set_title(f"World Map of the Gap-to-Target Indicator ({label}, {year_sel})", fontsize=15)
        ax.axis("off")

        plt.tight_layout()
        plt.savefig(graph_dir / f"Map_{label.replace(' ', '_')}_{year_sel}.png", dpi=300, bbox_inches="tight")
        plt.show()

# =========================================================
# 11. FEASIBILITY: DISTRIBUTION (PARIS ONLY)
# =========================================================
fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)

feas_specs = [
    ("First NDC", "feas_n1_edgar", feas_color_map["First NDC"]),
    ("Second NDC", "feas_n2_edgar", feas_color_map["Second NDC"]),
    ("Main target", "feas_main_edgar", feas_color_map["Main target"])
]

for ax, (title, var, color) in zip(axes, feas_specs):
    if var in df_paris.columns:
        series = df_paris.groupby(country_col)[var].mean().dropna()

        if len(series) > 0:
            q01 = series.quantile(0.01)
            q99 = series.quantile(0.99)
            series = series.clip(lower=q01, upper=q99)

            ax.hist(series, bins=20, color=color, edgecolor="white")
            ax.axvline(1, color="black", linestyle="--", linewidth=1)
            ax.axvline(0, color="grey", linestyle=":", linewidth=1)

        ax.set_title(f"{title} feasibility", fontsize=12)
        ax.set_xlabel("Feasibility ratio", fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

axes[0].set_ylabel("Number of countries", fontsize=10)
plt.tight_layout()
plt.savefig(graph_dir / "Feasibility_distribution.png", dpi=300, bbox_inches="tight")
plt.show()

# =========================================================
# 12. FEASIBILITY BY INCOME GROUP (PARIS ONLY, SCALE-CORRECTED)
# =========================================================
if income_col in df.columns:
    country_income = (
        df[[country_col, income_col]]
        .dropna(subset=[income_col])
        .drop_duplicates(subset=[country_col])
    )

    agg_feas = df_paris.groupby(country_col)[list(feas_vars.values())].mean().reset_index()
    df_inc_feas = agg_feas.merge(country_income, on=country_col, how="left").dropna(subset=[income_col])

    for col in feas_vars.values():
        if col in df_inc_feas.columns:
            df_inc_feas[col + "_plot"] = winsorize_series(df_inc_feas[col], lower_q=0.05, upper_q=0.95)

    group_feas = (
        df_inc_feas.groupby(income_col)[["feas_n1_edgar_plot", "feas_n2_edgar_plot", "feas_main_edgar_plot"]]
        .mean()
        .reindex(income_order)
        .dropna(how="all")
    )

    x = np.arange(len(group_feas))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width, group_feas["feas_n1_edgar_plot"], width=width, label="First NDC", color=feas_color_map["First NDC"])
    ax.bar(x,         group_feas["feas_n2_edgar_plot"], width=width, label="Second NDC", color=feas_color_map["Second NDC"])
    ax.bar(x + width, group_feas["feas_main_edgar_plot"], width=width, label="Main target", color=feas_color_map["Main target"])

    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.axhline(0, color="grey", linestyle=":", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(group_feas.index, rotation=15)
    ax.set_ylabel("Average feasibility ratio", fontsize=12)
    ax.set_title("Feasibility of NDC Commitments Across Income Groups", fontsize=14)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    vals = group_feas.to_numpy().astype(float).ravel()
    vals = vals[~np.isnan(vals)]
    if len(vals) > 0:
        ymin = min(vals.min(), 0) * 1.15
        ymax = max(vals.max(), 1) * 1.15
        if ymax - ymin < 2:
            ymax = ymin + 2
        ax.set_ylim(ymin, ymax)

    plt.tight_layout()
    plt.savefig(graph_dir / "Feasibility_by_income_group.png", dpi=300, bbox_inches="tight")
    plt.show()

# =========================================================
# 13. FEASIBILITY BY REGION (PARIS ONLY, SCALE-CORRECTED)
# =========================================================
if region_col in df.columns:
    country_region = (
        df[[country_col, region_col]]
        .dropna(subset=[region_col])
        .drop_duplicates(subset=[country_col])
    )

    agg_feas = df_paris.groupby(country_col)[list(feas_vars.values())].mean().reset_index()
    df_reg_feas = agg_feas.merge(country_region, on=country_col, how="left").dropna(subset=[region_col])

    for col in feas_vars.values():
        if col in df_reg_feas.columns:
            df_reg_feas[col + "_plot"] = winsorize_series(df_reg_feas[col], lower_q=0.05, upper_q=0.95)

    group_feas_region = (
        df_reg_feas.groupby(region_col)[["feas_n1_edgar_plot", "feas_n2_edgar_plot", "feas_main_edgar_plot"]]
        .mean()
        .sort_index()
    )

    x = np.arange(len(group_feas_region))
    width = 0.25

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(x - width, group_feas_region["feas_n1_edgar_plot"], width=width, label="First NDC", color=feas_color_map["First NDC"])
    ax.bar(x,         group_feas_region["feas_n2_edgar_plot"], width=width, label="Second NDC", color=feas_color_map["Second NDC"])
    ax.bar(x + width, group_feas_region["feas_main_edgar_plot"], width=width, label="Main target", color=feas_color_map["Main target"])

    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.axhline(0, color="grey", linestyle=":", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(group_feas_region.index, rotation=20, ha="right")
    ax.set_ylabel("Average feasibility ratio", fontsize=12)
    ax.set_title("Feasibility of NDC Commitments Across Regions", fontsize=14)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    vals = group_feas_region.to_numpy().astype(float).ravel()
    vals = vals[~np.isnan(vals)]
    if len(vals) > 0:
        ymin = min(vals.min(), 0) * 1.15
        ymax = max(vals.max(), 1) * 1.15
        if ymax - ymin < 2:
            ymax = ymin + 2
        ax.set_ylim(ymin, ymax)

    plt.tight_layout()
    plt.savefig(graph_dir / "Feasibility_by_region.png", dpi=300, bbox_inches="tight")
    plt.show()

print("\nToutes les figures ont été générées dans :", graph_dir)


# =========================================================
# 14. TOP / BOTTOM PERFORMERS (FEASIBILITY, PARIS ONLY)
#     VERSION ROBUSTE AUX VALEURS EXTREMES
# =========================================================

def plot_top_bottom_feasibility(
    df_country,
    var,
    title,
    filename,
    top_n=10,
    bottom_n=10,
    trim_quantile=0.90
):
    
    #Construit un graphe Top/Bottom 10 pour la faisabilité.

    #- Top 10 = plus fortes valeurs
   # - Bottom 10 = plus faibles valeurs
   # - Les barres sont tronquées visuellement pour éviter qu'une valeur extrême
    #  écrase toute la figure.
   # - Les vraies valeurs restent affichées en annotation.


    sub = df_country[[country_col, var]].dropna().copy()

    if sub.empty:
        print(f"Aucune donnée disponible pour {var}")
        return

    # Trier
    top10 = sub.nlargest(top_n, var).copy()
    bottom10 = sub.nsmallest(bottom_n, var).copy()

    # Seuils visuels pour éviter qu'un extrême écrase la figure
    # On tronque seulement pour l'affichage, pas pour les annotations
    top_cap = top10[var].quantile(trim_quantile)
    bottom_cap = bottom10[var].quantile(1 - trim_quantile)

    top10[var + "_plot"] = top10[var].clip(upper=top_cap)
    bottom10[var + "_plot"] = bottom10[var].clip(lower=bottom_cap)

    # Tri pour affichage vertical cohérent
    top10 = top10.sort_values(var + "_plot")
    bottom10 = bottom10.sort_values(var + "_plot")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # -------------------------
    # TOP 10
    # -------------------------
    axes[0].barh(
        top10[country_col],
        top10[var + "_plot"],
        color="#2E8B57",
        edgecolor="black"
    )
    axes[0].set_title(f"Top 10 Countries – {title}", fontsize=13)
    axes[0].set_xlabel("Feasibility ratio", fontsize=11)
    axes[0].set_ylabel("Countries", fontsize=11)
    axes[0].axvline(1, color="black", linestyle="--", linewidth=1)
    axes[0].axvline(0, color="grey", linestyle=":", linewidth=1)
    axes[0].grid(axis="x", linestyle="--", alpha=0.4)

    xlim_left_top = min(0, top10[var + "_plot"].min()) * 1.1
    xlim_right_top = max(top10[var + "_plot"].max(), 1) * 1.1
    axes[0].set_xlim(xlim_left_top, xlim_right_top)

    for i, (_, row) in enumerate(top10.iterrows()):
        shown_value = row[var + "_plot"]
        true_value = row[var]

        # Annotation de la vraie valeur
        axes[0].text(
            shown_value + (xlim_right_top - xlim_left_top) * 0.015,
            i,
            f"{true_value:.1f}",
            va="center",
            fontsize=9
        )

        # Petite flèche si tronqué
        if true_value > shown_value:
            axes[0].text(
                shown_value - (xlim_right_top - xlim_left_top) * 0.03,
                i,
                "",
                va="center",
                ha="center",
                fontsize=10,
                color="black"
            )

    # -------------------------
    # BOTTOM 10
    # -------------------------
    axes[1].barh(
        bottom10[country_col],
        bottom10[var + "_plot"],
        color="#C0392B",
        edgecolor="black"
    )
    axes[1].set_title(f"Bottom 10 Countries – {title}", fontsize=13)
    axes[1].set_xlabel("Feasibility ratio", fontsize=11)
    axes[1].set_ylabel("Countries", fontsize=11)
    axes[1].axvline(1, color="black", linestyle="--", linewidth=1)
    axes[1].axvline(0, color="grey", linestyle=":", linewidth=1)
    axes[1].grid(axis="x", linestyle="--", alpha=0.4)

    xlim_left_bot = min(bottom10[var + "_plot"].min(), 0) * 1.1
    xlim_right_bot = max(1, bottom10[var + "_plot"].max()) * 1.1
    axes[1].set_xlim(xlim_left_bot, xlim_right_bot)

    for i, (_, row) in enumerate(bottom10.iterrows()):
        shown_value = row[var + "_plot"]
        true_value = row[var]

        # Annotation de la vraie valeur
        axes[1].text(
            shown_value + (xlim_right_bot - xlim_left_bot) * 0.015,
            i,
            f"{true_value:.1f}",
            va="center",
            fontsize=9
        )

        # Petite flèche si tronqué
        if true_value < shown_value:
            axes[1].text(
                shown_value + (xlim_right_bot - xlim_left_bot) * 0.03,
                i,
                "",
                va="center",
                ha="center",
                fontsize=10,
                color="black"
            )

    plt.tight_layout()
    plt.savefig(graph_dir / filename, dpi=300, bbox_inches="tight")
    plt.show()


# ---------------------------------------------------------
# Agrégation pays (Paris only) pour la faisabilité
# ---------------------------------------------------------
df_country_feas_n1 = df_paris.groupby(country_col)[["feas_n1_edgar"]].mean().reset_index()
df_country_feas_n2 = df_paris.groupby(country_col)[["feas_n2_edgar"]].mean().reset_index()
df_country_feas_main = df_paris.groupby(country_col)[["feas_main_edgar"]].mean().reset_index()

# ---------------------------------------------------------
# Graphes Top / Bottom 10 faisabilité
# ---------------------------------------------------------
plot_top_bottom_feasibility(
    df_country_feas_n1,
    "feas_n1_edgar",
    "First NDC Cycle",
    "Top_Bottom_Feasibility_First_NDC.png",
    trim_quantile=0.90
)

plot_top_bottom_feasibility(
    df_country_feas_n2,
    "feas_n2_edgar",
    "Second NDC Cycle",
    "Top_Bottom_Feasibility_Second_NDC.png",
    trim_quantile=0.90
)

plot_top_bottom_feasibility(
    df_country_feas_main,
    "feas_main_edgar",
    "Main Target",
    "Top_Bottom_Feasibility_Main_Target.png",
    trim_quantile=0.90
)


# ---------------------------------------------------------
# Agrégation pays (Paris only) pour la faisabilité absolue
# ---------------------------------------------------------
df_country_feasabs_n1 = df_paris.groupby(country_col)[["feasabs_n1_edgar"]].mean().reset_index()
df_country_feasabs_n2 = df_paris.groupby(country_col)[["feasabs_n2_edgar"]].mean().reset_index()
df_country_feasabs_main = df_paris.groupby(country_col)[["feasabs_main_edgar"]].mean().reset_index()

# ---------------------------------------------------------
# Graphes Top / Bottom 10 faisabilité absolue
# ---------------------------------------------------------
plot_top_bottom_feasibility(
    df_country_feasabs_n1,
    "feasabs_n1_edgar",
    "First NDC Cycle (Absolute-Gap Feasibility)",
    "Top_Bottom_FeasibilityAbs_First_NDC.png",
    trim_quantile=0.90
)

plot_top_bottom_feasibility(
    df_country_feasabs_n2,
    "feasabs_n2_edgar",
    "Second NDC Cycle (Absolute-Gap Feasibility)",
    "Top_Bottom_FeasibilityAbs_Second_NDC.png",
    trim_quantile=0.90
)

plot_top_bottom_feasibility(
    df_country_feasabs_main,
    "feasabs_main_edgar",
    "Main Target (Absolute-Gap Feasibility)",
    "Top_Bottom_FeasibilityAbs_Main_Target.png",
    trim_quantile=0.90
)


from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ======================================================
# PATHS
# ======================================================

working_dir = Path(r"C:\Users\richm\Desktop\NDC DATA NEW\NDC Completed\Final Data")
input_file = working_dir / "Data_analysis_gap_only.dta"

graph_dir = working_dir / "Graphs"
graph_dir.mkdir(exist_ok=True)

df = pd.read_stata(input_file)


# ======================================================
# SETTINGS
# ======================================================

country_col = "iso3"
year_col = "year"

start_year = 2015
end_year = 2024

df_paris = df[df[year_col].between(start_year, end_year)].copy()


# ======================================================
# HELPER FUNCTIONS
# ======================================================

def country_mean_pair(data, x, y):
    """
    Compute country-level mean values over the selected Paris-period window.
    This avoids empty panels when a variable is missing in the latest year.
    """
    tmp = (
        data[[country_col, x, y]]
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=[x, y])
        .groupby(country_col, as_index=False)[[x, y]]
        .mean()
    )
    return tmp


def plot_robustness_panel(ax, data, x, y, title, ndc_label, y_label_name):
    """
    Scatter plot comparing the baseline production-based Gap-to-Target
    with an alternative specification.
    """
    if data.empty or data[x].nunique() < 2 or data[y].nunique() < 2:
        ax.text(
            0.5, 0.5,
            "No sufficient data",
            ha="center",
            va="center",
            fontsize=11
        )
        ax.set_title(title, fontsize=11, pad=12)
        ax.set_xlabel(f"Gap-to-Target ({ndc_label}, production-based)", fontsize=10)
        ax.set_ylabel(y_label_name, fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.3)
        return

    corr = data[x].corr(data[y])

    vals = pd.concat([data[x], data[y]]).replace([np.inf, -np.inf], np.nan).dropna()

    low = vals.quantile(0.01)
    high = vals.quantile(0.99)

    low = min(low, 0)
    high = max(high, 0)

    if low == high:
        low -= 1
        high += 1

    data_plot = data.copy()
    data_plot[x] = data_plot[x].clip(lower=low, upper=high)
    data_plot[y] = data_plot[y].clip(lower=low, upper=high)

    ax.scatter(
        data_plot[x],
        data_plot[y],
        alpha=0.65,
        s=35
    )

    ax.plot(
        [low, high],
        [low, high],
        linestyle="--",
        linewidth=1.3,
        color="black"
    )

    ax.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.axvline(0, color="grey", linestyle=":", linewidth=0.8)

    ax.set_xlim(low, high)
    ax.set_ylim(low, high)

    ax.set_xlabel(f"Gap-to-Target ({ndc_label}, production-based)", fontsize=10)
    ax.set_ylabel(y_label_name, fontsize=10)

    ax.set_title(
    f"{title}\n$r$ = {corr:.2f}",
    fontsize=11,
    pad=12
    )

    ax.grid(True, linestyle="--", alpha=0.3)


def make_robustness_figure(ndc="n2"):
    """
    Create a 4-panel robustness figure for either NDC1 or NDC2.
    """

    ndc_label = "First NDC" if ndc == "n1" else "Second NDC"

    baseline = f"gap_{ndc}_edgar_pct"
    consumption = f"gap_{ndc}_cons_pct"
    bau_s2 = f"gappct_{ndc}_r85s2m"
    bau_s3 = f"gappct_{ndc}_r85s3m"
    bau_s5 = f"gappct_{ndc}_r85s5m"

    specs = [
        ("(a) Baseline vs consumption-based", consumption),
        ("(b) Baseline vs BAU SSP2 mean", bau_s2),
        ("(c) Baseline vs BAU SSP3 mean", bau_s3),
        ("(d) Baseline vs BAU SSP5 mean", bau_s5),
    ]

    fig, axes = plt.subplots(
        2,
        2,
        figsize=(12, 9),
        constrained_layout=True
    )

    fig.suptitle(
        f"Robustness of the Gap-to-Target Indicator: {ndc_label}",
        fontsize=15,
        y=1.03
    )

    for ax, (title, alt_var) in zip(axes.flatten(), specs):

        if baseline not in df_paris.columns:
            ax.text(
                0.5, 0.5,
                f"Missing baseline variable:\n{baseline}",
                ha="center",
                va="center",
                fontsize=10
            )
            ax.set_title(title, fontsize=11, pad=12)
            ax.axis("off")
            continue

        if alt_var not in df_paris.columns:
            ax.text(
                0.5, 0.5,
                f"Missing alternative variable:\n{alt_var}",
                ha="center",
                va="center",
                fontsize=10
            )
            ax.set_title(title, fontsize=11, pad=12)
            ax.axis("off")
            continue

        if "cons" in alt_var:
            y_label = f"Gap-to-Target ({ndc_label}, consumption-based)"
        elif "r85s2" in alt_var:
            y_label = f"Gap-to-Target ({ndc_label}, BAU SSP2 mean)"
        elif "r85s3" in alt_var:
            y_label = f"Gap-to-Target ({ndc_label}, BAU SSP3 mean)"
        elif "r85s5" in alt_var:
            y_label = f"Gap-to-Target ({ndc_label}, BAU SSP5 mean)"
        else:
            y_label = f"Gap-to-Target ({ndc_label}, alternative specification)"

        tmp = country_mean_pair(df_paris, baseline, alt_var)

        print(ndc_label, "|", alt_var, "| countries:", len(tmp))

        plot_robustness_panel(
            ax=ax,
            data=tmp,
            x=baseline,
            y=alt_var,
            title=title,
            ndc_label=ndc_label,
            y_label_name=y_label
        )

    filename = f"Robustness_Gap_{ndc.upper()}_four_panels.png"

    plt.savefig(
        graph_dir / filename,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    print("Figure saved:", graph_dir / filename)


# ======================================================
# PRODUCE FIGURES
# ======================================================

make_robustness_figure("n1")
make_robustness_figure("n2")



from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


working_dir = Path(r"C:\Users\richm\Desktop\NDC DATA NEW\NDC Completed\Final Data")
input_file = working_dir / "Data_analysis_gap_only.dta"
graph_dir = working_dir / "Graphs"
graph_dir.mkdir(exist_ok=True)

df = pd.read_stata(input_file)

country_col = "iso3"
year_col = "year"

df_paris = df[df[year_col].between(2015, 2024)].copy()


def country_mean_pair(data, x, y):
    return (
        data[[country_col, x, y]]
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=[x, y])
        .groupby(country_col, as_index=False)[[x, y]]
        .mean()
    )


def plot_panel(ax, data, x, y, title, x_label, y_label):
    if data.empty or data[x].nunique() < 2 or data[y].nunique() < 2:
        ax.text(0.5, 0.5, "No sufficient data", ha="center", va="center")
        ax.set_title(title, fontsize=10)
        return

    corr = data[x].corr(data[y])

    vals = pd.concat([data[x], data[y]]).replace([np.inf, -np.inf], np.nan).dropna()
    low = min(vals.quantile(0.01), 0)
    high = max(vals.quantile(0.99), 0)

    data_plot = data.copy()
    data_plot[x] = data_plot[x].clip(lower=low, upper=high)
    data_plot[y] = data_plot[y].clip(lower=low, upper=high)

    ax.scatter(data_plot[x], data_plot[y], alpha=0.65, s=30)

    ax.plot([low, high], [low, high], linestyle="--", linewidth=1.2, color="black")
    ax.axhline(0, color="grey", linestyle=":", linewidth=0.8)
    ax.axvline(0, color="grey", linestyle=":", linewidth=0.8)

    ax.set_xlim(low, high)
    ax.set_ylim(low, high)

    ax.set_title(f"{title}\n$r$ = {corr:.2f}", fontsize=10, pad=10)
    ax.set_xlabel(x_label, fontsize=9)
    ax.set_ylabel(y_label, fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.3)


def make_bau_model_figure(ndc="n2", ssp="s2"):
    """
    ndc = 'n1' or 'n2'
    ssp = 's2', 's3', or 's5'
    """

    ndc_label = "First NDC" if ndc == "n1" else "Second NDC"
    ssp_label = {"s2": "SSP2", "s3": "SSP3", "s5": "SSP5"}[ssp]

    baseline = f"gap_{ndc}_edgar_pct"

    specs = [
        ("IIASA", f"gappct_{ndc}_r85{ssp}i"),
        ("OECD",  f"gappct_{ndc}_r85{ssp}o"),
        ("PIK",   f"gappct_{ndc}_r85{ssp}p"),
        ("Mean",  f"gappct_{ndc}_r85{ssp}m"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)

    fig.suptitle(
        f"Robustness to BAU Model Choice: {ndc_label}, RCP8.5 {ssp_label}",
        fontsize=15,
        y=1.03
    )

    for ax, (model_label, alt_var) in zip(axes.flatten(), specs):

        if baseline not in df_paris.columns or alt_var not in df_paris.columns:
            ax.text(
                0.5, 0.5,
                f"Missing variable:\n{alt_var}",
                ha="center",
                va="center",
                fontsize=10
            )
            ax.axis("off")
            continue

        tmp = country_mean_pair(df_paris, baseline, alt_var)

        plot_panel(
            ax=ax,
            data=tmp,
            x=baseline,
            y=alt_var,
            title=f"Baseline vs {ssp_label} {model_label}",
            x_label=f"Gap-to-Target ({ndc_label}, production-based)",
            y_label=f"Gap-to-Target ({ndc_label}, BAU {ssp_label} {model_label})"
        )

    filename = f"Robustness_BAU_Model_{ndc.upper()}_{ssp_label}.png"
    plt.savefig(graph_dir / filename, dpi=300, bbox_inches="tight")
    plt.show()

    print("Figure saved:", graph_dir / filename)


# ======================================================
# PRODUCE FIGURES
# ======================================================

for ndc in ["n1", "n2"]:
    for ssp in ["s2", "s3", "s5"]:
        make_bau_model_figure(ndc=ndc, ssp=ssp)
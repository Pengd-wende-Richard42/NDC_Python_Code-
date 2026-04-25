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
working_dir = Path(r"C:\Users\richm\Desktop\NDC DATA NEW\NDC Completed\Final Data")
input_file = working_dir / "Data_analysis_gap_only.dta"
graph_dir = working_dir / "Graphs_Appendix_Codebook"
graph_dir.mkdir(exist_ok=True)

# =========================================================
# 1. LOAD DATA
# =========================================================
meta = pd.read_excel(working_dir / "ICR.xlsx")
df = pd.read_stata(input_file)

df["iso3"] = df["iso3"].astype(str).str.strip().str.upper()
meta["iso3"] = meta["iso3"].astype(str).str.strip().str.upper()
meta = meta.drop_duplicates(subset=["iso3"], keep="first").copy()

df = df.merge(meta, on="iso3", how="left")

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

df_kyoto = df[df[year_col] <= KYOTO_END].copy()
df_paris = df[df[year_col] >= PARIS_START].copy()

income_order = [
    "Low income",
    "Lower middle income",
    "Upper middle income",
    "High income"
]

# =========================================================
# 3. HELPER FUNCTIONS
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

def standard_ylim(vals, ref0=True, ref1=False, margin=0.15, min_span=2):
    vals = np.asarray(vals, dtype=float)
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return (-1, 1)

    ymin = vals.min()
    ymax = vals.max()

    if ref0:
        ymin = min(ymin, 0)
        ymax = max(ymax, 0)

    if ref1:
        ymin = min(ymin, 1)
        ymax = max(ymax, 1)

    ymin *= (1 + margin) if ymin < 0 else (1 - margin)
    ymax *= (1 + margin) if ymax > 0 else (1 - margin)

    if (ymax - ymin) < min_span:
        ymax = ymin + min_span

    return ymin, ymax

def save_show(fig, filepath):
    fig.tight_layout()
    fig.savefig(filepath, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close(fig)

def available_vars(var_dict):
    return {k: v for k, v in var_dict.items() if v in df.columns}

def plot_distribution(df_use, var_dict, title, filename, xline=0, xlabel="Value", ncols=2):
    var_dict = available_vars(var_dict)
    if len(var_dict) == 0:
        print(f"[SKIP] No available vars for {filename}")
        return

    n = len(var_dict)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(7*ncols, 4*nrows), squeeze=False, sharey=True)
    axes = axes.flatten()

    for ax, (label, var) in zip(axes, var_dict.items()):
        series = df_use.groupby(country_col)[var].mean().dropna()
        if len(series) > 0:
            q01 = series.quantile(0.01)
            q99 = series.quantile(0.99)
            series = series.clip(lower=q01, upper=q99)
            ax.hist(series, bins=20, edgecolor="white")
            if xline is not None:
                ax.axvline(xline, color="black", linestyle="--", linewidth=1)

        ax.set_title(label, fontsize=11)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

    for j in range(len(var_dict), len(axes)):
        axes[j].axis("off")

    axes[0].set_ylabel("Number of countries", fontsize=10)
    fig.suptitle(title, fontsize=14, y=1.02)
    save_show(fig, graph_dir / filename)

def plot_group_bars(df_use, group_col, var_dict, title, ylabel, filename,
                    order=None, xline0=True, xline1=False, rotation=15):
    var_dict = available_vars(var_dict)
    if len(var_dict) == 0 or group_col not in df.columns:
        print(f"[SKIP] No available vars or missing group col for {filename}")
        return

    group_meta = (
        df[[country_col, group_col]]
        .dropna(subset=[group_col])
        .drop_duplicates(subset=[country_col])
    )

    agg = df_use.groupby(country_col)[list(var_dict.values())].mean().reset_index()
    merged = agg.merge(group_meta, on=country_col, how="left").dropna(subset=[group_col])

    plot_cols = []
    for var in var_dict.values():
        plot_var = var + "_plot"
        merged[plot_var] = winsorize_series(merged[var], 0.05, 0.95)
        plot_cols.append(plot_var)

    grouped = merged.groupby(group_col)[plot_cols].mean()
    if order is not None:
        grouped = grouped.reindex(order)
    grouped = grouped.dropna(how="all")

    if grouped.empty:
        print(f"[SKIP] Empty grouped data for {filename}")
        return

    x = np.arange(len(grouped))
    width = 0.8 / len(plot_cols)

    fig, ax = plt.subplots(figsize=(max(10, 1.4*len(grouped)), 5.5))

    for i, ((label, var), plot_var) in enumerate(zip(var_dict.items(), plot_cols)):
        ax.bar(
            x - 0.4 + width/2 + i*width,
            grouped[plot_var],
            width=width,
            label=label
        )

    if xline0:
        ax.axhline(0, color="black", linestyle="--", linewidth=1)
    if xline1:
        ax.axhline(1, color="grey", linestyle=":", linewidth=1)

    ax.set_xticks(x)
    ax.set_xticklabels(grouped.index, rotation=rotation, ha="right" if rotation > 15 else "center")
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(fontsize=9, ncol=2 if len(plot_cols) > 3 else 1)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    ymin, ymax = standard_ylim(grouped.to_numpy().ravel(), ref0=xline0, ref1=xline1)
    ax.set_ylim(ymin, ymax)

    save_show(fig, graph_dir / filename)

def plot_top_bottom(df_country, var, title, filename, xlabel, winsorize_top=True, xline0=True, xline1=False):
    if var not in df_country.columns:
        print(f"[SKIP] Missing {var} for {filename}")
        return

    sub = df_country[[country_col, var]].dropna().copy()
    if sub.empty:
        print(f"[SKIP] Empty data for {filename}")
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

    top10[var + "_plot"].plot.barh(ax=axes[0], edgecolor="black")
    axes[0].set_title(f"Top 10 Countries – {title}", fontsize=12)
    axes[0].set_xlabel(xlabel, fontsize=11)
    axes[0].set_ylabel("Countries", fontsize=11)
    axes[0].grid(axis="x", linestyle="--", alpha=0.4)
    if xline0:
        axes[0].axvline(0, color="black", linestyle="--", linewidth=1)
    if xline1:
        axes[0].axvline(1, color="grey", linestyle=":", linewidth=1)

    bottom10[var + "_plot"].plot.barh(ax=axes[1], edgecolor="black")
    axes[1].set_title(f"Bottom 10 Countries – {title}", fontsize=12)
    axes[1].set_xlabel(xlabel, fontsize=11)
    axes[1].set_ylabel("Countries", fontsize=11)
    axes[1].grid(axis="x", linestyle="--", alpha=0.4)
    if xline0:
        axes[1].axvline(0, color="black", linestyle="--", linewidth=1)
    if xline1:
        axes[1].axvline(1, color="grey", linestyle=":", linewidth=1)

    save_show(fig, graph_dir / filename)

def plot_top_bottom_feasibility(df_country, var, title, filename, xlabel="Feasibility ratio",
                                top_n=10, bottom_n=10, trim_quantile=0.90):
    if var not in df_country.columns:
        print(f"[SKIP] Missing {var} for {filename}")
        return

    sub = df_country[[country_col, var]].dropna().copy()
    if sub.empty:
        print(f"[SKIP] Empty data for {filename}")
        return

    top10 = sub.nlargest(top_n, var).copy()
    bottom10 = sub.nsmallest(bottom_n, var).copy()

    top_cap = top10[var].quantile(trim_quantile)
    bottom_cap = bottom10[var].quantile(1 - trim_quantile)

    top10[var + "_plot"] = top10[var].clip(upper=top_cap)
    bottom10[var + "_plot"] = bottom10[var].clip(lower=bottom_cap)

    top10 = top10.sort_values(var + "_plot")
    bottom10 = bottom10.sort_values(var + "_plot")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # TOP
    axes[0].barh(top10[country_col], top10[var + "_plot"], edgecolor="black")
    axes[0].set_title(f"Top 10 Countries – {title}", fontsize=12)
    axes[0].set_xlabel(xlabel, fontsize=11)
    axes[0].set_ylabel("Countries", fontsize=11)
    axes[0].axvline(1, color="black", linestyle="--", linewidth=1)
    axes[0].axvline(0, color="grey", linestyle=":", linewidth=1)
    axes[0].grid(axis="x", linestyle="--", alpha=0.4)

    xlim_left_top = min(0, top10[var + "_plot"].min()) * 1.1
    xlim_right_top = max(top10[var + "_plot"].max(), 1) * 1.1
    axes[0].set_xlim(xlim_left_top, xlim_right_top)

    for i, (_, row) in enumerate(top10.iterrows()):
        shown = row[var + "_plot"]
        truev = row[var]
        axes[0].text(shown + (xlim_right_top - xlim_left_top)*0.015, i, f"{truev:.1f}", va="center", fontsize=8)
        if truev > shown:
            axes[0].text(shown - (xlim_right_top - xlim_left_top)*0.03, i, "▶", va="center", ha="center", fontsize=9)

    # BOTTOM
    axes[1].barh(bottom10[country_col], bottom10[var + "_plot"], edgecolor="black")
    axes[1].set_title(f"Bottom 10 Countries – {title}", fontsize=12)
    axes[1].set_xlabel(xlabel, fontsize=11)
    axes[1].set_ylabel("Countries", fontsize=11)
    axes[1].axvline(1, color="black", linestyle="--", linewidth=1)
    axes[1].axvline(0, color="grey", linestyle=":", linewidth=1)
    axes[1].grid(axis="x", linestyle="--", alpha=0.4)

    xlim_left_bot = min(bottom10[var + "_plot"].min(), 0) * 1.1
    xlim_right_bot = max(1, bottom10[var + "_plot"].max()) * 1.1
    axes[1].set_xlim(xlim_left_bot, xlim_right_bot)

    for i, (_, row) in enumerate(bottom10.iterrows()):
        shown = row[var + "_plot"]
        truev = row[var]
        axes[1].text(shown + (xlim_right_bot - xlim_left_bot)*0.015, i, f"{truev:.1f}", va="center", fontsize=8)
        if truev < shown:
            axes[1].text(shown + (xlim_right_bot - xlim_left_bot)*0.03, i, "◀", va="center", ha="center", fontsize=9)

    save_show(fig, graph_dir / filename)

def plot_world_maps(map_specs, years_map, filename_prefix):
    world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    world = world[world["name"] != "Antarctica"].copy()

    all_vals = []
    for label, (var, data_use) in map_specs.items():
        if var in data_use.columns:
            year_sel = years_map.get(label, 2023)
            tmp = data_use.loc[data_use[year_col] == year_sel, [country_col, var]].dropna()
            tmp = tmp.groupby(country_col, as_index=False)[var].mean()
            if not tmp.empty:
                all_vals.append(tmp[var])

    if len(all_vals) == 0:
        print(f"[SKIP] No map data for {filename_prefix}")
        return

    all_vals_concat = pd.concat(all_vals)
    vmin = min(all_vals_concat.quantile(0.05), 0)
    vmax = max(all_vals_concat.quantile(0.95), 0)
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    for label, (var, data_use) in map_specs.items():
        if var not in data_use.columns:
            continue

        year_sel = years_map.get(label, 2023)
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
            missing_kwds={"color": "lightgrey", "edgecolor": "white", "hatch": "///"},
            legend_kwds={"label": "Relative gap-to-target", "shrink": 0.7}
        )

        missing_patch = mpatches.Patch(facecolor="lightgrey", hatch="///", label="No data")
        ax.legend(handles=[missing_patch], loc="lower left", fontsize=10, frameon=True)
        ax.set_title(f"{label} ({year_sel})", fontsize=14)
        ax.axis("off")

        save_show(fig, graph_dir / f"{filename_prefix}_{label.replace(' ', '_')}_{year_sel}.png")

# =========================================================
# 4. VARIABLE FAMILIES
# =========================================================

# -------- BASELINE CONDITIONAL / UNCONDITIONAL GAPS --------
gap_rel_baseline_conditional = {
    "First NDC Unconditional": "gap_n1_uncond_edgar_pct",
    "Second NDC Unconditional": "gap_n2_uncond_edgar_pct",
    "Main Unconditional": "gap_main_uncond_edgar_pct",
    "First NDC Conditional": "gap_n1_cond_edgar_pct",
    "Second NDC Conditional": "gap_n2_cond_edgar_pct",
    "Main Conditional": "gap_main_cond_edgar_pct",
}

# -------- ROBUSTNESS GAPS --------
gap_rel_robustness = {
    "First NDC Consumption-based": "gap_n1_cons_pct",
    "Second NDC Consumption-based": "gap_n2_cons_pct",
    "Main Consumption-based": "gap_main_cons_pct",
    "Second NDC BAU SSP2": "gap_n2_bau_ssp2_edgar_pct",
    "Second NDC BAU SSP3": "gap_n2_bau_ssp3_edgar_pct",
    "Second NDC BAU SSP5": "gap_n2_bau_ssp5_edgar_pct",
}

# -------- FEASIBILITY DYNAMIC: CONDITIONAL / UNCONDITIONAL --------
feas_dyn_conditional = {
    "First NDC Unconditional": "feas_n1_uncond_edgar",
    "Second NDC Unconditional": "feas_n2_uncond_edgar",
    "Main Unconditional": "feas_main_uncond_edgar",
    "First NDC Conditional": "feas_n1_cond_edgar",
    "Second NDC Conditional": "feas_n2_cond_edgar",
    "Main Conditional": "feas_main_cond_edgar",
}

# -------- FEASIBILITY ABSOLUTE: CONDITIONAL / UNCONDITIONAL --------
# ces colonnes ne sont tracées que si elles existent réellement dans la base
feas_abs_conditional = {
    "First NDC Unconditional": "feasabs_n1_uncond_edgar",
    "Second NDC Unconditional": "feasabs_n2_uncond_edgar",
    "Main Unconditional": "feasabs_main_uncond_edgar",
    "First NDC Conditional": "feasabs_n1_cond_edgar",
    "Second NDC Conditional": "feasabs_n2_cond_edgar",
    "Main Conditional": "feasabs_main_cond_edgar",
}

# -------- FEASIBILITY ROBUSTNESS --------
feas_dyn_robustness = {
    "First NDC Consumption-based": "feas_n1_cons",
    "Second NDC Consumption-based": "feas_n2_cons",
    "Main Consumption-based": "feas_main_cons",
}

feas_abs_robustness = {
    "First NDC Consumption-based": "feasabs_n1_cons",
    "Second NDC Consumption-based": "feasabs_n2_cons",
    "Main Consumption-based": "feasabs_main_cons",
}

# =========================================================
# 5. BASELINE GAPS: CONDITIONAL / UNCONDITIONAL
# =========================================================

# distributions
plot_distribution(
    df_paris,
    gap_rel_baseline_conditional,
    "Distribution of Conditional and Unconditional Baseline Gaps",
    "Distribution_Baseline_Gaps_Conditional_Unconditional.png",
    xline=0,
    xlabel="Relative gap-to-target"
)

# income
plot_group_bars(
    df_paris,
    income_col,
    gap_rel_baseline_conditional,
    "Conditional and Unconditional Baseline Gaps Across Income Groups",
    "Average relative gap-to-target",
    "Baseline_Gaps_Conditional_Unconditional_by_income.png",
    order=income_order,
    xline0=True,
    xline1=False,
    rotation=15
)

# region
plot_group_bars(
    df_paris,
    region_col,
    gap_rel_baseline_conditional,
    "Conditional and Unconditional Baseline Gaps Across Regions",
    "Average relative gap-to-target",
    "Baseline_Gaps_Conditional_Unconditional_by_region.png",
    order=None,
    xline0=True,
    xline1=False,
    rotation=20
)

# top/bottom par variable
for label, var in available_vars(gap_rel_baseline_conditional).items():
    df_country_tmp = df_paris.groupby(country_col)[[var]].mean().reset_index()
    safe = label.replace(" ", "_").replace("/", "_")
    plot_top_bottom(
        df_country_tmp,
        var,
        label,
        f"Top_Bottom_{safe}_Baseline_Gap.png",
        xlabel="Relative gap-to-target",
        winsorize_top=True,
        xline0=True,
        xline1=False
    )

# maps seulement pour N1/N2 cond/uncond si souhaité
map_specs_baseline_conditional = {
    "First NDC Unconditional": ("gap_n1_uncond_edgar_pct", df_paris),
    "Second NDC Unconditional": ("gap_n2_uncond_edgar_pct", df_paris),
    "First NDC Conditional": ("gap_n1_cond_edgar_pct", df_paris),
    "Second NDC Conditional": ("gap_n2_cond_edgar_pct", df_paris),
}
years_map_conditional = {
    "First NDC Unconditional": 2023,
    "Second NDC Unconditional": 2023,
    "First NDC Conditional": 2023,
    "Second NDC Conditional": 2023,
}
plot_world_maps(map_specs_baseline_conditional, years_map_conditional, "Map_Baseline_Conditional_Unconditional")

# =========================================================
# 6. ROBUSTNESS GAPS
# =========================================================

plot_distribution(
    df_paris,
    gap_rel_robustness,
    "Distribution of Robustness Gap Measures",
    "Distribution_Robustness_Gaps.png",
    xline=0,
    xlabel="Relative gap-to-target"
)

plot_group_bars(
    df_paris,
    income_col,
    gap_rel_robustness,
    "Robustness Gap Measures Across Income Groups",
    "Average relative gap-to-target",
    "Robustness_Gaps_by_income.png",
    order=income_order,
    xline0=True,
    xline1=False,
    rotation=15
)

plot_group_bars(
    df_paris,
    region_col,
    gap_rel_robustness,
    "Robustness Gap Measures Across Regions",
    "Average relative gap-to-target",
    "Robustness_Gaps_by_region.png",
    order=None,
    xline0=True,
    xline1=False,
    rotation=20
)

for label, var in available_vars(gap_rel_robustness).items():
    df_country_tmp = df_paris.groupby(country_col)[[var]].mean().reset_index()
    safe = label.replace(" ", "_").replace("/", "_")
    plot_top_bottom(
        df_country_tmp,
        var,
        label,
        f"Top_Bottom_{safe}_Robustness_Gap.png",
        xlabel="Relative gap-to-target",
        winsorize_top=True,
        xline0=True,
        xline1=False
    )

map_specs_robustness = {
    "First NDC Consumption-based": ("gap_n1_cons_pct", df_paris),
    "Second NDC Consumption-based": ("gap_n2_cons_pct", df_paris),
    "Second NDC BAU SSP2": ("gap_n2_bau_ssp2_edgar_pct", df_paris),
    "Second NDC BAU SSP3": ("gap_n2_bau_ssp3_edgar_pct", df_paris),
    "Second NDC BAU SSP5": ("gap_n2_bau_ssp5_edgar_pct", df_paris),
}
years_map_rob = {k: 2023 for k in map_specs_robustness.keys()}
plot_world_maps(map_specs_robustness, years_map_rob, "Map_Robustness_Gaps")

# =========================================================
# 7. FEASIBILITY DYNAMIC: CONDITIONAL / UNCONDITIONAL
# =========================================================
plot_distribution(
    df_paris,
    feas_dyn_conditional,
    "Distribution of Dynamic Feasibility (Conditional and Unconditional)",
    "Distribution_Dynamic_Feasibility_Conditional_Unconditional.png",
    xline=1,
    xlabel="Feasibility ratio"
)

plot_group_bars(
    df_paris,
    income_col,
    feas_dyn_conditional,
    "Dynamic Feasibility Across Income Groups (Conditional and Unconditional)",
    "Average feasibility ratio",
    "Dynamic_Feasibility_Conditional_Unconditional_by_income.png",
    order=income_order,
    xline0=True,
    xline1=True,
    rotation=15
)

plot_group_bars(
    df_paris,
    region_col,
    feas_dyn_conditional,
    "Dynamic Feasibility Across Regions (Conditional and Unconditional)",
    "Average feasibility ratio",
    "Dynamic_Feasibility_Conditional_Unconditional_by_region.png",
    order=None,
    xline0=True,
    xline1=True,
    rotation=20
)

for label, var in available_vars(feas_dyn_conditional).items():
    df_country_tmp = df_paris.groupby(country_col)[[var]].mean().reset_index()
    safe = label.replace(" ", "_").replace("/", "_")
    plot_top_bottom_feasibility(
        df_country_tmp,
        var,
        f"{label} Dynamic Feasibility",
        f"Top_Bottom_{safe}_Dynamic_Feasibility.png"
    )

# =========================================================
# 8. FEASIBILITY ABSOLUTE: CONDITIONAL / UNCONDITIONAL
# =========================================================
plot_distribution(
    df_paris,
    feas_abs_conditional,
    "Distribution of Absolute Feasibility (Conditional and Unconditional)",
    "Distribution_Absolute_Feasibility_Conditional_Unconditional.png",
    xline=1,
    xlabel="Feasibility ratio"
)

plot_group_bars(
    df_paris,
    income_col,
    feas_abs_conditional,
    "Absolute Feasibility Across Income Groups (Conditional and Unconditional)",
    "Average feasibility ratio",
    "Absolute_Feasibility_Conditional_Unconditional_by_income.png",
    order=income_order,
    xline0=True,
    xline1=True,
    rotation=15
)

plot_group_bars(
    df_paris,
    region_col,
    feas_abs_conditional,
    "Absolute Feasibility Across Regions (Conditional and Unconditional)",
    "Average feasibility ratio",
    "Absolute_Feasibility_Conditional_Unconditional_by_region.png",
    order=None,
    xline0=True,
    xline1=True,
    rotation=20
)

for label, var in available_vars(feas_abs_conditional).items():
    df_country_tmp = df_paris.groupby(country_col)[[var]].mean().reset_index()
    safe = label.replace(" ", "_").replace("/", "_")
    plot_top_bottom_feasibility(
        df_country_tmp,
        var,
        f"{label} Absolute Feasibility",
        f"Top_Bottom_{safe}_Absolute_Feasibility.png"
    )

# =========================================================
# 9. FEASIBILITY ROBUSTNESS
# =========================================================
plot_distribution(
    df_paris,
    feas_dyn_robustness,
    "Distribution of Dynamic Feasibility Robustness Measures",
    "Distribution_Dynamic_Feasibility_Robustness.png",
    xline=1,
    xlabel="Feasibility ratio"
)

plot_group_bars(
    df_paris,
    income_col,
    feas_dyn_robustness,
    "Dynamic Feasibility Robustness Across Income Groups",
    "Average feasibility ratio",
    "Dynamic_Feasibility_Robustness_by_income.png",
    order=income_order,
    xline0=True,
    xline1=True,
    rotation=15
)

plot_group_bars(
    df_paris,
    region_col,
    feas_dyn_robustness,
    "Dynamic Feasibility Robustness Across Regions",
    "Average feasibility ratio",
    "Dynamic_Feasibility_Robustness_by_region.png",
    order=None,
    xline0=True,
    xline1=True,
    rotation=20
)

for label, var in available_vars(feas_dyn_robustness).items():
    df_country_tmp = df_paris.groupby(country_col)[[var]].mean().reset_index()
    safe = label.replace(" ", "_").replace("/", "_")
    plot_top_bottom_feasibility(
        df_country_tmp,
        var,
        f"{label} Dynamic Feasibility",
        f"Top_Bottom_{safe}_Dynamic_Feasibility_Robustness.png"
    )

plot_distribution(
    df_paris,
    feas_abs_robustness,
    "Distribution of Absolute Feasibility Robustness Measures",
    "Distribution_Absolute_Feasibility_Robustness.png",
    xline=1,
    xlabel="Feasibility ratio"
)

plot_group_bars(
    df_paris,
    income_col,
    feas_abs_robustness,
    "Absolute Feasibility Robustness Across Income Groups",
    "Average feasibility ratio",
    "Absolute_Feasibility_Robustness_by_income.png",
    order=income_order,
    xline0=True,
    xline1=True,
    rotation=15
)

plot_group_bars(
    df_paris,
    region_col,
    feas_abs_robustness,
    "Absolute Feasibility Robustness Across Regions",
    "Average feasibility ratio",
    "Absolute_Feasibility_Robustness_by_region.png",
    order=None,
    xline0=True,
    xline1=True,
    rotation=20
)

for label, var in available_vars(feas_abs_robustness).items():
    df_country_tmp = df_paris.groupby(country_col)[[var]].mean().reset_index()
    safe = label.replace(" ", "_").replace("/", "_")
    plot_top_bottom_feasibility(
        df_country_tmp,
        var,
        f"{label} Absolute Feasibility",
        f"Top_Bottom_{safe}_Absolute_Feasibility_Robustness.png"
    )

print("\nTous les graphiques annexes / codebook ont été générés dans :", graph_dir)
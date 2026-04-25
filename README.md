# Project Structure

```text
├── climate_watch_ndc.py
├── Gap_to_target_Builder.py
├── Gap_to_target_Analyser.py
├── Robutness_Analyser.py
├── README.md
```

## Files Description

### `climate_watch_ndc.py`

Main data extraction and preprocessing pipeline for Nationally Determined Contributions (NDCs) from the Climate Watch API.

Main functionalities:

* Automated API requests with retry management
* Cleaning and normalization of NDC textual data
* Extraction of mitigation targets
* Parsing of target years, conditionality, and target formats
* Identification of:

  * unconditional targets
  * conditional targets
  * intensity targets
  * BAU targets
  * peaking targets
* Construction of structured NDC datasets
* Export to Excel-compatible formats

This script is the core ETL pipeline of the project.

---

### `Gap_to_target_Builder.py`

Construction of the harmonized climate policy panel dataset.

Main functionalities:

* Cleaning and standardization of:

  * NDC datasets
  * EDGAR emissions data
  * OWID climate data
  * NGFS scenario projections
* ISO3 harmonization
* Construction of:

  * Kyoto targets
  * NDC targets
  * emissions trajectories
  * feasibility indicators
* Panel dataset generation (1990–2050)
* Export to Stata `.dta` format

Integrated data sources:

* Climate Watch
* EDGAR
* Our World in Data
* NGFS scenarios

---

### `Gap_to_target_Analyser.py`

Main empirical analysis and visualization script.

Main functionalities:

* Computation of:

  * absolute gap-to-target indicators
  * relative gap-to-target indicators
  * feasibility metrics
* Global dynamic analysis of climate commitment alignment
* Income-group comparisons
* Regional comparisons
* Distribution analysis
* Top/bottom country performance analysis
* Automated graph generation

Outputs:

* figures
* Comparative charts
* Histograms
* Regional and income-group visualizations

---

### `Robutness_Analyser.py`

Robustness and supplementary empirical analysis script.

Main functionalities:

* Robustness checks
* Alternative specifications
* Appendix figures
* Sensitivity analysis
* Additional comparative visualizations
* Extended descriptive statistics

Used for:

* supplementary materials
* appendices
* validation exercises

---

## Research Scope

This repository supports empirical research on:

* Climate policy
* Nationally Determined Contributions (NDCs)
* Emissions gap analysis
* Climate finance
* International environmental agreements
* Kyoto Protocol and Paris Agreement alignment
* Climate target feasibility

---

## Main Technologies

* Python
* Pandas
* NumPy
* Matplotlib
* GeoPandas
* Requests
* OpenPyXL

---

## Outputs

The project generates:

* Harmonized climate datasets
* Emissions gap indicators
* Comparative visualizations
* Feasibility metrics
* Policy analysis figures
* Stata panel databases on 144 countries from 1997 to 2024


```
```

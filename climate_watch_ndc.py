

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DEFAULT_API_URL = "https://www.climatewatchdata.org/api/v1/data/ndc_content"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ClimateWatchNDCETL/4.0)",
    "Accept": "application/json,text/plain,*/*",
}

REQUEST_TIMEOUT = 90
DEFAULT_VERIFY_SSL = False

USEFUL_INDICATORS = {
    "indc_summary",
    "ghg_target",
    "ghg_target_type",
    "type_cible_ges",
    "target_year",
    "année_cible",
    "timeframe",
    "période",
    "mitigation_contribution_type",
    "conditionnalité",
    "conditionality",
    "submission_date",
    "submission_type",
    "submission",
    "adaptation",
    "non_ghg_target",
}

KEY_ALIASES = {
    "id": ["id"],
    "source": ["source"],
    "iso_code3": ["iso_code3", "code_iso_3"],
    "country": ["country", "pays"],
    "global_category": ["global_category", "catégorie_globale"],
    "overview_category": ["overview_category", "catégorie_aperçu", "catégorie_vue_d'ensemble"],
    "sector": ["sector", "secteur"],
    "subsector": ["subsector", "sous-secteur"],
    "indicator_id": ["indicator_id", "id_indicateur", "indicator_slug"],
    "indicator_name": ["indicator_name", "nom_indicateur"],
    "value": ["value", "valeur"],
}

PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
RANGE_PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:–|-|to|à)\s*(\d+(?:[.,]\d+)?)\s*%", re.I)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
BAU_RE = re.compile(r"\b(BAU|business as usual|baseline scenario|scénario de statu quo|scénario de référence)\b", re.I)
CONDITIONAL_RE = re.compile(r"\b(conditionnel|conditional)\b", re.I)
UNCONDITIONAL_RE = re.compile(r"\b(inconditionnel|unconditional)\b", re.I)
INTENSITY_RE = re.compile(r"\b(intensity|intensité|per GDP|per unit of GDP|par unité de PIB|par PIB|per capita|par habitant)\b", re.I)
ABSOLUTE_RE = re.compile(r"\b(MtCO2e|Mt CO2e|GtCO2e|Gt CO2e|tonnes|tCO2e|absolute|niveau absolu)\b", re.I)
PEAK_RE = re.compile(r"\b(peak|peaking|pic)\b", re.I)
POLICY_RE = re.compile(r"\b(policy|policies|action|actions|measure|mesure|mesures)\b", re.I)
MITIGATION_RE = re.compile(r"\b(mitigation|atténuation)\b", re.I)
ADAPTATION_RE = re.compile(r"\b(adaptation)\b", re.I)


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

def setup_logging(outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=outdir / "ndc_errors.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# ---------------------------------------------------------------------
# Session HTTP robuste
# ---------------------------------------------------------------------

def build_session(verify_ssl: bool = DEFAULT_VERIFY_SSL) -> requests.Session:
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    session.verify = verify_ssl
    return session


# ---------------------------------------------------------------------
# Helpers généraux
# ---------------------------------------------------------------------

def clean_html_text(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&ldquo;", '"').replace("&rdquo;", '"').replace("&nbsp;", " ")
    s = s.replace("\\u003cp\\u003e", " ").replace("\\u003c/p\\u003e", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_excel_illegal_chars(x: Any) -> Any:
    if x is None:
        return None
    s = str(x)
    s = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", s)
    return s


def sanitize_dataframe_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    for col in df2.columns:
        if df2[col].dtype == object:
            df2[col] = df2[col].apply(clean_excel_illegal_chars)
    return df2


def parse_date_mixed(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    try:
        from dateutil import parser
        return parser.parse(s, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return None


def safe_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    m = re.search(r"\b((?:19|20)\d{2})\b", str(x))
    return int(m.group(1)) if m else None


def first_nonempty(values: List[Any]) -> Optional[str]:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def choose_best(values: List[Any]) -> Optional[str]:
    cleaned = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            cleaned.append(s)
    if not cleaned:
        return None
    return sorted(cleaned, key=lambda x: (len(x), x), reverse=True)[0]


def choose_best_target_text(values: List[Any]) -> Optional[str]:
    """
    Pour la cible GHG, on préfère un texte plus direct et moins contextuel.
    """
    cleaned = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not s:
            continue

        low = s.lower()
        bad_markers = [
            "previous ndc",
            "version précédente",
            "first ndc",
            "updated first ndc",
            "adaptation component",
            "includes an adaptation component",
            "long-term",
            "lt-leds",
        ]
        penalty = sum(marker in low for marker in bad_markers)
        cleaned.append((penalty, len(s), s))

    if not cleaned:
        return None

    cleaned.sort(key=lambda x: (x[0], x[1]))
    return cleaned[0][2]


def coalesce(d: Dict[str, Any], canonical_key: str) -> Any:
    for k in KEY_ALIASES.get(canonical_key, []):
        if k in d:
            return d.get(k)
    return None


def normalize_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for canon in KEY_ALIASES:
        out[canon] = coalesce(rec, canon)
    return out


# ---------------------------------------------------------------------
# Parsing texte NDC
# ---------------------------------------------------------------------

def extract_percent_values(text: str) -> List[float]:
    if not text:
        return []
    vals = []
    for m in PERCENT_RE.finditer(text):
        try:
            vals.append(float(m.group(1).replace(",", ".")))
        except ValueError:
            continue
    return vals


def extract_percent_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    if not text:
        return None, None
    m = RANGE_PERCENT_RE.search(text)
    if not m:
        return None, None
    a = float(m.group(1).replace(",", "."))
    b = float(m.group(2).replace(",", "."))
    return min(a, b), max(a, b)


def infer_target_format(text: str) -> Optional[str]:
    if not text:
        return None
    if INTENSITY_RE.search(text):
        return "Intensity"
    if PEAK_RE.search(text):
        return "Peaking"
    if POLICY_RE.search(text) and not PERCENT_RE.search(text):
        return "Policy"
    if ABSOLUTE_RE.search(text) and not PERCENT_RE.search(text):
        return "Absolute"
    if PERCENT_RE.search(text):
        return "Percent"
    return None


def infer_target_reference(text: str) -> Optional[str]:
    if not text:
        return None
    if BAU_RE.search(text):
        return "BAU"
    years = YEAR_RE.findall(text)
    if years:
        return "Base Year"
    if INTENSITY_RE.search(text):
        return "Intensity baseline"
    return None


def split_conditional_unconditional(text: str) -> Tuple[Optional[float], Optional[float]]:
    if not text:
        return None, None

    pattern_pairs = [
        re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%[^.%]{0,120}?(unconditional|inconditionnel)[^.%]{0,180}?"
            r"(\d+(?:[.,]\d+)?)\s*%[^.%]{0,120}?(conditional|conditionnel)",
            re.I,
        ),
        re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%[^.%]{0,120}?(conditional|conditionnel)[^.%]{0,180}?"
            r"(\d+(?:[.,]\d+)?)\s*%[^.%]{0,120}?(unconditional|inconditionnel)",
            re.I,
        ),
    ]

    for pat in pattern_pairs:
        m = pat.search(text)
        if m:
            a = float(m.group(1).replace(",", "."))
            b = float(m.group(3).replace(",", "."))
            labels = [m.group(2).lower(), m.group(4).lower()]
            if "unconditional" in labels[0] or "inconditionnel" in labels[0]:
                return b, a
            return a, b

    values = extract_percent_values(text)
    txt = text.lower()

    if len(values) == 1:
        if CONDITIONAL_RE.search(txt) and not UNCONDITIONAL_RE.search(txt):
            return values[0], None
        if UNCONDITIONAL_RE.search(txt) and not CONDITIONAL_RE.search(txt):
            return None, values[0]

    return None, None


def ndc_version_from_submission_type(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().lower()
    if "first" in s or "premier" in s or "première" in s:
        return "First NDC"
    if "second" in s or "deux" in s:
        return "Second NDC"
    if "third" in s or "troisième" in s or "3.0" in s:
        return "Third NDC"
    if "updated" in s or "mise à jour" in s or "update" in s:
        return "Updated NDC"
    if "indc" in s:
        return "INDC"
    return None


def extract_ndc_version_from_text(*texts: Any) -> Optional[str]:
    blob = " ".join([str(x) for x in texts if x is not None]).lower()
    if "indc" in blob or "intended nationally determined contribution" in blob:
        return "INDC"
    if "ndc 3.0" in blob or "third ndc" in blob or "troisième" in blob:
        return "Third NDC"
    if "second ndc" in blob or "2.0" in blob or "deuxième" in blob:
        return "Second NDC"
    if "updated ndc" in blob or "updated first ndc" in blob or "revised first ndc" in blob:
        return "Updated NDC"
    if "first ndc" in blob or "premier ndc" in blob or "première ndc" in blob:
        return "First NDC"
    return None


def classify_scope(text: str) -> str:
    if not text:
        return "Unknown"
    has_mit = bool(MITIGATION_RE.search(text))
    has_adp = bool(ADAPTATION_RE.search(text))
    if has_mit and not has_adp:
        return "Mitigation"
    if has_adp and not has_mit:
        return "Adaptation"
    if has_mit and has_adp:
        return "Mixed"
    return "Unknown"


def harmonize_ndc_stage(submission_type: str = "", summary: str = "", ghg_target: str = "") -> str:
    text = " ".join([
        str(submission_type or ""),
        str(summary or ""),
        str(ghg_target or "")
    ]).lower()

    if "indc" in text or "intended nationally determined contribution" in text:
        return "INDC"

    if "third ndc" in text or "ndc 3.0" in text or "troisième" in text:
        return "Third NDC"

    if (
        "second ndc" in text
        or "updated ndc" in text
        or "updated first ndc" in text
        or "revised first ndc" in text
        or "ndc 2.0" in text
    ):
        return "Updated/Second NDC"

    if "first ndc" in text or "première ndc" in text or "premier ndc" in text:
        return "First NDC"

    return "Unclassified"


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------

def request_json(
    session: requests.Session,
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], requests.Response]:
    r = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json(), r


def parse_next_link(link_header: Optional[str]) -> Optional[str]:
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    for part in parts:
        if 'rel="next"' in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None


def fetch_api_pages(
    base_url: str,
    verify_ssl: bool = DEFAULT_VERIFY_SSL,
    max_pages: int = 10000,
    sleep_seconds: float = 0.2,
    sort_col: Optional[str] = None,
    sort_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    session = build_session(verify_ssl=verify_ssl)

    all_rows: List[Dict[str, Any]] = []
    seen_ids = set()

    next_url = base_url
    next_params: Optional[Dict[str, Any]] = {"page": 1}
    if sort_col:
        next_params["sort_col"] = sort_col
    if sort_dir:
        next_params["sort_dir"] = sort_dir

    page_count = 0

    while next_url and page_count < max_pages:
        page_count += 1
        try:
            payload, resp = request_json(session, next_url, params=next_params)
        except Exception as e:
            logging.info("Erreur API page %s: %s", page_count, e)
            print(f"Erreur API page {page_count}: {e}")
            break

        rows = payload.get("data", [])
        if not rows:
            print(f"Page {page_count}: 0 ligne, arrêt.")
            break

        new_count = 0
        for row in rows:
            row_id = row.get("id")
            key = row_id if row_id is not None else json.dumps(row, sort_keys=True, ensure_ascii=False)
            if key in seen_ids:
                continue
            seen_ids.add(key)
            all_rows.append(row)
            new_count += 1

        countries_seen = len({
            r.get("iso_code3") or r.get("code_iso_3")
            for r in all_rows
            if (r.get("iso_code3") or r.get("code_iso_3"))
        })
        print(f"Page {page_count}: {new_count} nouvelles lignes | total lignes: {len(all_rows)} | pays cumulés: {countries_seen}")

        link_header = resp.headers.get("Link")
        discovered_next = parse_next_link(link_header)

        if discovered_next:
            next_url = discovered_next
            next_params = None
        else:
            current_page = 1
            try:
                if next_params and "page" in next_params:
                    current_page = int(next_params["page"])
                else:
                    q = parse_qs(urlparse(resp.url).query)
                    if "page" in q:
                        current_page = int(q["page"][0])
            except Exception:
                current_page = page_count

            if new_count == 0:
                break

            next_url = base_url
            next_params = {"page": current_page + 1}
            if sort_col:
                next_params["sort_col"] = sort_col
            if sort_dir:
                next_params["sort_dir"] = sort_dir

        time.sleep(sleep_seconds)

    return all_rows


def load_json_files(input_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for fp in sorted(input_dir.glob("*.json")):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and "data" in payload:
                rows.extend(payload["data"])
            elif isinstance(payload, list):
                rows.extend(payload)
            else:
                logging.info("Fichier ignoré (structure non reconnue): %s", fp)
        except Exception as e:
            logging.info("Impossible de lire %s: %s", fp, e)
    return rows


# ---------------------------------------------------------------------
# Préparation des tables
# ---------------------------------------------------------------------

def rows_to_full_dataframe(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    rows = list(rows)
    if not rows:
        return pd.DataFrame()

    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())

    ordered_keys = sorted(all_keys)
    normalized = []
    for r in rows:
        normalized.append({k: r.get(k) for k in ordered_keys})

    df = pd.DataFrame(normalized)

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(clean_html_text)

    return df


def normalize_rows(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    clean = []
    for rec in rows:
        try:
            n = normalize_record(rec)
            n["value"] = clean_html_text(n["value"])
            n["indicator_id"] = str(n["indicator_id"]).strip().lower() if n["indicator_id"] is not None else None
            n["indicator_name"] = clean_html_text(n["indicator_name"])
            clean.append(n)
        except Exception as e:
            logging.info("Record ignoré: %s | erreur=%s", rec, e)

    df = pd.DataFrame(clean)
    if df.empty:
        return df

    df = df.drop_duplicates(
        subset=["iso_code3", "country", "indicator_id", "indicator_name", "value", "sector", "subsector"],
        keep="first"
    ).reset_index(drop=True)

    return df


def filter_useful_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["indicator_id"].isin(USEFUL_INDICATORS)].copy()


# ---------------------------------------------------------------------
# Construction d'une base harmonisée
# ---------------------------------------------------------------------

def extract_submission_groups(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["iso_code3", "country", "submission_date", "submission_type", "ndc_version"])

    sub_date = df[df["indicator_id"] == "submission_date"][["iso_code3", "country", "value"]].copy()
    sub_date["submission_date"] = sub_date["value"].apply(parse_date_mixed)
    sub_date = sub_date.drop(columns=["value"]).drop_duplicates()

    sub_type = df[df["indicator_id"] == "submission_type"][["iso_code3", "country", "value"]].copy()
    sub_type["submission_type"] = sub_type["value"].astype(str)
    sub_type["ndc_version"] = sub_type["submission_type"].apply(ndc_version_from_submission_type)
    sub_type = sub_type.drop(columns=["value"]).drop_duplicates()

    groups = pd.merge(sub_date, sub_type, on=["iso_code3", "country"], how="outer")

    if groups.empty:
        countries = df[["iso_code3", "country"]].drop_duplicates().copy()
        countries["submission_date"] = None
        countries["submission_type"] = None
        countries["ndc_version"] = None
        return countries

    return groups.drop_duplicates().reset_index(drop=True)


def build_harmonized_dataset(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = filter_useful_indicators(df)
    grouped_records = []
    submission_groups = extract_submission_groups(df)

    for _, grp in submission_groups.iterrows():
        iso3 = grp["iso_code3"]
        country = grp["country"]
        submission_date = grp.get("submission_date")
        submission_type = grp.get("submission_type")
        ndc_version = grp.get("ndc_version")

        g = df[(df["iso_code3"] == iso3) & (df["country"] == country)].copy()
        if g.empty:
            continue

        bag = defaultdict(list)
        for _, row in g.iterrows():
            iid = row.get("indicator_id")
            if iid:
                bag[iid].append(row.get("value"))

        summary = choose_best(bag.get("indc_summary", []))
        ghg_target = choose_best_target_text(bag.get("ghg_target", []))
        condition_text = choose_best(bag.get("conditionnalité", []) + bag.get("conditionality", []))
        target_year_txt = choose_best(bag.get("année_cible", []) + bag.get("target_year", []))
        timeframe = choose_best(bag.get("timeframe", []) + bag.get("période", []))
        target_ref_raw = choose_best(bag.get("ghg_target_type", []) + bag.get("type_cible_ges", []))
        mitigation_contribution_type = choose_best(bag.get("mitigation_contribution_type", []))
        adaptation = choose_best(bag.get("adaptation", []))
        non_ghg_target = choose_best(bag.get("non_ghg_target", []))

        parse_text_parts = [ghg_target, condition_text, target_ref_raw, timeframe]
        parse_text = " | ".join([x for x in parse_text_parts if x])

        if not parse_text.strip():
            parse_text = " | ".join([x for x in [summary, condition_text, target_ref_raw, timeframe] if x])

        if ndc_version is None:
            ndc_version = extract_ndc_version_from_text(ghg_target, summary, submission_type)

        conditional_pct, unconditional_pct = split_conditional_unconditional(parse_text)

        if conditional_pct is None and unconditional_pct is None:
            vals = extract_percent_values(parse_text)
            if len(vals) == 1 and condition_text:
                ctext = condition_text.lower()
                if "conditional" in ctext or "conditionnel" in ctext:
                    conditional_pct = vals[0]
                elif "unconditional" in ctext or "inconditionnel" in ctext:
                    unconditional_pct = vals[0]

        target_min_pct, target_max_pct = extract_percent_range(parse_text)
        target_format = infer_target_format(parse_text)

        target_reference = None
        if target_ref_raw:
            tr = str(target_ref_raw).lower()
            if "référence" in tr or "baseline" in tr or "scenario" in tr or "statu quo" in tr:
                target_reference = "BAU"
            elif "année de base" in tr or "base year" in tr or "1990" in tr or "2005" in tr or "2018 level" in tr:
                target_reference = "Base Year"
            elif "intens" in tr:
                target_reference = "Intensity baseline"

        if target_reference is None:
            target_reference = infer_target_reference(parse_text)

        base_year = None
        if target_reference == "BAU":
            m = re.search(r"(BAU|business as usual|statu quo|baseline)[^\d]{0,20}((19|20)\d{2})", parse_text, re.I)
            if m:
                base_year = f"BAU {m.group(2)}"
            else:
                base_year = "BAU"
        else:
            years = re.findall(r"\b((?:19|20)\d{2})\b", parse_text)
            ty = safe_int(target_year_txt)
            for y in years:
                y_int = int(y)
                if ty is None or y_int != ty:
                    base_year = y
                    break

        target_year = safe_int(target_year_txt)
        if target_year is None and timeframe:
            years = re.findall(r"\b((?:19|20)\d{2})\b", timeframe)
            if years:
                target_year = int(years[-1])

        scope = "Mitigation" if ghg_target and str(ghg_target).strip().lower() != "not applicable" else "Unknown"

        cleaning_flag = "clean"
        if ghg_target is None:
            cleaning_flag = "missing_ghg_target"
        elif summary and ghg_target and summary != ghg_target:
            if len(str(summary)) > 500:
                cleaning_flag = "summary_may_mix_old_and_new_ndcs"
        if mitigation_contribution_type and str(mitigation_contribution_type).lower() == "no ghg target":
            cleaning_flag = "no_ghg_target"

        ndc_stage_harmonized = harmonize_ndc_stage(
            submission_type=submission_type or "",
            summary=summary or "",
            ghg_target=ghg_target or "",
        )

        grouped_records.append({
            "iso_code3": iso3,
            "country": country,
            "submission_date": submission_date,
            "submission_type": submission_type,
            "ndc_version": ndc_version,
            "ndc_stage_harmonized": ndc_stage_harmonized,
            "target_format": target_format,
            "target_reference": target_reference,
            "base_year": base_year,
            "target_year": target_year,
            "target_min_pct": target_min_pct,
            "target_max_pct": target_max_pct,
            "conditional_pct": conditional_pct,
            "unconditional_pct": unconditional_pct,
            "mitigation_contribution_type": mitigation_contribution_type,
            "adaptation_included": adaptation,
            "scope": scope,
            "timeframe": timeframe,
            "sector": "Economy-wide",
            "summary": summary,
            "ghg_target": ghg_target,
            "non_ghg_target": non_ghg_target,
            "conditionality_text": condition_text,
            "cleaning_flag": cleaning_flag,
        })

    out = pd.DataFrame(grouped_records)
    if out.empty:
        return out

    cols = [
        "iso_code3", "country", "submission_date", "submission_type", "ndc_version",
        "ndc_stage_harmonized",
        "target_format", "target_reference", "base_year", "target_year",
        "target_min_pct", "target_max_pct",
        "conditional_pct", "unconditional_pct",
        "mitigation_contribution_type", "adaptation_included", "scope",
        "timeframe", "sector", "summary", "ghg_target", "non_ghg_target",
        "conditionality_text", "cleaning_flag"
    ]

    out = out[cols].drop_duplicates().sort_values(
        ["country", "submission_date", "ndc_stage_harmonized", "ndc_version"],
        na_position="last"
    ).reset_index(drop=True)

    return out


# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------

def export_outputs(
    df_api_full: pd.DataFrame,
    df_raw_normalized: pd.DataFrame,
    df_harmonized: pd.DataFrame,
    outdir: Path,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    raw_full_csv = outdir / "raw_api_full.csv"
    raw_norm_csv = outdir / "raw_normalized.csv"
    harmonized_csv = outdir / "ndc_harmonized.csv"
    wide_xlsx = outdir / "ndc_by_stage.xlsx"

    df_api_full.to_csv(raw_full_csv, index=False, encoding="utf-8-sig")
    df_raw_normalized.to_csv(raw_norm_csv, index=False, encoding="utf-8-sig")
    df_harmonized.to_csv(harmonized_csv, index=False, encoding="utf-8-sig")

    df_api_full_xlsx = sanitize_dataframe_for_excel(df_api_full)
    df_raw_normalized_xlsx = sanitize_dataframe_for_excel(df_raw_normalized)
    df_harmonized_xlsx = sanitize_dataframe_for_excel(df_harmonized)

    stage_sheet_map = {
        "INDC": "INDC",
        "First NDC": "First_NDC",
        "Updated/Second NDC": "Updated_or_Second_NDC",
        "Third NDC": "Third_NDC",
        "Unclassified": "Unclassified",
    }

    try:
        with pd.ExcelWriter(wide_xlsx, engine="openpyxl") as writer:
            df_api_full_xlsx.head(50000).to_excel(writer, index=False, sheet_name="raw_api_full")
            df_raw_normalized_xlsx.to_excel(writer, index=False, sheet_name="raw_normalized")
            df_harmonized_xlsx.to_excel(writer, index=False, sheet_name="harmonized_all")

            for stage, sheet_name in stage_sheet_map.items():
                subset = df_harmonized_xlsx[df_harmonized_xlsx["ndc_stage_harmonized"] == stage].copy()
                subset.to_excel(writer, index=False, sheet_name=sheet_name)

        print(f"[OK] {wide_xlsx}")
    except Exception as e:
        logging.info("Erreur export Excel: %s", e)
        print(f"[WARN] Export Excel échoué: {e}")

    print(f"[OK] {raw_full_csv}")
    print(f"[OK] {raw_norm_csv}")
    print(f"[OK] {harmonized_csv}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["api", "files"], default="api")
    parser.add_argument("--base-url", default=DEFAULT_API_URL, help="Endpoint JSON paginé Climate Watch")
    parser.add_argument("--input-dir", default="raw_json", help="Dossier contenant des .json")
    parser.add_argument("--outdir", default="output", help="Dossier de sortie")
    parser.add_argument("--verify-ssl", action="store_true", help="Vérifier le certificat SSL")
    parser.add_argument("--max-pages", type=int, default=10000, help="Nombre max de pages")
    parser.add_argument("--sleep-seconds", type=float, default=0.2, help="Pause entre pages")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    setup_logging(outdir)

    print(f"Mode utilisé : {args.mode}")

    if args.mode == "api":
        print(f"API utilisée : {args.base_url}")
        print(f"Vérification SSL : {args.verify_ssl}")
        rows = fetch_api_pages(
            base_url=args.base_url,
            verify_ssl=args.verify_ssl,
            max_pages=args.max_pages,
            sleep_seconds=args.sleep_seconds,
            sort_col=None,
            sort_dir=None,
        )
    else:
        print(f"Dossier JSON : {args.input_dir}")
        rows = load_json_files(Path(args.input_dir))

    if not rows:
        raise SystemExit("Aucune donnée récupérée.")

    df_api_full = rows_to_full_dataframe(rows)
    if df_api_full.empty:
        raise SystemExit("Aucune ligne exploitable dans la table brute API.")

    df_raw_normalized = normalize_rows(rows)
    if df_raw_normalized.empty:
        raise SystemExit("Aucune ligne exploitable après normalisation.")

    df_harmonized = build_harmonized_dataset(df_raw_normalized)

    export_outputs(df_api_full, df_raw_normalized, df_harmonized, outdir)

    print("\nRésumé :")
    print(f"Lignes API brutes: {len(df_api_full)}")
    print(f"Colonnes API brutes: {len(df_api_full.columns)}")
    print(f"Pays distincts (API brute): {df_api_full['iso_code3'].nunique() if 'iso_code3' in df_api_full.columns else 'NA'}")
    print(f"Pays distincts (normalisé): {df_raw_normalized['iso_code3'].nunique() if 'iso_code3' in df_raw_normalized.columns else 'NA'}")
    print(f"Pays distincts (harmonisé): {df_harmonized['iso_code3'].nunique() if not df_harmonized.empty else 0}")
    print(f"Lignes harmonisées: {len(df_harmonized)}")

    if not df_harmonized.empty:
        print("\nRépartition par édition harmonisée :")
        print(df_harmonized["ndc_stage_harmonized"].value_counts(dropna=False).to_string())

        print("\nAperçu harmonisé :")
        print(df_harmonized.head(20).to_string(index=False))
    else:
        print("\nBase harmonisée vide.")


if __name__ == "__main__":
    main()
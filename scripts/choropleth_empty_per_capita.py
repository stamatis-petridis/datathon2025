"""
Choropleth map of empty dwellings per capita by municipality.

Inputs:
- outputs/friction_by_municipality.json
- data/elstat/csv/plithismos.csv (ELSTAT 2021 population by municipality)
- data/geo/gadm41_GRC_3.shp

Outputs:
- outputs/choropleth_empty_per_capita.png (static, dpi=300)
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, Tuple

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from fuzzywuzzy import fuzz, process
from matplotlib import colormaps
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize


DATA_ROOT = Path(__file__).resolve().parents[1]
FRICTION_JSON = DATA_ROOT / "outputs" / "friction_by_municipality.json"
POP_CSV = DATA_ROOT / "data" / "elstat" / "csv" / "plithismos.csv"
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
PNG_OUT = DATA_ROOT / "outputs" / "choropleth_empty_per_capita.png"

CMAP_NAME = "YlOrRd"


GREEK_TO_LATIN = {
    "Α": "A", "Β": "V", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z", "Η": "I", "Θ": "Th",
    "Ι": "I", "Κ": "K", "Λ": "L", "Μ": "M", "Ν": "N", "Ξ": "X", "Ο": "O", "Π": "P",
    "Ρ": "R", "Σ": "S", "Τ": "T", "Υ": "Y", "Φ": "F", "Χ": "Ch", "Ψ": "Ps", "Ω": "O",
    "ά": "a", "έ": "e", "ί": "i", "ό": "o", "ύ": "y", "ή": "i", "ώ": "o", "ϊ": "i",
    "ϋ": "y", "ΐ": "i", "ΰ": "y", "ς": "s", "α": "a", "β": "v", "γ": "g", "δ": "d",
    "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "τ": "t", "υ": "y",
    "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
}


def transliterate(text: str) -> str:
    return "".join(GREEK_TO_LATIN.get(ch, ch) for ch in text)


def normalize(text: str) -> str:
    text = transliterate(str(text))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def _norm_greek(text: str) -> str:
    """Accent-stripping normalization for Greek-only joins."""
    if not isinstance(text, str):
        text = str(text)
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return without_accents.lower().strip()


def build_name_index(names: Iterable[str]) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for name in names:
        norm = normalize(name)
        if norm and norm not in index:
            index[norm] = name
    return index


def match_names(targets: Iterable[str], candidates: Dict[str, str]) -> Dict[str, Tuple[str, int]]:
    cand_norms = list(candidates.keys())
    matches: Dict[str, Tuple[str, int]] = {}
    for target in targets:
        norm = normalize(target)
        if norm in candidates:
            matches[target] = (candidates[norm], 100)
            continue
        if not cand_norms:
            continue
        best_norm, score = process.extractOne(norm, cand_norms, scorer=fuzz.token_sort_ratio)
        matches[target] = (candidates[best_norm], score)
    return matches


def load_population() -> pd.DataFrame:
    """
    Load ELSTAT 2021 population per municipality from plithismos.csv.

    Expects:
    - 'Γεωγρα-φικό επίπεδο' == 5 for municipalities
    - 'Περιγραφή' like 'ΔΗΜΟΣ ΚΟΜΟΤΗΝΗΣ'
    - 'Μόνιμος πληθυσμός' numeric population
    """
    if not POP_CSV.exists():
        raise FileNotFoundError(f"Missing population CSV: {POP_CSV}")

    df = pd.read_csv(POP_CSV)
    level_col = "Γεωγρα-φικό επίπεδο"
    name_col = "Περιγραφή"
    pop_col = "Μόνιμος πληθυσμός"

    for col in (level_col, name_col, pop_col):
        if col not in df.columns:
            raise KeyError(f"Expected column '{col}' in {POP_CSV}, found {list(df.columns)}")

    muni = df[df[level_col] == 5].copy()

    def clean_name(desc: str) -> str:
        s = str(desc).strip()
        if s.startswith("ΔΗΜΟΣ "):
            s = s[len("ΔΗΜΟΣ ") :]
        return s

    muni["name_pop"] = muni[name_col].map(clean_name)
    muni["population"] = pd.to_numeric(muni[pop_col], errors="coerce")
    muni = muni[muni["population"].notna()].copy()
    muni["norm_name"] = muni["name_pop"].map(_norm_greek)
    return muni[["norm_name", "population", "name_pop"]]


def load_friction_with_population() -> pd.DataFrame:
    """Load friction JSON and join with population per municipality."""
    if not FRICTION_JSON.exists():
        raise FileNotFoundError(f"Missing friction JSON: {FRICTION_JSON}")

    data = json.loads(FRICTION_JSON.read_text(encoding="utf-8"))
    muni_records = data.get("municipalities", [])
    if not muni_records:
        raise ValueError("No 'municipalities' records found in friction JSON.")

    df = pd.DataFrame(muni_records)
    required = {"name", "s_empty", "s_total", "sigma"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing expected fields in friction data: {missing}")

    df["s_empty"] = pd.to_numeric(df["s_empty"], errors="coerce")
    df["s_total"] = pd.to_numeric(df["s_total"], errors="coerce")
    df["sigma"] = pd.to_numeric(df["sigma"], errors="coerce")
    df = df[df["s_total"] > 0].copy()

    df["norm_name"] = df["name"].map(_norm_greek)

    pop = load_population()
    merged = df.merge(pop, on="norm_name", how="inner", suffixes=("", "_pop"))
    merged = merged[merged["population"] > 0].copy()

    merged["empty_per_capita"] = merged["s_empty"] / merged["population"]
    return merged


def prepare_dataframe(gdf: gpd.GeoDataFrame, muni_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Match friction+population municipalities to GADM shapes (same logic as choropleth_municipalities)."""
    muni_df = muni_df.copy()
    muni_df["matched_name"] = pd.NA
    muni_df["match_score"] = pd.NA

    overrides_one = {
        "Piraeus": "ΠΕΙΡΑΙΩΣ",
        "Athens": "ΑΘΗΝΑΙΩΝ",
        "Acharnes": "ΑΧΑΡΝΩΝ",
        "Heraklion": "ΗΡΑΚΛΕΙΟΥ",
        "Naousa": "ΗΡΩΙΚΗΣ ΠΟΛΕΩΣ ΝΑΟΥΣΑΣ",
        "Abdera": "ΑΒΔΗΡΩΝ",
        "Ithaca": "ΙΘΑΚΗΣ",
        "Paxi": "ΠΑΞΩΝ",
        "Patras": "ΠΑΤΡΕΩΝ",
        "Chalcis": "ΧΑΛΚΙΔΕΩΝ",
        "Thebes": "ΘΗΒΑΙΩΝ",
        "Delphi": "ΔΕΛΦΩΝ",
        "Lamia": "ΛΑΜΙΕΩΝ",
        "Cythera": "ΚΥΘΗΡΩΝ",
        "Psara": "ΗΡΩΙΚΗΣ ΝΗΣΟΥ ΨΑΡΩΝ",
        "Ios": "ΙΗΤΩΝ",
        "Kasos": "ΗΡΩΙΚΗΣ ΝΗΣΟΥ ΚΑΣΟΥ",
        "Orestida": "ΑΡΓΟΥΣ ΟΡΕΣΤΙΚΟΥ",
        "Missolonghi": "ΙΕΡΑΣ ΠΟΛΗΣ ΜΕΣΟΛΟΓΓΙΟΥ",
        "Kalambaka": "ΜΕΤΕΩΡΩΝ",
        "Molos-Agios Konstantinos": "ΚΑΜΕΝΩΝ ΒΟΥΡΛΩΝ",
        "South Kynouria": "ΝΟΤΙΑΣ ΚΥΝΟΥΡΙΑΣ",
    }

    overrides_many = {
        "Lesbos": ["ΔΥΤΙΚΗΣ ΛΕΣΒΟΥ", "ΜΥΤΙΛΗΝΗΣ"],
        "Cephalonia": ["ΑΡΓΟΣΤΟΛΙΟΥ", "ΛΗΞΟΥΡΙΟΥ", "ΣΑΜΗΣ"],
    }

    greek_to_idx = {name: i for i, name in enumerate(muni_df["name"])}
    for gadm_name, greek_name in overrides_one.items():
        idx = greek_to_idx.get(greek_name)
        if idx is not None:
            muni_df.loc[idx, "matched_name"] = gadm_name
            muni_df.loc[idx, "match_score"] = 100

    override_rows = []
    for gadm_name, greek_list in overrides_many.items():
        subset = muni_df[muni_df["name"].isin(greek_list)]
        if subset.empty:
            continue
        s_total = subset["s_total"].sum()
        s_empty = subset["s_empty"].sum()
        population = subset["population"].sum()
        if population <= 0 or s_total <= 0:
            continue
        sigma = s_empty / s_total
        empty_pc = s_empty / population
        override_rows.append(
            {
                "name": f"{gadm_name} (agg)",
                "matched_name": gadm_name,
                "match_score": 100,
                "s_total": s_total,
                "s_empty": s_empty,
                "population": population,
                "sigma": sigma,
                "empty_per_capita": empty_pc,
            }
        )
    if override_rows:
        muni_df = pd.concat([muni_df, pd.DataFrame(override_rows)], ignore_index=True)

    gadm_filtered = gdf[gdf["NAME_3"] != "Athos"].copy()
    gadm_index = build_name_index(gadm_filtered["NAME_3"])

    remaining = muni_df[muni_df["matched_name"].isna()]
    remaining_matches = match_names(remaining["name"].tolist(), gadm_index)
    muni_df.loc[remaining.index, "matched_name"] = remaining["name"].map(
        lambda x: remaining_matches.get(x, (None, None))[0]
    )
    muni_df.loc[remaining.index, "match_score"] = remaining["name"].map(
        lambda x: remaining_matches.get(x, (None, None))[1]
    )

    muni_df_sorted = muni_df.sort_values(by=["match_score"], ascending=False)
    muni_df_dedup = muni_df_sorted.drop_duplicates(subset=["matched_name"])

    merged_all = gadm_filtered.merge(muni_df_dedup, left_on="NAME_3", right_on="matched_name", how="left")
    merged = merged_all.dropna(subset=["empty_per_capita"])
    return merged


def human_ratio_tick(val: float) -> str:
    """Format legend ticks like '0.1', '0.5', '1.0', '2.0+'."""
    if val >= 2.0:
        return "2.0+"
    return f"{val:.1f}"


def plot_static(merged: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 10))

    # Cap values at 2.0 for color scaling
    merged = merged.copy()
    merged["empty_pc_clipped"] = merged["empty_per_capita"].clip(upper=2.0)

    vmin, vmax = 0.0, 2.0
    cmap = colormaps.get_cmap(CMAP_NAME)
    norm = Normalize(vmin=vmin, vmax=vmax)

    merged.plot(
        column="empty_pc_clipped",
        cmap=cmap,
        norm=norm,
        linewidth=0.1,
        edgecolor="black",
        ax=ax,
    )

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)

    ticks = [0.1, 0.5, 1.0, 2.0]
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([human_ratio_tick(t) for t in ticks])
    cbar.set_label("Empty dwellings per person")

    ax.set_title("Empty Dwellings per Capita by Municipality — Greece 2021", fontsize=14, weight="bold")
    ax.text(
        0.5,
        0.92,
        "High ratio = excess empty stock relative to population",
        fontsize=10,
        ha="center",
        transform=fig.transFigure,
    )
    ax.axis("off")

    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    gdf = gpd.read_file(SHAPE_PATH).to_crs(epsg=4326)
    muni = load_friction_with_population()
    merged = prepare_dataframe(gdf, muni)
    if merged.empty:
        raise SystemExit("No matched municipalities with empty_per_capita values.")
    plot_static(merged)


if __name__ == "__main__":
    main()


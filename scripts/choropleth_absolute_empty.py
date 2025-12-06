"""
Choropleth map of absolute empty dwellings (s_empty) by municipality.

Inputs:
- data/geo/gadm41_GRC_3.shp
- outputs/friction_by_municipality.json

Outputs:
- outputs/choropleth_absolute_empty.png (static, dpi=300)
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, Tuple

import geopandas as gpd
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz, process
from matplotlib import colormaps
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable


DATA_ROOT = Path(__file__).resolve().parents[1]
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
JSON_PATH = DATA_ROOT / "outputs" / "friction_by_municipality.json"
PNG_OUT = DATA_ROOT / "outputs" / "choropleth_absolute_empty.png"

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
    text = transliterate(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


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


def load_data():
    gdf = gpd.read_file(SHAPE_PATH).to_crs(epsg=4326)
    with JSON_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    muni_records = data.get("municipalities", [])
    return gdf, muni_records


def prepare_dataframe(gdf: gpd.GeoDataFrame, muni_records):
    muni_df = gpd.pd.DataFrame(muni_records)
    muni_df["matched_name"] = gpd.pd.NA
    muni_df["match_score"] = gpd.pd.NA

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

    # Apply one-to-one overrides
    greek_to_idx = {name: i for i, name in enumerate(muni_df["name"])}
    for gadm_name, greek_name in overrides_one.items():
        idx = greek_to_idx.get(greek_name)
        if idx is not None:
            muni_df.loc[idx, "matched_name"] = gadm_name
            muni_df.loc[idx, "match_score"] = 100

    # Aggregated rows for many-to-one overrides (weighted by s_total)
    override_rows = []
    for gadm_name, greek_list in overrides_many.items():
        subset = muni_df[muni_df["name"].isin(greek_list)]
        if subset.empty:
            continue
        total = subset["s_total"].sum()
        if total == 0:
            continue
        s_empty = subset["s_empty"].sum()
        override_rows.append(
            {
                "name": f"{gadm_name} (agg)",
                "matched_name": gadm_name,
                "match_score": 100,
                "s_total": total,
                "s_empty": s_empty,
            }
        )
    if override_rows:
        muni_df = gpd.pd.concat([muni_df, gpd.pd.DataFrame(override_rows)], ignore_index=True)

    # Fuzzy match remaining (skip Athos)
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

    # Deduplicate on matched_name keeping best score
    muni_df_sorted = muni_df.sort_values(by=["match_score"], ascending=False)
    muni_df_dedup = muni_df_sorted.drop_duplicates(subset=["matched_name"])

    merged_all = gadm_filtered.merge(muni_df_dedup, left_on="NAME_3", right_on="matched_name", how="left")
    merged = merged_all.dropna(subset=["s_empty"])
    return merged


def human_tick(val: float) -> str:
    """Format tick labels like 1k, 10k, 50k, 100k+."""
    if val >= 100000:
        return "100k+"
    if val >= 1000:
        return f"{int(val/1000):d}k"
    return f"{int(val):d}"


def plot_static(merged: gpd.GeoDataFrame):
    fig, ax = plt.subplots(figsize=(10, 10))

    # Linear scale over s_empty
    vmin = max(merged["s_empty"].min(), 1)
    vmax = merged["s_empty"].max()
    cmap = colormaps.get_cmap(CMAP_NAME)
    norm = Normalize(vmin=vmin, vmax=vmax)

    merged.plot(column="s_empty", cmap=cmap, norm=norm, linewidth=0.1, edgecolor="black", ax=ax)

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)

    # Custom ticks at nice round numbers
    ticks = [1_000, 5_000, 10_000, 25_000, 50_000, 100_000]
    ticks = [t for t in ticks if vmin <= t <= vmax]
    if ticks:
        cbar.set_ticks(ticks)
        cbar.set_ticklabels([human_tick(t) for t in ticks])
    cbar.set_label("Empty dwellings (s_empty)")

    ax.set_title("Absolute Empty Dwellings by Municipality — Greece 2021", fontsize=14, weight="bold")
    ax.text(
        0.5,
        0.92,
        "Where the locked stock physically exists",
        fontsize=10,
        ha="center",
        transform=fig.transFigure,
    )
    ax.axis("off")

    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    gdf, muni_records = load_data()
    merged = prepare_dataframe(gdf, muni_records)
    if merged.empty:
        raise SystemExit("No matched municipalities with s_empty values.")
    plot_static(merged)


if __name__ == "__main__":
    main()

"""
Choropleth: Greek municipal housing friction vs EU-style benchmarks.

Inputs:
- outputs/friction_by_municipality.json
- data/geo/gadm41_GRC_3.shp

Outputs:
- outputs/choropleth_eu_benchmark.png (static, dpi=300)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, Tuple

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from fuzzywuzzy import fuzz, process
from matplotlib import colors as mcolors
from matplotlib.patches import Patch


DATA_ROOT = Path(__file__).resolve().parents[1]
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
JSON_PATH = DATA_ROOT / "outputs" / "friction_by_municipality.json"
PNG_OUT = DATA_ROOT / "outputs" / "choropleth_eu_benchmark.png"


GREEK_TO_LATIN = {
    "Α": "A",
    "Β": "V",
    "Γ": "G",
    "Δ": "D",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "I",
    "Θ": "Th",
    "Ι": "I",
    "Κ": "K",
    "Λ": "L",
    "Μ": "M",
    "Ν": "N",
    "Ξ": "X",
    "Ο": "O",
    "Π": "P",
    "Ρ": "R",
    "Σ": "S",
    "Τ": "T",
    "Υ": "Y",
    "Φ": "F",
    "Χ": "Ch",
    "Ψ": "Ps",
    "Ω": "O",
    "ά": "a",
    "έ": "e",
    "ί": "i",
    "ό": "o",
    "ύ": "y",
    "ή": "i",
    "ώ": "o",
    "ϊ": "i",
    "ϋ": "y",
    "ΐ": "i",
    "ΰ": "y",
    "ς": "s",
    "α": "a",
    "β": "v",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "i",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "τ": "t",
    "υ": "y",
    "φ": "f",
    "χ": "ch",
    "ψ": "ps",
    "ω": "o",
}


def transliterate(text: str) -> str:
    return "".join(GREEK_TO_LATIN.get(ch, ch) for ch in text)


def normalize(text: str) -> str:
    text = transliterate(str(text))
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def build_name_index(names: Iterable[str]) -> Dict[str, str]:
    index: Dict[str, str] = {}
    for name in names:
        key = normalize(name)
        if key and key not in index:
            index[key] = name
    return index


def match_names(targets: Iterable[str], candidates: Dict[str, str]) -> Dict[str, Tuple[str, int]]:
    cand_keys = list(candidates.keys())
    out: Dict[str, Tuple[str, int]] = {}
    for target in targets:
        key = normalize(target)
        if key in candidates:
            out[target] = (candidates[key], 100)
            continue
        if not cand_keys:
            continue
        best, score = process.extractOne(key, cand_keys, scorer=fuzz.token_sort_ratio)
        out[target] = (candidates[best], score)
    return out


def load_data() -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    gdf = gpd.read_file(SHAPE_PATH).to_crs(epsg=4326)
    gdf = gdf[gdf["NAME_3"] != "Athos"].copy()
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    muni_records = data.get("municipalities", data)
    df = pd.DataFrame(muni_records)
    return gdf, df


def prepare_dataframe(gdf: gpd.GeoDataFrame, muni_df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Match ELSTAT municipalities to GADM L3 and attach sigma + EU benchmark."""
    if "name" not in muni_df.columns or "sigma" not in muni_df.columns:
        raise KeyError("Expected 'name' and 'sigma' in friction_by_municipality.json")

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

    # One-to-one overrides
    greek_to_idx = {name: i for i, name in enumerate(muni_df["name"])}
    for gadm_name, greek_name in overrides_one.items():
        idx = greek_to_idx.get(greek_name)
        if idx is not None:
            muni_df.loc[idx, "matched_name"] = gadm_name
            muni_df.loc[idx, "match_score"] = 100

    # Aggregated rows for many-to-one (use weighted sigma)
    agg_rows = []
    for gadm_name, greek_list in overrides_many.items():
        subset = muni_df[muni_df["name"].isin(greek_list)]
        if subset.empty:
            continue
        total = subset["s_total"].sum() if "s_total" in subset.columns else 0
        if total <= 0:
            continue
        sigma = (subset["sigma"] * subset["s_total"]).sum() / total
        agg_rows.append(
            {
                "name": f"{gadm_name} (agg)",
                "matched_name": gadm_name,
                "match_score": 100,
                "sigma": sigma,
                "s_total": total,
            }
        )
    if agg_rows:
        muni_df = pd.concat([muni_df, pd.DataFrame(agg_rows)], ignore_index=True)

    # Fuzzy match remaining to GADM
    gadm_index = build_name_index(gdf["NAME_3"])
    remaining = muni_df[muni_df["matched_name"].isna()]
    matches = match_names(remaining["name"].tolist(), gadm_index)
    muni_df.loc[remaining.index, "matched_name"] = remaining["name"].map(
        lambda x: matches.get(x, (None, None))[0]
    )
    muni_df.loc[remaining.index, "match_score"] = remaining["name"].map(
        lambda x: matches.get(x, (None, None))[1]
    )

    # Keep best match per GADM name
    muni_df = muni_df.sort_values("match_score", ascending=False).drop_duplicates(subset=["matched_name"])

    merged = gdf.merge(muni_df, left_on="NAME_3", right_on="matched_name", how="left")
    merged = merged.dropna(subset=["sigma"])
    return merged


EU_COLORS = {
    "European Efficient": "#006400",          # dark green
    "European Normal": "#2ca02c",             # green
    "Mediterranean Acceptable": "#a6d96a",    # light green
    "Elevated Friction": "#ffbb33",           # yellow
    "Structural Dysfunction": "#ff7f0e",      # orange
    "Market Collapse": "#d62728",             # red
}


def classify_eu(sigma: float) -> str:
    """Classify sigma into EU-style benchmark buckets."""
    if sigma < 0.10:
        return "European Efficient"
    if sigma < 0.15:
        return "European Normal"
    if sigma < 0.20:
        return "Mediterranean Acceptable"
    if sigma < 0.30:
        return "Elevated Friction"
    if sigma < 0.50:
        return "Structural Dysfunction"
    return "Market Collapse"


def plot_static(merged: gpd.GeoDataFrame) -> None:
    """Plot static PNG with EU benchmark categories."""
    merged = merged.copy()
    merged["sigma"] = merged["sigma"].astype(float)
    merged["eu_cat"] = merged["sigma"].map(classify_eu)

    fig, ax = plt.subplots(figsize=(10, 10))

    # Color each polygon by category using a discrete palette
    merged["color"] = merged["eu_cat"].map(EU_COLORS)
    merged.plot(color=merged["color"], linewidth=0.1, edgecolor="black", ax=ax)

    # Legend with counts
    counts = merged["eu_cat"].value_counts().to_dict()
    handles = []
    for label, color in EU_COLORS.items():
        count = counts.get(label, 0)
        pretty = label
        handles.append(Patch(color=color, label=f"{pretty} ({count})"))
    ax.legend(handles=handles, title="EU benchmark category", loc="lower left")

    ax.set_title("Greek Housing by EU Standards — Greece 2021", fontsize=14, weight="bold")
    ax.text(
        0.5,
        0.92,
        "Only 11% of Greek municipalities meet European efficiency norms",
        fontsize=10,
        ha="center",
        transform=fig.transFigure,
    )
    ax.axis("off")

    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    gdf, muni_df = load_data()
    merged = prepare_dataframe(gdf, muni_df)
    if merged.empty:
        raise SystemExit("No matched municipalities with sigma values.")
    plot_static(merged)


if __name__ == "__main__":
    main()


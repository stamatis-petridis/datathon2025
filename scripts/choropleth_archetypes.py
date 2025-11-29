"""
Choropleth map of housing market archetypes by municipality.

Inputs:
- outputs/municipal_archetypes.csv
- data/geo/gadm41_GRC_3.shp

Outputs:
- outputs/choropleth_archetypes.png (static)
- outputs/choropleth_archetypes.html (interactive folium)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from branca.element import MacroElement
from fuzzywuzzy import fuzz, process
from matplotlib import colormaps
from matplotlib import colors as mcolors
from matplotlib.patches import Patch

DATA_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = DATA_ROOT / "outputs" / "municipal_archetypes.csv"
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
PNG_OUT = DATA_ROOT / "outputs" / "choropleth_archetypes.png"
HTML_OUT = DATA_ROOT / "outputs" / "choropleth_archetypes.html"

ARCT_COLORS = {
    "TOURIST_DRAIN": "#d62728",
    "TRANSITIONAL": "#ffbb33",
    "HEALTHY": "#2ca02c",
    "SYSTEM_FAILURE": "#7f7f7f",
}

OVER_ONE = {
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

OVER_MANY = {
    "Lesbos": ["ΔΥΤΙΚΗΣ ΛΕΣΒΟΥ", "ΜΥΤΙΛΗΝΗΣ"],
    "Cephalonia": ["ΑΡΓΟΣΤΟΛΙΟΥ", "ΛΗΞΟΥΡΙΟΥ", "ΣΑΜΗΣ"],
}


def translit(text: str) -> str:
    table = {
        "Α": "A", "Β": "V", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z", "Η": "I", "Θ": "Th",
        "Ι": "I", "Κ": "K", "Λ": "L", "Μ": "M", "Ν": "N", "Ξ": "X", "Ο": "O", "Π": "P",
        "Ρ": "R", "Σ": "S", "Τ": "T", "Υ": "Y", "Φ": "F", "Χ": "Ch", "Ψ": "Ps", "Ω": "O",
        "ά": "a", "έ": "e", "ί": "i", "ό": "o", "ύ": "y", "ή": "i", "ώ": "o", "ϊ": "i",
        "ϋ": "y", "ΐ": "i", "ΰ": "y", "ς": "s", "α": "a", "β": "v", "γ": "g", "δ": "d",
        "ε": "e", "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
        "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s", "τ": "t", "υ": "y",
        "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
    }
    return "".join(table.get(ch, ch) for ch in text)


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", translit(text).lower())


def build_index(names: Iterable[str]) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for name in names:
        key = normalize(name)
        if key and key not in idx:
            idx[key] = name
    return idx


def match_names(targets: Iterable[str], candidates: Dict[str, str]) -> Dict[str, Tuple[str, int]]:
    cand_keys = list(candidates.keys())
    out: Dict[str, Tuple[str, int]] = {}
    for target in targets:
        key = normalize(target)
        if key in candidates:
            out[target] = (candidates[key], 100)
            continue
        best, score = process.extractOne(key, cand_keys, scorer=fuzz.token_sort_ratio)
        out[target] = (candidates[best], score)
    return out


def reclassify(row: pd.Series) -> str:
    sigma = row["sigma"]
    tourism = row["share_tourism"]
    if sigma > 0.5 and tourism > 0.3:
        return "TOURIST_DRAIN"
    if sigma > 0.5:
        return "SYSTEM_FAILURE"
    if 0.25 <= sigma <= 0.5:
        return "TRANSITIONAL"
    return "HEALTHY"


def prepare_dataframe() -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
    gdf = gpd.read_file(SHAPE_PATH).to_crs(epsg=4326)
    gdf = gdf[gdf["NAME_3"] != "Athos"]
    df = pd.read_csv(CSV_PATH)

    df["matched_name"] = pd.NA
    df["match_score"] = pd.NA

    # Apply one-to-one overrides
    name_to_idx = {n: i for i, n in enumerate(df["name"])}
    for gadm, greek in OVER_ONE.items():
        idx = name_to_idx.get(greek)
        if idx is not None:
            df.loc[idx, "matched_name"] = gadm
            df.loc[idx, "match_score"] = 100

    # Aggregate many-to-one with weighted fields
    extra_rows: List[Dict] = []
    for gadm, greek_list in OVER_MANY.items():
        subset = df[df["name"].isin(greek_list)]
        if subset.empty:
            continue
        total = subset["s_total"].sum()
        if total == 0:
            continue
        weighted = lambda col: float((subset[col] * subset["s_total"]).sum() / total)
        sigma = weighted("sigma")
        share_tourism = weighted("share_tourism")
        share_market = weighted("share_market")
        share_sys = weighted("share_system_failure")
        archetype = reclassify(pd.Series({"sigma": sigma, "share_tourism": share_tourism}))
        extra_rows.append(
            {
                "name": f"{gadm} (agg)",
                "matched_name": gadm,
                "match_score": 100,
                "sigma": sigma,
                "share_tourism": share_tourism,
                "share_market": share_market,
                "share_system_failure": share_sys,
                "archetype": archetype,
                "s_total": total,
            }
        )
    if extra_rows:
        df = pd.concat([df, pd.DataFrame(extra_rows)], ignore_index=True)

    # Fuzzy match remaining
    idx_map = build_index(gdf["NAME_3"])
    remaining = df[df["matched_name"].isna()]
    matches = match_names(remaining["name"].tolist(), idx_map)
    df.loc[remaining.index, "matched_name"] = remaining["name"].map(lambda x: matches[x][0])
    df.loc[remaining.index, "match_score"] = remaining["name"].map(lambda x: matches[x][1])

    # Deduplicate by best score
    df = df.sort_values(by="match_score", ascending=False).drop_duplicates(subset=["matched_name"])

    merged = gdf.merge(df, left_on="NAME_3", right_on="matched_name", how="left")
    matched = merged.dropna(subset=["archetype"])
    return matched, df


def plot_static(gdf: gpd.GeoDataFrame, counts: Dict[str, int]) -> None:
    fig, ax = plt.subplots(figsize=(10, 10))
    labels = list(ARCT_COLORS.keys())
    colors = gdf["archetype"].map(ARCT_COLORS)
    gdf.plot(color=colors, linewidth=0.1, edgecolor="black", ax=ax)
    legend_handles = [
        Patch(color=ARCT_COLORS[label], label=f"{label.replace('_', ' ').title()} ({counts.get(label, 0)})")
        for label in labels
    ]
    ax.legend(handles=legend_handles, title="Archetypes", loc="lower left")
    ax.set_title("Housing Market Archetypes — Greece 2021", fontsize=14, weight="bold")
    ax.text(
        0.5,
        0.92,
        "Four distinct housing regimes requiring different policy interventions",
        fontsize=10,
        ha="center",
        transform=fig.transFigure,
    )
    ax.axis("off")
    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


def add_folium_legend(map_obj: folium.Map, counts: Dict[str, int]) -> None:
    entries = ""
    for label, color in ARCT_COLORS.items():
        entries += (
            f"<div style='margin-bottom:4px;'>"
            f"<span style='background:{color};width:12px;height:12px;"
            f"display:inline-block;margin-right:6px;'></span>"
            f"{label.replace('_', ' ').title()} ({counts.get(label, 0)})"
            f"</div>"
        )
    html = (
        "<div style='position: fixed; bottom: 30px; right: 10px; z-index: 9999; "
        "background: white; padding: 10px; border: 1px solid #ccc; border-radius: 4px;'>"
        "<b>Archetypes</b><br>"
        f"{entries}"
        "</div>"
    )
    legend_el = folium.Element(html)
    map_obj.get_root().html.add_child(legend_el)  # type: ignore


def plot_interactive(gdf: gpd.GeoDataFrame, counts: Dict[str, int]) -> None:
    center = gdf.geometry.union_all().centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=7, tiles="cartodbpositron")

    def style_fn(feature):
        arche = feature["properties"].get("archetype")
        color = ARCT_COLORS.get(arche, "#cccccc")
        return {
            "fillColor": color,
            "color": "#666666",
            "weight": 0.3,
            "fillOpacity": 0.7,
        }

    tooltip = folium.GeoJsonTooltip(fields=["NAME_3", "archetype"], aliases=["Municipality", "Archetype"])

    folium.GeoJson(
        gdf[["NAME_3", "archetype", "sigma", "geometry"]],
        style_function=style_fn,
        tooltip=tooltip,
        name="Archetypes",
    ).add_to(m)

    add_folium_legend(m, counts)
    folium.LayerControl().add_to(m)

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(HTML_OUT))


def main() -> None:
    matched, df = prepare_dataframe()
    counts = matched["archetype"].value_counts().to_dict()
    print(f"Matched {len(matched)} municipalities with archetypes.")
    plot_static(matched, counts)
    plot_interactive(matched, counts)


if __name__ == "__main__":
    main()

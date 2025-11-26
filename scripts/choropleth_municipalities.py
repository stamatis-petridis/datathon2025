"""
Create a choropleth map of housing friction (sigma) by municipality.

Inputs:
- data/geo/gadm41_GRC_3.shp (GADM level 3 municipalities)
- outputs/friction_by_municipality.json (Greek names, sigma values)

Outputs:
- outputs/choropleth_municipalities.png (static, dpi=300)
- outputs/choropleth_municipalities.html (interactive folium map)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, Tuple

import geopandas as gpd
import folium
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz, process
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable, get_cmap
from branca import colormap as bcm


DATA_ROOT = Path(__file__).resolve().parents[1]
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
JSON_PATH = DATA_ROOT / "outputs" / "friction_by_municipality.json"
PNG_OUT = DATA_ROOT / "outputs" / "choropleth_municipalities.png"
HTML_OUT = DATA_ROOT / "outputs" / "choropleth_municipalities.html"

VMIN = 0.10
VMAX = 0.85
CMAP_NAME = "RdYlGn_r"  # or "viridis_r"


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
    """Return mapping target -> (matched candidate original, score)."""
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
    with JSON_PATH.open() as f:
        data = json.load(f)
    muni_records = data.get("municipalities", [])
    return gdf, muni_records


def prepare_dataframe(gdf: gpd.GeoDataFrame, muni_records):
    muni_df = gpd.pd.DataFrame(muni_records)

    gadm_index = build_name_index(gdf["NAME_3"])
    target_names = muni_df["name"].tolist()
    matches = match_names(target_names, gadm_index)

    muni_df["matched_name"] = muni_df["name"].map(lambda x: matches.get(x, (None, None))[0])
    muni_df["match_score"] = muni_df["name"].map(lambda x: matches.get(x, (None, None))[1])

    merged = gdf.merge(muni_df, left_on="NAME_3", right_on="matched_name", how="left")
    merged = merged.dropna(subset=["sigma"])
    return merged


def plot_static(merged: gpd.GeoDataFrame):
    fig, ax = plt.subplots(figsize=(10, 10))
    cmap = get_cmap(CMAP_NAME)
    norm = Normalize(vmin=VMIN, vmax=VMAX)

    merged.plot(column="sigma", cmap=cmap, norm=norm, linewidth=0.1, edgecolor="black", ax=ax)

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("σ (locked stock share)")

    ax.set_title("Housing Friction Index (σ) by Municipality — Greece 2021", fontsize=14, weight="bold")
    ax.text(0.5, 0.92, "σ = locked stock share | Data: ELSTAT Census 2021", fontsize=10,
            ha="center", transform=fig.transFigure)
    ax.axis("off")

    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_interactive(merged: gpd.GeoDataFrame):
    merged = merged.to_crs(epsg=4326)
    center = merged.geometry.unary_union.centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=7, tiles="cartodbpositron")

    colormap = bcm.linear.RdYlGn_11.scale(VMIN, VMAX).to_step(10)
    colormap.caption = "σ (locked stock share)"

    def style_fn(feature):
        val = feature["properties"].get("sigma")
        if val is None:
            return {"fillColor": "#cccccc", "color": "#666666", "weight": 0.3, "fillOpacity": 0.5}
        return {
            "fillColor": colormap(val),
            "color": "#666666",
            "weight": 0.3,
            "fillOpacity": 0.7,
        }

    tooltip = folium.GeoJsonTooltip(
        fields=["NAME_3", "sigma"],
        aliases=["Municipality", "σ"],
        localize=True,
        sticky=False,
    )

    folium.GeoJson(
        merged[["NAME_3", "sigma", "geometry"]],
        style_function=style_fn,
        tooltip=tooltip,
        name="Housing Friction (σ)",
    ).add_to(m)

    colormap.add_to(m)
    folium.LayerControl().add_to(m)

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(HTML_OUT))


def main():
    gdf, muni_records = load_data()
    merged = prepare_dataframe(gdf, muni_records)
    if merged.empty:
        raise SystemExit("No matched municipalities with sigma values.")
    plot_static(merged)
    plot_interactive(merged)


if __name__ == "__main__":
    main()
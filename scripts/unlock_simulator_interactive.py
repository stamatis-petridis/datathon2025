"""
Interactive unlock simulator (folium) with multiple unlock scenarios.

Creates layer toggles for unlock levels (0%, 10%, 20%, 30%, 40%) showing
simulated σ and price change on a map.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, Tuple

import folium
import geopandas as gpd
import pandas as pd
from branca.colormap import linear
from branca.element import Element
from fuzzywuzzy import fuzz, process

DATA_ROOT = Path(__file__).resolve().parents[1]
FRICTION_JSON = DATA_ROOT / "outputs" / "friction_by_municipality.json"
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
HTML_OUT = DATA_ROOT / "outputs" / "unlock_simulator_interactive.html"

UNLOCK_LEVELS = [0.0, 0.1, 0.2, 0.3, 0.4]
ALPHA = 0.4  # price model parameter

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
    return re.sub(r"[^a-z0-9]+", "", translit(str(text)).lower())


def build_index(names: Iterable[str]) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for n in names:
        key = normalize(n)
        if key and key not in idx:
            idx[key] = n
    return idx


def match_names(targets: Iterable[str], candidates: Dict[str, str]) -> Dict[str, str]:
    cand_keys = list(candidates.keys())
    out: Dict[str, str] = {}
    for t in targets:
        key = normalize(t)
        if key in candidates:
            out[t] = candidates[key]
        else:
            best, _ = process.extractOne(key, cand_keys, scorer=fuzz.token_sort_ratio)
            out[t] = candidates[best]
    return out


def load_friction(path: Path) -> pd.DataFrame:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    records = data["municipalities"] if isinstance(data, dict) and "municipalities" in data else data
    df = pd.DataFrame(records)
    df = df.rename(columns={"name": "Municipality"})
    df["sigma"] = pd.to_numeric(df["sigma"], errors="coerce")
    return df


def merge_shapes(df: pd.DataFrame, shp: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp).to_crs(epsg=4326)
    gdf = gdf[gdf["NAME_3"] != "Athos"]
    idx_map = build_index(gdf["NAME_3"])
    greek_to_gadm = {v: k for k, v in OVER_ONE.items()}

    df = df.copy()
    df["matched_name"] = df["Municipality"].map(greek_to_gadm)
    remaining = df["matched_name"].isna()
    matched_remaining = match_names(df.loc[remaining, "Municipality"], idx_map)
    df.loc[remaining, "matched_name"] = df.loc[remaining, "Municipality"].map(matched_remaining)

    merged = gdf.merge(df, left_on="NAME_3", right_on="matched_name", how="left")
    return merged


def add_unlock_layer(m: folium.Map, gdf: gpd.GeoDataFrame, unlock_pct: float, sigma_min: float, sigma_max: float) -> None:
    df = gdf.copy()
    df["sigma_new"] = df["sigma"] * (1.0 - unlock_pct)
    df["F_new"] = 1.0 / (1.0 - df["sigma_new"].clip(upper=0.999999))
    df["price_change_pct"] = -ALPHA * (unlock_pct * df["sigma"] / (1 - df["sigma"].clip(upper=0.999999))) * 100

    layer = folium.FeatureGroup(name=f"Unlock {int(unlock_pct*100)}%")
    cmap = linear.RdYlGn_11.scale(sigma_min, sigma_max)

    def style_fn(feature):
        val = feature["properties"].get("sigma_new")
        if val is None:
            return {"fillColor": "#cccccc", "color": "#666666", "weight": 0.3, "fillOpacity": 0.5}
        return {
            "fillColor": cmap(val),
            "color": "#666666",
            "weight": 0.3,
            "fillOpacity": 0.7,
        }

    tooltip = folium.GeoJsonTooltip(
        fields=["NAME_3", "sigma", "sigma_new", "price_change_pct"],
        aliases=["Municipality", "Baseline σ", "Simulated σ", "Price change (%)"],
        localize=True,
        sticky=False,
    )

    folium.GeoJson(
        df[["NAME_3", "sigma", "sigma_new", "price_change_pct", "geometry"]],
        style_function=style_fn,
        tooltip=tooltip,
        name=f"Unlock {int(unlock_pct*100)}%",
    ).add_to(layer)

    cmap.caption = "Simulated σ"
    cmap.add_to(m)
    layer.add_to(m)


def main() -> None:
    df = load_friction(FRICTION_JSON)
    merged = merge_shapes(df, SHAPE_PATH)
    sigma_min = merged["sigma"].min(skipna=True)
    sigma_max = merged["sigma"].max(skipna=True)

    center = merged.geometry.union_all().centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=7, tiles="cartodbpositron")

    for pct in UNLOCK_LEVELS:
        add_unlock_layer(m, merged, pct, sigma_min, sigma_max)

    folium.LayerControl().add_to(m)

    # Add slider to toggle unlock levels
    map_id = m.get_name()
    slider_html = f"""
    <script>
    function addUnlockSlider_{map_id}() {{
      var map = {map_id};
      var control = L.control({{position:'topright'}});
      control.onAdd = function() {{
        var div = L.DomUtil.create('div','unlock-slider');
        div.innerHTML = '<label style="background:white;padding:6px;border:1px solid #ccc;border-radius:4px;display:inline-block;">Unlock: <input type="range" id="unlockRange" min="0" max="40" step="10" value="0" style="vertical-align:middle;"> <span id="unlockVal">0%</span></label>';
        L.DomEvent.disableClickPropagation(div);
        return div;
      }};
      control.addTo(map);
      function updateLayers(val) {{
        var target = 'Unlock ' + val + '%';
        map.eachLayer(function(layer) {{
          if (layer.options && layer.options.name && layer.options.name.startsWith('Unlock ')) {{
            if (layer.options.name === target) {{ map.addLayer(layer); }}
            else {{ map.removeLayer(layer); }}
          }}
        }});
        var lbl = document.getElementById('unlockVal');
        if (lbl) lbl.innerText = val + '%';
      }}
      updateLayers(0);
      var slider = document.getElementById('unlockRange');
      if (slider) {{
        slider.oninput = function(e) {{ updateLayers(e.target.value); }};
      }}
    }}
    addUnlockSlider_{map_id}();
    </script>
    """
    m.get_root().html.add_child(Element(slider_html))

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(HTML_OUT))
    print(f"✓ Saved interactive unlock map to {HTML_OUT.resolve()}")


if __name__ == "__main__":
    main()

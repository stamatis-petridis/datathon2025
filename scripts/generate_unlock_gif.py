"""
Generate an animated GIF showing the effect of unlocking a fraction of locked stock.

For each unlock percentage in [start, end] with the given step:
- new_sigma = sigma * (1 - unlock_pct/100)
- map municipalities by new_sigma (fixed color scale 0–0.85, RdYlGn with red=high, green=low)
- title shows unlock level, subtitle shows national σ baseline → new σ

Outputs:
- outputs/unlock_animation.gif (by default), looping forever.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Tuple, List

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from fuzzywuzzy import fuzz, process
from matplotlib import colormaps
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize


DATA_ROOT = Path(__file__).resolve().parents[1]
SHAPE_PATH = DATA_ROOT / "data" / "geo" / "gadm41_GRC_3.shp"
JSON_PATH = DATA_ROOT / "outputs" / "friction_by_municipality.json"
DEFAULT_OUT = DATA_ROOT / "outputs" / "unlock_animation.gif"

VMIN = 0.0
VMAX = 0.85
CMAP_NAME = "RdYlGn_r"  # green = low, red = high


# Greek -> Latin transliteration used for fuzzy matching
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

# Overrides for tricky name matches Greek -> GADM English
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


def transliterate(text: str) -> str:
    return "".join(GREEK_TO_LATIN.get(ch, ch) for ch in text)


def normalize(text: str) -> str:
    text = transliterate(str(text))
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def build_index(names: Iterable[str]) -> Dict[str, str]:
    idx: Dict[str, str] = {}
    for name in names:
        key = normalize(name)
        if key and key not in idx:
            idx[key] = name
    return idx


def match_names(targets: Iterable[str], candidates: Dict[str, str]) -> Dict[str, Tuple[str, int]]:
    cand_norms = list(candidates.keys())
    out: Dict[str, Tuple[str, int]] = {}
    for target in targets:
        key = normalize(target)
        if key in candidates:
            out[target] = (candidates[key], 100)
            continue
        if not cand_norms:
            continue
        best, score = process.extractOne(key, cand_norms, scorer=fuzz.token_sort_ratio)
        out[target] = (candidates[best], score)
    return out


def load_friction() -> pd.DataFrame:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"Missing friction file: {JSON_PATH}")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    muni = data.get("municipalities", data)
    df = pd.DataFrame(muni)
    required = {"name", "s_total", "s_empty", "sigma"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing expected fields in friction JSON: {missing}")
    df["s_total"] = pd.to_numeric(df["s_total"], errors="coerce")
    df["s_empty"] = pd.to_numeric(df["s_empty"], errors="coerce")
    df["sigma"] = pd.to_numeric(df["sigma"], errors="coerce")
    df = df[df["s_total"] > 0].copy()
    return df


def prepare_dataframe(gdf: gpd.GeoDataFrame, df: pd.DataFrame) -> gpd.GeoDataFrame:
    df = df.copy()
    df["matched_name"] = pd.NA
    df["match_score"] = pd.NA

    # One-to-one overrides
    greek_to_idx = {name: i for i, name in enumerate(df["name"])}
    for gadm, greek in OVER_ONE.items():
        idx = greek_to_idx.get(greek)
        if idx is not None:
            df.loc[idx, "matched_name"] = gadm
            df.loc[idx, "match_score"] = 100

    # Aggregated rows for many-to-one (sum s_total/s_empty, weighted sigma)
    extra_rows: List[Dict] = []
    for gadm, greek_list in OVER_MANY.items():
        subset = df[df["name"].isin(greek_list)]
        if subset.empty:
            continue
        total = subset["s_total"].sum()
        empty = subset["s_empty"].sum()
        if total <= 0:
            continue
        sigma = empty / total
        extra_rows.append(
            {
                "name": f"{gadm} (agg)",
                "matched_name": gadm,
                "match_score": 100,
                "s_total": total,
                "s_empty": empty,
                "sigma": sigma,
            }
        )
    if extra_rows:
        df = pd.concat([df, pd.DataFrame(extra_rows)], ignore_index=True)

    # Fuzzy match remaining
    gadm_filtered = gdf[gdf["NAME_3"] != "Athos"].copy()
    idx_map = build_index(gadm_filtered["NAME_3"])
    remaining = df[df["matched_name"].isna()]
    matches = match_names(remaining["name"].tolist(), idx_map)
    df.loc[remaining.index, "matched_name"] = remaining["name"].map(lambda x: matches.get(x, (None, None))[0])
    df.loc[remaining.index, "match_score"] = remaining["name"].map(lambda x: matches.get(x, (None, None))[1])

    # Deduplicate by best score
    df = df.sort_values("match_score", ascending=False).drop_duplicates(subset=["matched_name"])
    merged = gadm_filtered.merge(df, left_on="NAME_3", right_on="matched_name", how="left")
    merged = merged.dropna(subset=["sigma"])
    return merged


def national_sigma(df: pd.DataFrame, empty_col: str = "s_empty") -> float:
    """Compute national sigma = sum(empty) / sum(total) using the given empty column."""
    s_total = pd.to_numeric(df["s_total"], errors="coerce").sum()
    s_empty = pd.to_numeric(df[empty_col], errors="coerce").sum()
    if s_total <= 0:
        return float("nan")
    return s_empty / s_total


def generate_frames(merged: gpd.GeoDataFrame, levels: list[int], temp_dir: Path) -> list[Path]:
    frames: list[Path] = []
    baseline_sigma = national_sigma(merged, "s_empty")

    for pct in levels:
        u = pct / 100.0
        # Scale s_empty (and sigma accordingly) for each municipality
        merged["sigma_new"] = merged["sigma"] * (1.0 - u)

        # National sigma after unlock (using scaled s_empty)
        merged["s_empty_new"] = merged["s_empty"] * (1.0 - u)
        nat_new = national_sigma(merged, "s_empty_new")

        fig, ax = plt.subplots(figsize=(10, 10))
        cmap = colormaps.get_cmap(CMAP_NAME)
        norm = Normalize(vmin=VMIN, vmax=VMAX)

        merged.plot(column="sigma_new", cmap=cmap, norm=norm, linewidth=0.1, edgecolor="black", ax=ax)

        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label("σ (after unlock)")

        ax.set_title(f"Unlock Effect: {pct}% of locked stock released", fontsize=14, weight="bold")
        ax.text(
            0.5,
            0.92,
            f"National σ: {baseline_sigma:.2f} → {nat_new:.2f}",
            fontsize=10,
            ha="center",
            transform=fig.transFigure,
        )
        ax.axis("off")

        out_path = temp_dir / f"frame_{pct:03d}.png"
        fig.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        frames.append(out_path)

    return frames


def assemble_gif(frame_paths: list[Path], output: Path, duration_ms: int) -> None:
    images = [Image.open(p) for p in frame_paths]
    if not images:
        raise ValueError("No frames to assemble into GIF.")
    output.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        output,
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=0,  # loop forever
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate unlock effect animation (GIF).")
    parser.add_argument("--start", type=int, default=0, help="Starting unlock percentage (default 0)")
    parser.add_argument("--end", type=int, default=40, help="Ending unlock percentage (default 40)")
    parser.add_argument("--step", type=int, default=10, help="Step size in percentage points (default 10)")
    parser.add_argument("--duration", type=int, default=1500, help="Frame duration in ms (default 1500)")
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUT),
        help="Output GIF path (default outputs/unlock_animation.gif)",
    )
    args = parser.parse_args()

    if args.step <= 0:
        raise ValueError("Step must be positive.")
    if args.end < args.start:
        raise ValueError("end must be >= start.")

    levels = list(range(args.start, args.end + 1, args.step))

    gdf = gpd.read_file(SHAPE_PATH).to_crs(epsg=4326)
    friction_df = load_friction()
    merged = prepare_dataframe(gdf, friction_df)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        frames = generate_frames(merged, levels, tmpdir_path)
        assemble_gif(frames, Path(args.output), args.duration)
        # Cleanup is automatic via TemporaryDirectory
    print(f"✓ GIF saved to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()

"""
Unlock Simulator (v0.1)

Goal
----
Given:
- baseline locked stock share σ per municipality
- friction factor F = 1 / (1 - σ)
- a price model P ∝ (D * F / S)^α

we simulate what happens to prices if a fraction u of locked stock is "unlocked"
(i.e. returned to the effective market).

Model
-----
Let:
- σ = locked stock share
- F = 1 / (1 - σ)
- u in [0, 1] = fraction of locked stock that is unlocked

Then:
- new locked share: σ' = σ * (1 - u)
- new friction: F' = 1 / (1 - σ')
- price ratio (holding D, S fixed): P_new / P_old = (F' / F)^α

We apply this per municipality and export the results.

Inputs
------
- friction_by_municipality.json (produced by compute_f_by_municipality.py)
- CLI parameters:
    --unlock-fraction u   (default: 0.20 → unlock 20% of locked homes)
    --alpha α             (default: 1.4)
    --min-sigma σ_min     (default: 0.25; only simulate “constrained” markets)

Outputs
-------
- outputs/unlock_simulation_municipalities.csv
- Console summary of top/bottom price drops.
"""

import argparse
import json
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
from fuzzywuzzy import fuzz, process
from matplotlib import colors as mcolors
from matplotlib.patches import Patch


def load_municipal_friction(path: Path) -> pd.DataFrame:
    """
    Load friction_by_municipality.json into a DataFrame.

    We try to be robust to two structures:
    1) Top-level list of dicts
    2) Top-level dict with a 'municipalities' list
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and "municipalities" in data:
        records = data["municipalities"]
    else:
        raise ValueError(
            f"Unsupported JSON structure in {path}. "
            "Expected a list or a dict with key 'municipalities'."
        )

    df = pd.DataFrame(records)

    rename_map = {}
    for col in df.columns:
        low = str(col).lower()
        if low in {"municipality", "dimos", "δήμος", "name"}:
            rename_map[col] = "Municipality"
        if low in {"sigma", "σ", "locked_share"}:
            rename_map[col] = "sigma"

    df = df.rename(columns=rename_map)

    if "Municipality" not in df.columns or "sigma" not in df.columns:
        raise ValueError(
            "Could not find 'Municipality' and 'sigma' columns after normalization. "
            f"Columns seen: {list(df.columns)}"
        )

    df["sigma"] = pd.to_numeric(df["sigma"], errors="coerce")

    return df


# --- name matching helpers (reuse overrides from choropleth scripts) ---
# These overrides say how specific Greek ELSTAT municipality names map
# onto the corresponding English GADM level‑3 names.
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
# Three-bucket archetype palette used for both baseline and simulated maps.
ARCT_COLORS = {
    "PROBLEMATIC": "#d62728",
    "TRANSITIONAL": "#ffbb33",
    "HEALTHY": "#2ca02c",
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
    import re
    return re.sub(r"[^a-z0-9]+", "", translit(str(text)).lower())


def build_index(names) -> dict:
    idx = {}
    for n in names:
        key = normalize(n)
        if key and key not in idx:
            idx[key] = n
    return idx


def match_names(targets, candidates):
    cand_keys = list(candidates.keys())
    out = {}
    for t in targets:
        key = normalize(t)
        if key in candidates:
            out[t] = candidates[key]
        else:
            best, _ = process.extractOne(key, cand_keys, scorer=fuzz.token_sort_ratio)
            out[t] = candidates[best]
    return out


def merge_with_shapes(df: pd.DataFrame, shp_path: Path) -> gpd.GeoDataFrame:
    """Attach simulation results to GADM level‑3 municipality polygons."""
    gdf = gpd.read_file(shp_path).to_crs(epsg=4326)
    gdf = gdf[gdf["NAME_3"] != "Athos"]

    # Override map Greek -> GADM English
    greek_to_gadm = {v: k for k, v in OVER_ONE.items()}
    idx_map = build_index(gdf["NAME_3"])

    df = df.copy()
    df["matched_name"] = df["Municipality"].map(greek_to_gadm)

    remaining = df["matched_name"].isna()
    matched_remaining = match_names(df.loc[remaining, "Municipality"], idx_map)
    df.loc[remaining, "matched_name"] = df.loc[remaining, "Municipality"].map(matched_remaining)

    merged = gdf.merge(df, left_on="NAME_3", right_on="matched_name", how="left")
    return merged


def compute_friction(sigma: pd.Series) -> pd.Series:
    """F = 1 / (1 - σ). Guard against σ >= 1."""
    eps = 1e-9
    return 1.0 / (1.0 - sigma.clip(upper=1 - eps))


def simulate_unlock(
    df: pd.DataFrame,
    unlock_fraction: float,
    alpha: float,
    min_sigma: float,
) -> pd.DataFrame:
    """
    Core simulation logic.

    Parameters
    ----------
    df : DataFrame with at least columns:
        - Municipality
        - sigma (locked share)
    unlock_fraction : float in [0, 1]
        Fraction of locked stock that is unlocked.
    alpha : float
        Elasticity parameter in the price model.
    min_sigma : float
        Only simulate municipalities with σ >= min_sigma (others kept but effect ~0).

    Returns
    -------
    DataFrame with added columns:
        - F_baseline
        - sigma_new
        - F_new
        - price_ratio (P_new / P_old)
        - price_change_pct
    """
    res = df.copy()

    # Compute tourism share if present (used only for archetype labelling).
    if {"vacation", "secondary", "s_total"}.issubset(res.columns):
        res["share_tourism"] = (pd.to_numeric(res["vacation"], errors="coerce") + pd.to_numeric(res["secondary"], errors="coerce")) / pd.to_numeric(res["s_total"], errors="coerce")
    else:
        res["share_tourism"] = pd.NA

    res["F_baseline"] = compute_friction(res["sigma"])

    # Apply unlock to all municipalities as a proportional reduction
    # of the locked share σ (percentage reduction, not percentage points).
    res["sigma_new"] = res["sigma"] * (1.0 - unlock_fraction)

    res["F_new"] = compute_friction(res["sigma_new"])

    ratio = (res["F_new"] / res["F_baseline"]).pow(alpha)
    res["price_ratio"] = ratio
    res["price_change_pct"] = (ratio - 1.0) * 100.0

    # Archetypes (baseline and simulated) — three-bucket view
    # PROBLEMATIC / TRANSITIONAL / HEALTHY, based only on σ.
    def classify(sig, tour):
        sig = float(sig)
        # Problematic: high σ, regardless of tourism mix
        if sig > 0.5:
            return "PROBLEMATIC"
        if 0.25 <= sig <= 0.5:
            return "TRANSITIONAL"
        return "HEALTHY"

    res["archetype_base"] = res.apply(lambda r: classify(r["sigma"], r["share_tourism"]), axis=1)
    res["archetype_sim"] = res.apply(lambda r: classify(r["sigma_new"], r["share_tourism"]), axis=1)
    labels = list(ARCT_COLORS.keys())
    code_map = {label: idx for idx, label in enumerate(labels)}
    res["arc_code_base"] = res["archetype_base"].map(code_map)
    res["arc_code_sim"] = res["archetype_sim"].map(code_map)

    return res


def print_summary(df: pd.DataFrame, unlock_fraction: float, alpha: float, min_sigma: float) -> None:
    """Print a small human-readable summary of the scenario and results."""
    print("=" * 100)
    print("UNLOCK SIMULATOR — Housing Friction")
    print("=" * 100)
    print(f"Unlock fraction (u):       {unlock_fraction:.2%}")
    print(f"Elasticity (alpha):        {alpha:.2f}")
    print(f"Min σ simulated:           {min_sigma:.2f}")
    print()

    constrained = df[df["sigma"] >= min_sigma]
    if not constrained.empty:
        avg_sigma = constrained["sigma"].mean()
        avg_sigma_new = constrained["sigma_new"].mean()
        avg_price_change = constrained["price_change_pct"].mean()

        print("Average over constrained municipalities (σ >= min_sigma):")
        print(f"- Baseline σ:             {avg_sigma:.3f}")
        print(f"- New σ:                  {avg_sigma_new:.3f}")
        print(f"- Avg price change:       {avg_price_change:.2f}%")
        print()

    top = df.sort_values("price_change_pct").head(10)
    print("Top 10 municipalities by price drop (most negative price_change_pct):")
    print(
        top[["Municipality", "sigma", "sigma_new", "price_change_pct"]]
        .to_string(index=False, formatters={"price_change_pct": "{:.2f}%".format})
    )
    print()

    worst = df.sort_values("price_change_pct", ascending=False).head(5)
    if (worst["price_change_pct"] > 0).any():
        print("Municipalities with smallest or positive improvements (edge cases):")
        print(
            worst[["Municipality", "sigma", "sigma_new", "price_change_pct"]]
            .to_string(index=False, formatters={"price_change_pct": "{:.2f}%".format})
        )
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate impact of unlocking part of locked housing stock on prices."
    )
    parser.add_argument(
        "--input-json",
        type=str,
        default="outputs/friction_by_municipality.json",
        help="Path to friction_by_municipality.json",
    )
    parser.add_argument(
        "--unlock-fraction",
        type=float,
        default=0.20,
        help="Fraction of locked stock to unlock (0.20 = 20%% of σ).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.4,
        help="Price elasticity parameter α in P ∝ (D * F / S)^α.",
    )
    parser.add_argument(
        "--min-sigma",
        type=float,
        default=0.0,
        help="Only used for reporting summaries; unlock applies everywhere regardless of this value.",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="outputs/unlock_simulation_municipalities.csv",
        help="Where to write simulation results.",
    )

    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Load baseline friction + dwelling counts per municipality.
    df = load_municipal_friction(input_path)
    # 2) Run unlock simulation.
    sim = simulate_unlock(
        df=df,
        unlock_fraction=args.unlock_fraction,
        alpha=args.alpha,
        min_sigma=args.min_sigma,
    )

    # 3) Persist full simulation table.
    sim.to_csv(output_path, index=False)
    print(f"✓ Simulation results written to: {output_path.resolve()}")

    # Plot collage
    # ------------------------------------------------------------------
    # Build a 3x2 figure:
    #   Row 1: simulated σ map, price‑change map
    #   Row 2: major‑city price drops, top‑10 price drops
    #   Row 3: baseline archetype map, simulated archetype map
    collage_path = output_path.parent / "unlock_effect_collage.png"
    try:
        # Prepare map data for simulated metrics
        shp_path = Path("data/geo/gadm41_GRC_3.shp")
        merged = merge_with_shapes(sim, shp_path)
        arc_counts_sim = merged["archetype_sim"].value_counts().to_dict()
        arc_counts_base = merged["archetype_base"].value_counts().to_dict()

        fig, axes = plt.subplots(3, 2, figsize=(14, 16))

        # Panel 1: map (σ_new choropleth)
        cmap_sigma = "RdYlGn_r"  # green = low sigma, red = high sigma
        g1 = merged.plot(column="sigma_new", cmap=cmap_sigma, linewidth=0.1, edgecolor="black", ax=axes[0, 0])
        axes[0, 0].set_title("Simulated σ (after unlock)")
        axes[0, 0].axis("off")
        sm1 = plt.cm.ScalarMappable(
            cmap=cmap_sigma,
            norm=mcolors.Normalize(
                vmin=merged["sigma_new"].min(skipna=True),
                vmax=merged["sigma_new"].max(skipna=True),
            ),
        )
        sm1.set_array([])
        fig.colorbar(sm1, ax=axes[0, 0], fraction=0.03, pad=0.02, label="σ (after unlock)")

        # Panel 2: map (price change %)
        # Swap so higher price change = deeper green, lower = white
        cmap_price = mcolors.LinearSegmentedColormap.from_list("white_to_green", ["#2ca02c", "#ffffff"])
        g2 = merged.plot(column="price_change_pct", cmap=cmap_price, linewidth=0.1, edgecolor="black", ax=axes[0, 1])
        axes[0, 1].set_title("Price change (%)")
        axes[0, 1].axis("off")
        sm2 = plt.cm.ScalarMappable(
            cmap=cmap_price,
            norm=mcolors.Normalize(
                vmin=merged["price_change_pct"].min(skipna=True),
                vmax=merged["price_change_pct"].max(skipna=True),
            ),
        )
        sm2.set_array([])
        fig.colorbar(sm2, ax=axes[0, 1], fraction=0.03, pad=0.02, label="Price change (%)")

        # Panel 3: major cities price drop (robust matching on variants)
        targets = {
            "ΑΘΗΝΑΙΩΝ": ["ΑΘΗΝΑΙΩΝ"],
            "ΘΕΣΣΑΛΟΝΙΚΗΣ": ["ΘΕΣΣΑΛΟΝΙΚΗΣ"],
            "ΠΕΙΡΑΙΩΣ": ["ΠΕΙΡΑΙΩΣ", "ΠΕΙΡΑΙΑΣ"],
            "ΠΑΤΡΕΩΝ": ["ΠΑΤΡΕΩΝ", "ΠΑΤΡΑΣ"],
            "ΗΡΑΚΛΕΙΟΥ": ["ΗΡΑΚΛΕΙΟΥ"],
            "ΛΑΡΙΣΑΙΩΝ": ["ΛΑΡΙΣΑΙΩΝ", "ΛΑΡΙΣΑΣ"],
        }
        norm_map = {}
        for n in sim["Municipality"]:
            key = normalize(n)
            if key and key not in norm_map:
                norm_map[key] = n
        major_rows = []
        for _, variants in targets.items():
            found = None
            for v in variants:
                key = normalize(v)
                if key in norm_map:
                    found = norm_map[key]
                    break
            if found:
                major_rows.append(sim[sim["Municipality"] == found].iloc[0])
        if major_rows:
            majors = pd.DataFrame(major_rows).sort_values("price_change_pct")
            majors["drop_mag"] = (-majors["price_change_pct"]).clip(lower=0)
            axes[1, 0].barh(majors["Municipality"], majors["drop_mag"], color="#2ca02c", alpha=0.85)
            axes[1, 0].set_title("Major cities — price drop (%)")
            axes[1, 0].set_xlabel("Price drop magnitude (%)")
            axes[1, 0].invert_yaxis()
            for _, row in majors.iterrows():
                axes[1, 0].text(row["drop_mag"] + 0.05, row["Municipality"], f"{row['price_change_pct']:.2f}%", va="center", fontsize=8)
        else:
            axes[1, 0].text(0.5, 0.5, "Major cities not found", ha="center", va="center")
            axes[1, 0].axis("off")

        # Panel 4: top 10 price drops
        top10 = sim.sort_values("price_change_pct").head(10)
        axes[1, 1].barh(top10["Municipality"], top10["price_change_pct"], color="#2ca02c", alpha=0.85)
        axes[1, 1].set_title("Top 10 price drops")
        axes[1, 1].set_xlabel("Price change (%)")
        axes[1, 1].invert_yaxis()

        # Panel 5: baseline archetypes choropleth
        labels_arc = list(ARCT_COLORS.keys())
        cmap_arc = mcolors.ListedColormap([ARCT_COLORS[l] for l in labels_arc])
        norm_arc = mcolors.BoundaryNorm(range(len(labels_arc) + 1), cmap_arc.N)
        merged.plot(column="arc_code_base", cmap=cmap_arc, norm=norm_arc, linewidth=0.1, edgecolor="black", ax=axes[2, 0])
        axes[2, 0].set_title("Baseline Housing Archetypes")
        axes[2, 0].axis("off")
        handles_arc_base = [
            Patch(color=ARCT_COLORS[label], label=f"{label.replace('_', ' ').title()} ({arc_counts_base.get(label, 0)})")
            for label in labels_arc
        ]
        axes[2, 0].legend(handles=handles_arc_base, title="Archetype (baseline)", loc="lower left")

        # Panel 6: simulated archetypes choropleth
        merged.plot(column="arc_code_sim", cmap=cmap_arc, norm=norm_arc, linewidth=0.1, edgecolor="black", ax=axes[2, 1])
        axes[2, 1].set_title("Simulated Housing Archetypes (after unlock)")
        axes[2, 1].axis("off")
        handles_arc = [
            Patch(color=ARCT_COLORS[label], label=f"{label.replace('_', ' ').title()} ({arc_counts_sim.get(label, 0)})")
            for label in labels_arc
        ]
        axes[2, 1].legend(handles=handles_arc, title="Archetype (simulated)", loc="lower left")

        plt.tight_layout()
        fig.savefig(collage_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"✓ Collage saved to: {collage_path.resolve()}")
    except Exception as exc:  # pragma: no cover
        print(f"Warning: failed to create collage ({exc})")

    print_summary(
        sim,
        unlock_fraction=args.unlock_fraction,
        alpha=args.alpha,
        min_sigma=args.min_sigma,
    )


if __name__ == "__main__":
    main()

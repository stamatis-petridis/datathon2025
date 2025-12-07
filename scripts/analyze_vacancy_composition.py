from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd


DATA_ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = DATA_ROOT / "outputs" / "friction_by_municipality.json"
CSV_OUT = DATA_ROOT / "outputs" / "municipal_archetypes.csv"
SUMMARY_OUT = DATA_ROOT / "outputs" / "archetype_summary.json"
CHART_TOP20 = DATA_ROOT / "outputs" / "top20_sigma_composition.png"
CHART_CITIES = DATA_ROOT / "outputs" / "major_cities_composition.png"


def _norm(text: str) -> str:
    """Normalize Greek text by removing accents and lowercasing."""
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return without_accents.lower()


def classify_row(row: pd.Series) -> str:
    sigma = row["sigma"]
    if sigma < 0.10:
        return "EU_EFFICIENT"
    if sigma < 0.15:
        return "EU_NORMAL"
    if sigma < 0.20:
        return "MEDITERRANEAN_ACCEPTABLE"
    if sigma < 0.30:
        return "ELEVATED_FRICTION"
    if sigma < 0.50:
        return "STRUCTURAL_DYSFUNCTION"
    return "MARKET_COLLAPSE"


def load_data() -> pd.DataFrame:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"Missing data file: {JSON_PATH}")
    data = json.loads(JSON_PATH.read_text())
    muni = data.get("municipalities", [])
    df = pd.DataFrame(muni)
    required = {"name", "sigma", "s_total", "for_rent", "for_sale", "vacation", "secondary", "other_reason"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing expected fields in JSON: {missing}")
    # shares
    df["s_total"] = pd.to_numeric(df["s_total"], errors="coerce")
    for col in ["for_rent", "for_sale", "vacation", "secondary", "other_reason", "sigma"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df["s_total"] > 0].copy()
    df["share_market"] = (df["for_rent"] + df["for_sale"]) / df["s_total"]
    df["share_tourism"] = (df["vacation"] + df["secondary"]) / df["s_total"]
    df["share_system_failure"] = df["other_reason"] / df["s_total"]
    df["archetype"] = df.apply(classify_row, axis=1)
    return df


def summarize(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for archetype, group in df.groupby("archetype"):
        summary[archetype] = {
            "count": int(len(group)),
            "avg_sigma": float(group["sigma"].mean()),
            "avg_share_tourism": float(group["share_tourism"].mean()),
            "avg_share_market": float(group["share_market"].mean()),
            "avg_share_system_failure": float(group["share_system_failure"].mean()),
        }
    summary["total"] = {"count": int(len(df))}
    return summary


def print_summary(summary: Dict[str, Dict[str, float]]) -> None:
    print("Archetype summary (EU benchmarks):")
    print(f"{'Archetype':28s} {'Count':>6s} {'Avg σ':>8s} {'Avg tourism':>12s}")
    for archetype, stats in summary.items():
        if archetype == "total":
            continue
        print(
            f"{archetype:28s} "
            f"{stats['count']:6d} "
            f"{stats['avg_sigma']:8.3f} "
            f"{stats['avg_share_tourism']:12.3f}"
        )
    print(f"Total municipalities: {summary['total']['count']}")


def stacked_bar(df: pd.DataFrame, labels: List[str], path: Path, title: str) -> None:
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = pd.Series([0] * len(df), index=df.index)
    parts = [
        ("share_market", "#8c8c8c", "Market (rent/sale)"),
        ("share_tourism", "#f4a261", "Tourism (vacation/secondary)"),
        ("share_system_failure", "#2a9d8f", "System failure"),
    ]
    for col, color, label in parts:
        ax.bar(labels, df[col], bottom=bottom, color=color, label=label)
        bottom += df[col]
    ax.set_ylabel("Share of total dwellings")
    ax.set_title(title)
    ax.set_ylim(0, 1)
    ax.legend()
    ax.tick_params(axis="x", labelrotation=45)
    for tick in ax.get_xticklabels():
        tick.set_horizontalalignment("right")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def select_major_cities(df: pd.DataFrame) -> pd.DataFrame:
    # Map provided names to JSON names (upper-case Greek in data)
    targets = {
        "Αθήνα": "ΑΘΗΝΑΙΩΝ",
        "Θεσσαλονίκη": "ΘΕΣΣΑΛΟΝΙΚΗΣ",
        "Πειραιάς": "ΠΕΙΡΑΙΩΣ",
        "Πάτρα": "ΠΑΤΡΕΩΝ",
        "Ηράκλειο": "ΗΡΑΚΛΕΙΟΥ",
        "Λάρισα": "ΛΑΡΙΣΑΙΩΝ",
    }
    # fallback normalization
    name_map = {n: n for n in df["name"]}
    norm_map = {_norm(n): n for n in df["name"]}
    rows = []
    for label, greek in targets.items():
        match = name_map.get(greek) or norm_map.get(_norm(greek))
        if match and match in df["name"].values:
            rows.append(df[df["name"] == match].iloc[0])
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def main() -> None:
    df = load_data()

    # Save CSV
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_OUT, index=False)

    # Summary
    summary = summarize(df)
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print_summary(summary)

    # Charts
    top20 = df.sort_values("sigma", ascending=False).head(20)
    stacked_bar(
        top20,
        top20["name"].tolist(),
        CHART_TOP20,
        "Top 20 municipalities by σ — vacancy composition",
    )

    cities_df = select_major_cities(df)
    if not cities_df.empty:
        stacked_bar(
            cities_df,
            cities_df["name"].tolist(),
            CHART_CITIES,
            "Major cities — vacancy composition",
        )
    else:
        print("Warning: major cities not found in dataset.")


if __name__ == "__main__":
    main()

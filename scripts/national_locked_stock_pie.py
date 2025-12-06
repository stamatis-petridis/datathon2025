from __future__ import annotations

"""
National locked stock composition — pie chart.

This script:
- loads outputs/friction_by_municipality.json
- aggregates empty dwellings by reason:
  * for rent
  * for sale
  * vacation + secondary homes
  * other empty/locked
- produces a national-level pie chart matching the report snapshot:
  outputs/national_locked_stock_pie.png
"""

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


DATA_ROOT = Path(__file__).resolve().parents[1]
FRICTION_JSON = DATA_ROOT / "outputs" / "friction_by_municipality.json"
OUT_PNG = DATA_ROOT / "outputs" / "national_locked_stock_pie.png"


def load_aggregate() -> dict:
    """Aggregate empty dwellings by reason over all municipalities."""
    if not FRICTION_JSON.exists():
        raise FileNotFoundError(f"Missing friction JSON: {FRICTION_JSON}")

    data = json.loads(FRICTION_JSON.read_text(encoding="utf-8"))
    muni = data.get("municipalities", [])
    if not muni:
        raise ValueError("No 'municipalities' records found in friction JSON.")

    agg = Counter()
    for r in muni:
        for key in ["s_total", "s_empty", "for_rent", "for_sale", "vacation", "secondary", "other_reason"]:
            if key in r:
                agg[key] += r[key]

    # Derived categories
    rent = agg.get("for_rent", 0)
    sale = agg.get("for_sale", 0)
    vac_sec = agg.get("vacation", 0) + agg.get("secondary", 0)
    other = agg.get("other_reason", 0)

    return {
        "s_total": agg.get("s_total", 0),
        "s_empty": agg.get("s_empty", 0),
        "for_rent": rent,
        "for_sale": sale,
        "vacation_secondary": vac_sec,
        "other": other,
    }


def plot_pie(stats: dict) -> None:
    """Create and save the national locked-stock composition pie chart."""
    labels = [
        "Empty for rent",
        "Empty for sale",
        "Vacation / secondary homes",
        "Other empty / locked",
    ]
    values = [
        stats["for_rent"],
        stats["for_sale"],
        stats["vacation_secondary"],
        stats["other"],
    ]

    total_empty = sum(values)
    if total_empty <= 0:
        raise ValueError("Total empty dwellings is zero; cannot plot pie chart.")

    fig, ax = plt.subplots(figsize=(6, 6))

    # First draw pie without external labels; we'll place lock-type + numbers inside each wedge
    wedges, _texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
        wedgeprops={"linewidth": 0.5, "edgecolor": "white"},
        textprops={"fontsize": 8, "color": "white"},
    )

    # Replace default autopct text with lock type + percent + count inside the slice
    for i, (wedge, autotext) in enumerate(zip(wedges, autotexts)):
        label = labels[i]
        val = values[i]
        pct = 100.0 * val / total_empty
        autotext.set_text(f"{label}\n{pct:.1f}%\n({val:,d})")
        autotext.set_color("black")
        autotext.set_fontsize(10)

    ax.set_title("National Locked-Stock Composition — Greece 2021", fontsize=12, weight="bold")
    ax.axis("equal")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=300)
    plt.close(fig)
    print(f"✓ Pie chart saved to: {OUT_PNG.resolve()}")


def main() -> None:
    stats = load_aggregate()
    plot_pie(stats)


if __name__ == "__main__":
    main()

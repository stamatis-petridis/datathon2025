"""
Export an unlocked friction JSON for a given unlock percentage.

Usage:
    python scripts/export_unlock_json.py --unlock-pct 12.5 \
        --output outputs/friction_by_municipality_unlocked_12.5.json

What it does:
- loads outputs/friction_by_municipality.json
- applies a proportional reduction to locked stock:
      s_empty_new = s_empty * (1 - unlock_pct/100)
      sigma_new   = s_empty_new / s_total
      F_new       = 1 / (1 - sigma_new)
- writes a JSON with updated per-municipality fields plus national totals.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DATA_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = DATA_ROOT / "outputs" / "friction_by_municipality.json"


def load_friction(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing friction file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def apply_unlock(data: dict, unlock_pct: float) -> dict:
    """Apply proportional unlock to every municipality and recompute national totals."""
    factor = 1.0 - unlock_pct / 100.0

    muni = data.get("municipalities", data if isinstance(data, list) else [])
    if not muni:
        raise ValueError("No municipality records found in input JSON.")

    out_muni = []
    national_tot_s = 0.0
    national_tot_empty = 0.0

    for rec in muni:
        s_total = float(rec.get("s_total", 0))
        s_empty = float(rec.get("s_empty", 0))
        sigma = float(rec.get("sigma", 0))

        s_empty_new = s_empty * factor
        sigma_new = s_empty_new / s_total if s_total > 0 else 0.0
        F_new = 1.0 / (1.0 - sigma_new) if sigma_new < 1 else float("inf")
        F_old = rec.get("F", 1.0)
        price_ratio = (F_new / F_old) if F_old and F_old != 0 else 1.0
        price_change_pct = (price_ratio - 1.0) * 100.0

        national_tot_s += s_total
        national_tot_empty += s_empty_new

        rec_out = dict(rec)
        rec_out["s_empty_unlocked"] = s_empty_new
        rec_out["sigma_unlocked"] = sigma_new
        rec_out["F_unlocked"] = F_new
        rec_out["price_change_pct_unlocked"] = price_change_pct
        out_muni.append(rec_out)

    sigma_nat = national_tot_empty / national_tot_s if national_tot_s > 0 else 0.0
    F_nat = 1.0 / (1.0 - sigma_nat) if sigma_nat < 1 else float("inf")
    price_ratio_nat = (F_nat / data.get("national", {}).get("F", 1.0)) if data.get("national", {}) else 1.0
    price_change_nat = (price_ratio_nat - 1.0) * 100.0

    return {
        "unlock_pct": unlock_pct,
        "national": {
            "s_total": national_tot_s,
            "s_empty_unlocked": national_tot_empty,
            "sigma_unlocked": sigma_nat,
            "F_unlocked": F_nat,
            "price_change_pct_unlocked": price_change_nat,
        },
        "municipalities": out_muni,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export unlocked friction JSON for a given unlock percentage.")
    parser.add_argument("--input", type=str, default=str(DEFAULT_IN), help="Path to friction_by_municipality.json")
    parser.add_argument("--unlock-pct", type=float, required=True, help="Unlock percentage (e.g., 12.5 for 12.5%)")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON path (default: outputs/friction_by_municipality_unlocked_<pct>.json)",
    )
    args = parser.parse_args()

    if args.unlock_pct < 0 or args.unlock_pct > 100:
        raise ValueError("unlock-pct must be between 0 and 100.")

    input_path = Path(args.input)
    data = load_friction(input_path)
    unlocked = apply_unlock(data, args.unlock_pct)

    # Default output path if not provided
    if args.output is None:
        out_name = f"friction_by_municipality_unlocked_{args.unlock_pct:.1f}.json"
        output_path = DATA_ROOT / "outputs" / out_name
    else:
        output_path = Path(args.output)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(unlocked, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Unlocked JSON saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()

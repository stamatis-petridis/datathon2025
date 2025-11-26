"""
Compute friction factor F_v0 for each Περιφέρεια (Region).
Level 3 in the ELSTAT hierarchy.

Output: Table + JSON for visualization.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def compute_f_by_region(path: str) -> pd.DataFrame:
    """Extract σ and F for each Region (Level 3)."""
    
    # Read CSV (cleaner than xlsx for this)
    df = pd.read_csv(path, header=None, encoding='utf-8')
    
    # Find data start (after header rows)
    # Header is at row 3, data starts at row 7 (0-indexed)
    data = df.iloc[7:].copy()
    data.columns = [
        'level', 'code', 'name', 
        's_total', 'total_with_bath', 'bath_inside', 'bath_outside', 'no_bath',
        's_occupied', 'occ_with_bath', 'occ_bath_inside', 'occ_bath_outside', 'occ_no_bath',
        's_empty', 'empty_with_bath', 'empty_bath_inside', 'empty_bath_outside', 'empty_no_bath'
    ]
    
    # Convert numeric columns
    for col in ['level', 'code', 's_total', 's_occupied', 's_empty']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # Filter to Level 3 (Περιφέρεια) and main rows only
    # Main rows have the region name, not "Διαθεσιμότητα δικτύου..."
    regions = data[
        (data['level'] == 3) & 
        (data['name'].str.contains('ΠΕΡΙΦΕΡΕΙΑ', na=False))
    ].copy()
    
    # Calculate σ and F
    regions['sigma'] = regions['s_empty'] / regions['s_total']
    regions['F'] = 1 / (1 - regions['sigma'])
    
    # Clean up names
    regions['name'] = regions['name'].str.replace('ΠΕΡΙΦΕΡΕΙΑ ', '', regex=False)
    
    # Select output columns
    result = regions[['code', 'name', 's_total', 's_occupied', 's_empty', 'sigma', 'F']].copy()
    result = result.sort_values('sigma', ascending=False).reset_index(drop=True)
    
    return result


def main():
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data" / "elstat"
    
    # Try CSV first, fall back to xlsx
    csv_path = data_dir / "csv" / "A05_dwellings_status_pe_2021.csv"
    xlsx_path = data_dir / "A05_dwellings_status_pe_2021.xlsx"
    
    if csv_path.exists():
        path = str(csv_path)
    elif xlsx_path.exists():
        # For xlsx, convert to csv-like structure
        print("Using xlsx file...", file=sys.stderr)
        path = str(xlsx_path)
    else:
        print(f"Data file not found in {data_dir}", file=sys.stderr)
        sys.exit(1)
    
    result = compute_f_by_region(path)
    
    # Print table
    print("=" * 90)
    print("FRICTION FACTOR BY ΠΕΡΙΦΕΡΕΙΑ (Region) — Ranked by σ (highest first)")
    print("=" * 90)
    print(f"\n{'Rank':<5} {'Region':<45} {'S_total':>12} {'S_empty':>12} {'σ':>8} {'F':>8}")
    print("-" * 90)
    
    for i, row in result.iterrows():
        print(f"{i+1:<5} {row['name']:<45} {int(row['s_total']):>12,} {int(row['s_empty']):>12,} {row['sigma']:>8.3f} {row['F']:>8.3f}")
    
    # National totals
    print("-" * 90)
    s_total_nat = result['s_total'].sum()
    s_empty_nat = result['s_empty'].sum()
    sigma_nat = s_empty_nat / s_total_nat
    f_nat = 1 / (1 - sigma_nat)
    print(f"{'NAT':<5} {'ΣΥΝΟΛΟ ΧΩΡΑΣ':<45} {int(s_total_nat):>12,} {int(s_empty_nat):>12,} {sigma_nat:>8.3f} {f_nat:>8.3f}")
    
    # Save to JSON for visualization
    output_dir = script_dir.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    json_data = {
        "level": "Περιφέρεια",
        "level_code": 3,
        "computed_at": pd.Timestamp.now().isoformat(),
        "national": {
            "s_total": int(s_total_nat),
            "s_empty": int(s_empty_nat),
            "sigma": round(sigma_nat, 4),
            "F": round(f_nat, 4)
        },
        "regions": [
            {
                "code": int(row['code']),
                "name": row['name'],
                "s_total": int(row['s_total']),
                "s_empty": int(row['s_empty']),
                "sigma": round(row['sigma'], 4),
                "F": round(row['F'], 4)
            }
            for _, row in result.iterrows()
        ]
    }
    
    json_path = output_dir / "friction_by_region.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ JSON saved to: {json_path}")


if __name__ == "__main__":
    main()

"""
Compute friction factor F_v0 for each Δήμος (Municipality).
Level 5 in the ELSTAT hierarchy. ~332 municipalities.

Uses G01 file which has full geographic hierarchy down to settlement level.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def compute_f_by_municipality(path: str) -> pd.DataFrame:
    """Extract σ and F for each Municipality (Level 5)."""
    
    df = pd.read_csv(path, header=None, encoding='utf-8')
    
    # Data starts at row 6 (0-indexed), after headers
    data = df.iloc[6:].copy()
    data.columns = [
        'level', 'code', 'name', 
        'total_all', 's_total', 's_occupied', 's_empty',
        'for_rent', 'for_sale', 'vacation', 'secondary', 'other_reason',
        'non_normal'
    ]
    
    # Convert numeric columns
    for col in ['level', 'code', 's_total', 's_occupied', 's_empty', 
                'for_rent', 'for_sale', 'vacation', 'secondary', 'other_reason']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # Filter to Level 5 (Δήμος) 
    municipalities = data[data['level'] == 5].copy()
    
    # Calculate σ and F
    municipalities['sigma'] = municipalities['s_empty'] / municipalities['s_total']
    municipalities['F'] = 1 / (1 - municipalities['sigma'])
    
    # Calculate "true locked" (other_reason = not for rent/sale/vacation/secondary)
    municipalities['true_locked'] = municipalities['other_reason']
    municipalities['true_locked_pct'] = municipalities['true_locked'] / municipalities['s_total']
    
    # Clean up names
    municipalities['name'] = municipalities['name'].str.replace('ΔΗΜΟΣ ', '', regex=False)
    
    # Select output columns
    result = municipalities[[
        'code', 'name', 's_total', 's_occupied', 's_empty', 
        'for_rent', 'for_sale', 'vacation', 'secondary', 'other_reason',
        'sigma', 'F', 'true_locked_pct'
    ]].copy()
    result = result.sort_values('sigma', ascending=False).reset_index(drop=True)
    
    return result


def main():
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data" / "elstat"
    
    csv_path = data_dir / "csv" / "G01_dwellings_status_oikismoi_2021.csv"
    
    if not csv_path.exists():
        print(f"Data file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    result = compute_f_by_municipality(str(csv_path))
    
    # Print table
    print("=" * 120)
    print("FRICTION FACTOR BY ΔΗΜΟΣ (Municipality) — Ranked by σ (highest first)")
    print("=" * 120)
    print(f"\n{'Rank':<5} {'Municipality':<35} {'S_total':>10} {'S_empty':>10} {'σ':>7} {'F':>7} {'Vacation':>10} {'TrueLock%':>10}")
    print("-" * 120)
    
    # Top 30
    for i, row in result.head(30).iterrows():
        print(f"{i+1:<5} {row['name'][:33]:<35} {int(row['s_total']):>10,} {int(row['s_empty']):>10,} {row['sigma']:>7.3f} {row['F']:>7.2f} {int(row['vacation']):>10,} {row['true_locked_pct']:>10.3f}")
    
    print(f"\n... (showing top 30 of {len(result)} municipalities)")
    
    # Bottom 10 (healthiest markets)
    print("\n" + "=" * 120)
    print("HEALTHIEST MARKETS (lowest σ)")
    print("=" * 120)
    print(f"\n{'Rank':<5} {'Municipality':<35} {'S_total':>10} {'S_empty':>10} {'σ':>7} {'F':>7}")
    print("-" * 120)
    
    bottom = result.tail(10).iloc[::-1]  # Reverse to show lowest first
    for i, (_, row) in enumerate(bottom.iterrows()):
        print(f"{len(result)-9+i:<5} {row['name'][:33]:<35} {int(row['s_total']):>10,} {int(row['s_empty']):>10,} {row['sigma']:>7.3f} {row['F']:>7.2f}")
    
    # Athens municipalities breakdown
    print("\n" + "=" * 120)
    print("MAJOR CITIES COMPARISON")
    print("=" * 120)
    
    major_cities = ['ΑΘΗΝΑΙΩΝ', 'ΘΕΣΣΑΛΟΝΙΚΗΣ', 'ΠΕΙΡΑΙΩΣ', 'ΠΑΤΡΕΩΝ', 'ΗΡΑΚΛΕΙΟΥ', 'ΛΑΡΙΣΑΙΩΝ']
    
    print(f"\n{'Municipality':<35} {'S_total':>10} {'S_empty':>10} {'σ':>7} {'F':>7} {'ForRent':>10} {'Vacation':>10} {'TrueLock':>10}")
    print("-" * 120)
    
    for city in major_cities:
        city_row = result[result['name'] == city]
        if not city_row.empty:
            row = city_row.iloc[0]
            print(f"{row['name']:<35} {int(row['s_total']):>10,} {int(row['s_empty']):>10,} {row['sigma']:>7.3f} {row['F']:>7.2f} {int(row['for_rent']):>10,} {int(row['vacation']):>10,} {int(row['other_reason']):>10,}")
    
    # National totals
    print("\n" + "-" * 120)
    s_total_nat = result['s_total'].sum()
    s_empty_nat = result['s_empty'].sum()
    sigma_nat = s_empty_nat / s_total_nat
    f_nat = 1 / (1 - sigma_nat)
    print(f"{'ΣΥΝΟΛΟ ΧΩΡΑΣ':<35} {int(s_total_nat):>10,} {int(s_empty_nat):>10,} {sigma_nat:>7.3f} {f_nat:>7.2f}")
    
    # Save to JSON
    output_dir = script_dir.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    json_data = {
        "level": "Δήμος",
        "level_code": 5,
        "computed_at": pd.Timestamp.now().isoformat(),
        "national": {
            "s_total": int(s_total_nat),
            "s_empty": int(s_empty_nat),
            "sigma": round(sigma_nat, 4),
            "F": round(f_nat, 4)
        },
        "municipalities": [
            {
                "code": int(row['code']),
                "name": row['name'],
                "s_total": int(row['s_total']),
                "s_empty": int(row['s_empty']),
                "for_rent": int(row['for_rent']),
                "for_sale": int(row['for_sale']),
                "vacation": int(row['vacation']),
                "secondary": int(row['secondary']),
                "other_reason": int(row['other_reason']),
                "sigma": round(row['sigma'], 4),
                "F": round(row['F'], 4),
                "true_locked_pct": round(row['true_locked_pct'], 4)
            }
            for _, row in result.iterrows()
        ]
    }
    
    json_path = output_dir / "friction_by_municipality.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ JSON saved to: {json_path}")
    print(f"✓ Total Municipalities: {len(result)}")


if __name__ == "__main__":
    main()

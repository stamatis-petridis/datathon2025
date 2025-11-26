"""
Compute friction factor F_v0 for each Περιφερειακή Ενότητα (Regional Unit).
Level 4 in the ELSTAT hierarchy. ~74 units.

Output: Table + JSON for visualization.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def compute_f_by_pe(path: str) -> pd.DataFrame:
    """Extract σ and F for each Regional Unit (Level 4)."""
    
    df = pd.read_csv(path, header=None, encoding='utf-8')
    
    # Data starts at row 7 (0-indexed)
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
    
    # Filter to Level 4 (Περιφερειακή Ενότητα) and main rows only
    pe = data[
        (data['level'] == 4) & 
        (data['name'].str.contains('ΠΕΡΙΦΕΡΕΙΑΚΗ ΕΝΟΤΗΤΑ', na=False))
    ].copy()
    
    # Calculate σ and F
    pe['sigma'] = pe['s_empty'] / pe['s_total']
    pe['F'] = 1 / (1 - pe['sigma'])
    
    # Clean up names
    pe['name'] = pe['name'].str.replace('ΠΕΡΙΦΕΡΕΙΑΚΗ ΕΝΟΤΗΤΑ ', '', regex=False)
    
    # Select output columns
    result = pe[['code', 'name', 's_total', 's_occupied', 's_empty', 'sigma', 'F']].copy()
    result = result.sort_values('sigma', ascending=False).reset_index(drop=True)
    
    return result


def main():
    script_dir = Path(__file__).resolve().parent
    data_dir = script_dir.parent / "data" / "elstat"
    
    csv_path = data_dir / "csv" / "A05_dwellings_status_pe_2021.csv"
    
    if not csv_path.exists():
        print(f"Data file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    result = compute_f_by_pe(str(csv_path))
    
    # Print table
    print("=" * 100)
    print("FRICTION FACTOR BY ΠΕΡΙΦΕΡΕΙΑΚΗ ΕΝΟΤΗΤΑ (Regional Unit) — Ranked by σ (highest first)")
    print("=" * 100)
    print(f"\n{'Rank':<5} {'Regional Unit':<40} {'S_total':>12} {'S_empty':>12} {'σ':>8} {'F':>8}")
    print("-" * 100)
    
    # Top 20
    for i, row in result.head(20).iterrows():
        print(f"{i+1:<5} {row['name'][:38]:<40} {int(row['s_total']):>12,} {int(row['s_empty']):>12,} {row['sigma']:>8.3f} {row['F']:>8.3f}")
    
    print("\n... (showing top 20 of {})".format(len(result)))
    
    # Also show Attica breakdown
    print("\n" + "=" * 100)
    print("ΑΤΤΙΚΗ BREAKDOWN (all PE within Attica)")
    print("=" * 100)
    
    # Attica codes start with 9 (code 9xxxx)
    attica = result[result['code'].astype(str).str.startswith('9')].sort_values('sigma', ascending=False)
    
    print(f"\n{'Rank':<5} {'Regional Unit':<40} {'S_total':>12} {'S_empty':>12} {'σ':>8} {'F':>8}")
    print("-" * 100)
    
    for i, (_, row) in enumerate(attica.iterrows()):
        print(f"{i+1:<5} {row['name'][:38]:<40} {int(row['s_total']):>12,} {int(row['s_empty']):>12,} {row['sigma']:>8.3f} {row['F']:>8.3f}")
    
    # National totals
    print("\n" + "-" * 100)
    s_total_nat = result['s_total'].sum()
    s_empty_nat = result['s_empty'].sum()
    sigma_nat = s_empty_nat / s_total_nat
    f_nat = 1 / (1 - sigma_nat)
    print(f"{'NAT':<5} {'ΣΥΝΟΛΟ ΧΩΡΑΣ':<40} {int(s_total_nat):>12,} {int(s_empty_nat):>12,} {sigma_nat:>8.3f} {f_nat:>8.3f}")
    
    # Save to JSON
    output_dir = script_dir.parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    json_data = {
        "level": "Περιφερειακή Ενότητα",
        "level_code": 4,
        "computed_at": pd.Timestamp.now().isoformat(),
        "national": {
            "s_total": int(s_total_nat),
            "s_empty": int(s_empty_nat),
            "sigma": round(sigma_nat, 4),
            "F": round(f_nat, 4)
        },
        "units": [
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
    
    json_path = output_dir / "friction_by_pe.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ JSON saved to: {json_path}")
    print(f"✓ Total Regional Units: {len(result)}")


if __name__ == "__main__":
    main()

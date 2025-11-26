"""
Explore the A05 dataset structure to understand geographic hierarchy encoding.
Run this to see how Περιφέρεια (Region) vs Περιφερειακή Ενότητα (Regional Unit) are distinguished.
"""
from __future__ import annotations

import sys
from pathlib import Path
import unicodedata
import pandas as pd


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch) and not ch.isspace())


def explore_structure(path: str) -> None:
    df_raw = pd.read_excel(path, header=None)
    
    print("=" * 80)
    print("DATASET STRUCTURE EXPLORATION")
    print("=" * 80)
    print(f"\nShape: {df_raw.shape}")
    
    # Find header row
    try:
        header_start = df_raw.index[df_raw.iloc[:, 0] == "Γεωγραφικό επίπεδο"][0]
        print(f"\nHeader starts at row: {header_start}")
    except IndexError:
        print("Could not find header row")
        return
    
    # Show header rows
    print("\n--- HEADER ROWS (4 rows merged) ---")
    for i in range(4):
        row = df_raw.iloc[header_start + i, :8].tolist()
        print(f"Row {header_start + i}: {row}")
    
    # Get data portion
    data = df_raw.iloc[header_start + 4:].copy()
    
    # Column 0 should be "Γεωγραφικό επίπεδο" (geographic level indicator)
    # Column 1 should be "Κωδικός" (code)
    # Column 2 should be "Περιγραφή" (description/name)
    
    print("\n--- GEOGRAPHIC LEVEL VALUES (Column 0) ---")
    geo_levels = data.iloc[:, 0].dropna().unique()
    print(f"Unique values: {geo_levels}")
    
    print("\n--- SAMPLE ROWS BY GEOGRAPHIC LEVEL ---")
    for level in geo_levels:
        subset = data[data.iloc[:, 0] == level]
        print(f"\n[Level: {level}] - {len(subset)} rows")
        # Show first 3 rows (cols 0-4)
        for idx, row in subset.head(3).iterrows():
            print(f"  Code: {row.iloc[1]}, Name: {row.iloc[2]}")
    
    # Find the row that says "ΣΥΝΟΛΟ ΧΩΡΑΣ" (national total)
    print("\n--- LOOKING FOR NATIONAL AND REGION TOTALS ---")
    for idx, row in data.iterrows():
        name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        if "ΣΥΝΟΛΟ" in name or "ΧΩΡΑ" in name:
            print(f"Row {idx}: Level={row.iloc[0]}, Code={row.iloc[1]}, Name={name}")


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parents[1] / "data" / "elstat" / "A05_dwellings_status_pe_2021.xlsx"
    explore_structure(str(default_path))

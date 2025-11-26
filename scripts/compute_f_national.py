from __future__ import annotations

import sys
from pathlib import Path

import unicodedata

import pandas as pd


def _build_columns(df: pd.DataFrame, header_start: int, rows: int = 4) -> list[str]:
    headers = df.loc[header_start : header_start + rows - 1]
    names: list[str] = []
    for col in df.columns:
        parts = [
            str(val).strip()
            for val in headers[col]
            if pd.notna(val) and str(val).strip()
        ]
        names.append(" ".join(parts))
    return names


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch) and not ch.isspace())


def _find_col(cols: list[str], include: list[str], exclude: list[str] | None = None) -> str:
    exclude = exclude or []
    inc_norm = [_norm(token) for token in include]
    exc_norm = [_norm(token) for token in exclude]
    for name in cols:
        normed = _norm(name)
        if all(token in normed for token in inc_norm) and not any(tok in normed for tok in exc_norm):
            return name
    raise KeyError(f"Could not find column with tokens {include} (excluding {exclude})")


def compute_f_national(path: str) -> None:
    xls_path = Path(path)
    if not xls_path.exists():
        print(f"File not found: {xls_path}", file=sys.stderr)
        sys.exit(1)

    df_raw = pd.read_excel(xls_path, header=None)

    try:
        header_start = df_raw.index[df_raw.iloc[:, 0] == "Γεωγραφικό επίπεδο"][0]
    except IndexError:
        print("Could not locate header row (Γεωγραφικό επίπεδο).", file=sys.stderr)
        sys.exit(1)

    columns = _build_columns(df_raw, header_start, rows=4)
    data = df_raw.loc[header_start + 4 :].copy()
    data.columns = columns
    data = data.dropna(how="all")

    try:
        desc_col = _find_col(columns, ["περιγραφή"])
    except KeyError:
        # Fallback to third column if the match fails
        desc_col = columns[2]

    national = data[data[desc_col].astype(str).str.strip() == "ΣΥΝΟΛΟ ΧΩΡΑΣ"]
    if national.empty:
        print("National row (ΣΥΝΟΛΟ ΧΩΡΑΣ) not found.", file=sys.stderr)
        sys.exit(1)

    try:
        total_col = _find_col(columns, ["κανονικές", "κατοικίες", "συνολο"], exclude=["κενες"])
    except KeyError:
        total_col = _find_col(columns, ["κανονικες", "συνολο"], exclude=["κενες"])

    empty_col = _find_col(columns, ["κενες", "συνολο"])

    row = national.iloc[0]
    s_total = pd.to_numeric(row[total_col], errors="coerce")
    s_empty = pd.to_numeric(row[empty_col], errors="coerce")

    if pd.isna(s_total) or pd.isna(s_empty) or s_total == 0:
        print("Missing or zero values for total/empty dwellings.", file=sys.stderr)
        sys.exit(1)

    sigma = float(s_empty) / float(s_total)
    friction = 1.0 / (1.0 - sigma)

    print(f"Total normal dwellings (S_total): {int(s_total):,}")
    print(f"Empty normal dwellings (S_empty): {int(s_empty):,}")
    print(f"Locked share (sigma): {sigma:.3f}")
    print(f"Friction factor F_v0: {friction:.3f}")


if __name__ == "__main__":
    default_path = Path(__file__).resolve().parents[1] / "data" / "elstat" / "A05_dwellings_status_pe_2021.xlsx"
    compute_f_national(str(default_path))

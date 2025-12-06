import json
import pandas as pd
from pathlib import Path

src = Path("outputs/friction_by_municipality.json")
out = Path("outputs/sigma_by_municipality.csv")

data = json.loads(src.read_text(encoding="utf-8"))

# friction_by_municipality.json has a top-level dict with a "municipalities" list
if isinstance(data, dict) and "municipalities" in data:
    records = data["municipalities"]
elif isinstance(data, list):
    records = data
else:
    raise ValueError("Unexpected JSON structure in friction_by_municipality.json")

df = pd.DataFrame(records)

# Keep the most relevant fields for inspection
cols = [c for c in ["code", "name", "s_total", "s_empty", "sigma"] if c in df.columns]
df = df[cols]

out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print("Saved:", out)

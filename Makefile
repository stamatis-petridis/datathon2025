.PHONY: install data csv friction analysis maps report all clean
.ONESHELL:

PYTHON := python3
PIP := $(PYTHON) -m pip
DATA_DIR := data/elstat
GEO_DIR := data/geo
OUTPUT_DIR := outputs

install:
	$(PIP) install -r requirements.txt

data:
	mkdir -p $(DATA_DIR) $(GEO_DIR)
	curl -L -o $(DATA_DIR)/buildings_by_use.xlsx "https://www.statistics.gr/documents/20181/18660884/A1601_SKT01_TB_DC_00_2021_02A_F_GR.xlsx"
	curl -L -o $(DATA_DIR)/buildings_by_use_dwellings.xlsx "https://www.statistics.gr/documents/20181/18660884/A1601_SKT01_TB_DC_00_2021_04A_F_GR.xlsx"
	curl -L -o $(DATA_DIR)/buildings_by_period.xlsx "https://www.statistics.gr/documents/20181/18660884/A1601_SKT01_TB_DC_00_2021_06A_F_GR.xlsx"
	curl -L -o $(DATA_DIR)/A05_dwellings_status_pe_2021.xlsx "https://www.statistics.gr/documents/20181/18660884/E%BC%CE%B5%CE%BD%CE%B5%CF%82%2C%2B%CE%BA%CE%B5%CE%BD%CE%AD%CF%82%29%2C%2B%CE%B4%CE%B9%CE%B1%CE%B8%CE%B5%CF%83%CE%B9%CE%BC%CF%8C%CF%84%CE%B7%CF%84%CE%B1%2B%CE%B4%CE%B9%CE%BA%CF%84%CF%8D%CE%BF%CF%85%2B%CF%85%CE%B4%CF%81%CE%BF%CE%B4%CF%8C%CF%84%CE%B7%CF%83%CE%B7%CF%82%2B%CE%BA%CE%B1%CE%B9%2B%CE%BB%CE%BF%CF%85%CF%84%CF%81%CE%BF%CF%8D.%2B%CE%A0%CE%B5%CF%81%CE%B9%CF%86%CE%B5%CF%81%CE%B5%CE%B9%CE%B1%CE%BA%CE%AD%CF%82%2B%CE%95%CE%BD%CF%8C%CF%84%CE%B7%CF%84%CE%B5%CF%82%2B%28%2B2021%2B%29.xlsx/bab0ae50-a30d-48aa-77ee-0528b3eb91e9?download=true"
	curl -L -o $(DATA_DIR)/G01_dwellings_status_oikismoi_2021.xlsx "https://www.statistics.gr/documents/20181/18660884/2B%CE%9A%CE%B1%CE%BD%CE%BF%CE%BD%CE%B9%CE%BA%CE%AD%CF%82%2B%CE%BA%CE%B1%CF%84%CE%BF%CE%B9%CE%BA%CE%AF%CE%B5%CF%82%2B%CE%BA%CE%B1%CF%84%CE%AC%2B%CE%BA%CE%B1%CF%84%CE%AC%CF%83%CF%84%CE%B1%CF%83%CE%B7%2B%CE%BA%CE%B1%CF%84%CE%BF%CE%B9%CE%BA%CE%AF%CE%B1%CF%82%2B%CE%BA%CE%B1%CE%B9%2B%CE%BC%CE%B7%2B%CE%BA%CE%B1%CE%BD%CE%BF%CE%BD%CE%B9%CE%BA%CE%AD%CF%82%2B%CE%BA%CE%B1%CF%84%CE%BF%CE%B9%CE%BA%CE%AF%CE%B5%CF%82.%2B%CE%9F%CE%B9%CE%BA%CE%B9%CF%83%CE%BC%CE%BF%CE%AF%2B%28%2B2021%2B%29.xlsx/e0c72124-3d35-8b56-513b-800315f25b86?download=true"
	curl -L -o $(GEO_DIR)/gadm41_GRC_shp.zip "https://geodata.ucdavis.edu/gadm/gadm4.1/shp/gadm41_GRC_shp.zip"
	unzip -o $(GEO_DIR)/gadm41_GRC_shp.zip -d $(GEO_DIR)

csv:
	$(PYTHON) -c "from pathlib import Path; import pandas as pd, sys; src=Path('data/elstat'); out=src/'csv'; out.mkdir(parents=True, exist_ok=True); \
files=sorted(src.glob('*.xlsx')); \
[ (pd.read_excel(x).to_csv(out/f'{x.stem}.csv', index=False), sys.stdout.write(f'Wrote {out/x.stem}.csv\\n')) for x in files ];"

friction:
	@if [ -n "$(wildcard scripts/compute_f_*.py)" ]; then \
		for f in scripts/compute_f_*.py; do echo "Running $$f"; $(PYTHON) $$f; done; \
	else \
		echo "No compute_f_*.py scripts found"; \
	fi

analysis:
	$(PYTHON) scripts/analyze_vacancy_composition.py

maps:
	$(PYTHON) scripts/choropleth_municipalities.py
	$(PYTHON) scripts/choropleth_archetypes.py

report:
	@printf "Generating PDF report (pandoc)...\n"; \
	if command -v pandoc >/dev/null 2>&1; then \
		pandoc docs/housing_friction_report.md \
			--pdf-engine=xelatex \
			--resource-path=.:docs:outputs \
			-V mainfont="Times New Roman" \
			-o outputs/housing_friction_report.pdf; \
	else \
		echo "pandoc not installed; skipping PDF export"; \
	fi

all: install data csv friction analysis maps report

clean:
	rm -f $(OUTPUT_DIR)/*.png $(OUTPUT_DIR)/*.html $(OUTPUT_DIR)/*.json $(OUTPUT_DIR)/*.csv $(OUTPUT_DIR)/*.pdf

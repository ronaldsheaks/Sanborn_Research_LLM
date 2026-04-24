# Sanborn Research LLM - Phase 0 Corpus Proof of Concept

This is a lightweight work sample showing how AI can assist with jazz/cultural hub and corridor research for Buffalo and Pittsburgh.

## What this proves

The workflow turns a qualitative corpus into structured research leads:

1. Inventory source PDFs.
2. Extract readable text samples.
3. Discard unreadable / upside-down candidates from automated scoring.
4. Count recurring names, places, institutions, streets, and governance terms.
5. Parse event-contract style listings where the pattern is detectable.
6. Generate candidate hubs/corridors for human verification and later GIS work.

## Current output

- Sources inventoried: **13**
- Event rows extracted from contract-listing samples: **12**
- Candidate hubs/corridors generated: **20**
- Keyword/theme rows generated: **56**

## Key tables

- `data/source_inventory.csv` - source list, topic focus, extraction status, notes
- `data/keyword_counts.csv` - recurring theme terms and source counts
- `data/event_contracts.csv` - parsed event / performance listing rows
- `data/candidate_hubs_corridors.csv` - scored candidate hubs and corridor leads
- `data/source_theme_scores.csv` - source-level theme signal counts

## Method

Corpus PDFs -> deterministic Python extraction/counting -> event parsing -> candidate hub/corridor scoring -> human verification -> GIS/story map layer.

Python does the counting. The LLM should be used after this step to summarize patterns, group terms, and draft research notes from source IDs and excerpts.

## How to run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/sanborn_llm_corpus_poc.py --corpus-dir corpus_raw --out-dir data
```

Keep PDFs in `corpus_raw/`. Keep API keys in `.env`; never hard-code them.

## Next strengthening steps

1. Add Green Book linked pages, Sanborn map links, newspaper items, and building photos.
2. Add source URLs/citations to every extracted record.
3. Add geocoded coordinates to candidate places.
4. Connect candidates back to the master GIS dataset.
5. Add optional LLM summaries using source IDs and excerpts.
6. Export GeoJSON for Leaflet/QGIS/ArcGIS after coordinates are verified.

# Sanborn Research LLM - Phase 0 Corpus Proof of Concept

This is a lightweight work sample showing how AI can assist with jazz/cultural hub and corridor research for Buffalo and Pittsburgh.

## What this proves

The workflow turns a qualitative corpus into structured research leads:

1. Inventory source PDFs, transcripts, documentary pages, and archival links.
2. Extract readable text samples or transcript-derived metadata.
3. Discard unreadable / upside-down candidates from automated scoring.
4. Count recurring names, places, institutions, streets, and governance terms.
5. Parse event-contract style listings where the pattern is detectable.
6. Generate candidate hubs/corridors for human verification and later GIS work.

## Current output

- Sources inventoried: **28**
- Event rows extracted from contract-listing samples: **12**
- Candidate hubs/corridors generated: **20+**
- Keyword/theme rows generated: **56+**
- New Pittsburgh transcript-derived corpus source: **PBS/WQED Wylie Avenue Days**

## Key tables / files

- `data/source_inventory.csv` - source list, topic focus, extraction status, notes
- `data/keyword_counts.csv` - recurring theme terms and source counts
- `data/event_contracts.csv` - parsed event / performance listing rows
- `data/candidate_hubs_corridors.csv` - scored candidate hubs and corridor leads
- `data/source_theme_scores.csv` - source-level theme signal counts
- `data/pbs_wylie_avenue_days_corpus.json` - structured, copyright-safe corpus metadata derived from the PBS/WQED *Wylie Avenue Days* transcript page
- `wylie-avenue-days.html` - public addendum page summarizing the Pittsburgh/Hill District corpus addition

## New PBS/WQED corpus addition

The app now includes a structured corpus record for *Wylie Avenue Days*, a PBS/WQED documentary focused on Pittsburgh's Hill District, Wylie Avenue, Fullerton Street, Black commercial life, jazz/nightlife institutions, media institutions, churches, social clubs, segregation, urban renewal, and displacement.

The full PBS transcript is not republished in this public repository. Instead, the project stores source metadata, extracted entities, candidate nodes, theme bins, GIS handoff notes, and verification guidance. This keeps the workflow useful for LLM/corpus analysis while respecting the source transcript.

Priority model signals added from this source include:

- Wylie Avenue / Fullerton Street crossroads
- Goode's Pharmacy
- Crawford Grill No. 1 and No. 2
- Pittsburgh Courier
- Loendi Club
- The Frogs
- Saint Benedict the Moor / Freedom Corner
- Nesbitt's Pie Shop
- McAvoy's Jeweler
- Owl Cab Company
- Greenlee Field
- Civic Arena / Lower Hill displacement zone
- Great Migration, Black commercial corridor, parallel institutions, social infrastructure, media/documentation, nightlife, informal economy, urban renewal, and displacement theme bins

## Method

Corpus PDFs/transcript pages -> deterministic Python extraction/counting -> event parsing -> candidate hub/corridor scoring -> LLM-assisted thematic grouping -> human verification -> GIS/story map layer.

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
7. Integrate `pbs_wylie_avenue_days_corpus.json` into the automated source inventory and entity-count build script.

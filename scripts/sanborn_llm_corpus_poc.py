#!/usr/bin/env python3
"""
Sanborn Research LLM - Phase 0 corpus proof of concept.

Purpose:
    Convert a small archival corpus into deterministic research tables that can
    support an LLM-assisted workflow for hub/corridor discovery.

Design rule:
    Python does the counting and table generation. The LLM should only be used
    after this step to summarize, interpret, and suggest bins based on source IDs.

Usage:
    1. Put PDFs in ./corpus_raw or pass --corpus-dir /path/to/pdfs
    2. Install pypdf: pip install pypdf
    3. Run: python scripts/sanborn_llm_corpus_poc.py --corpus-dir corpus_raw --out-dir data

Notes:
    - Files with page rotation 180 are skipped as upside-down.
    - Fragile/corrupt PDFs are inventoried and marked for OCR/manual review.
    - This starter limits extraction pages by default to keep a proof-of-concept fast.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    from pypdf import PdfReader
except Exception as exc:  # pragma: no cover
    raise SystemExit("Missing dependency. Install with: pip install pypdf") from exc

THEME_TERMS: Dict[str, List[str]] = {
    "Jazz / performance": [
        "jazz", "music", "musician", "musicians", "band", "orchestra", "swing",
        "bebop", "dance", "jam session", "performance", "performer", "nightlife",
        "club", "venue", "theater", "ballroom", "auditorium",
    ],
    "Governance / labor": [
        "union", "local 533", "local 471", "american federation of musicians",
        "contract", "contracts", "booking", "dues", "work tax", "business agent",
        "secretary", "president", "membership", "merge", "merger", "integration",
        "segregation",
    ],
    "Hub / institution": [
        "colored musicians club", "crawford grill", "loendi club", "new granada",
        "savoy ballroom", "musicians club", "michigan street baptist church",
        "wufo", "pittsburgh courier", "buffalo criterion", "memorial auditorium",
    ],
    "Corridor / spatial": [
        "corridor", "street", "avenue", "wylie avenue", "fullerton", "center avenue",
        "michigan street", "hill district", "lower hill", "upper hill", "buffalo",
        "pittsburgh", "neighborhood", "district", "crossroads",
    ],
    "Economy / business": [
        "business", "entrepreneur", "economic", "numbers", "racket", "hotel",
        "bar", "pharmacy", "restaurant", "cash", "rent", "loan", "wages", "job",
    ],
    "Urban change / displacement": [
        "urban redevelopment", "redevelopment", "renewal", "demolition", "clearing",
        "displacement", "riot", "riots", "civil rights", "migration", "segregation",
    ],
}

CURATED_CANDIDATES = {
    "Colored Musicians Club": ("Buffalo", "institution / union", ["Colored Musicians Club", "Local 533"]),
    "Michigan Street": ("Buffalo", "corridor / street", ["Michigan Street"]),
    "WUFO Radio": ("Buffalo", "radio / cultural institution", ["WUFO"]),
    "Michigan Street Baptist Church": ("Buffalo", "church / civic institution", ["Michigan Street Baptist Church"]),
    "Crawford Grill": ("Pittsburgh", "venue / club", ["Crawford Grill"]),
    "Wylie Avenue": ("Pittsburgh", "corridor / street", ["Wylie Avenue"]),
    "Fullerton Street": ("Pittsburgh", "corridor / street", ["Fullerton Street", "Fullerton"]),
    "New Granada Theater": ("Pittsburgh", "venue / theater", ["New Granada", "Granada Theater"]),
    "Savoy Ballroom": ("Pittsburgh", "venue / ballroom", ["Savoy Ballroom", "Hill City Auditorium", "Pythian Temple"]),
    "Loendi Club": ("Pittsburgh", "social club", ["Loendi Club", "Loendi"]),
    "Musicians Club": ("Pittsburgh", "institution / club", ["Musicians Club", "Musicians' Club", "Musicians’ Club"]),
    "Hurricane Bar": ("Pittsburgh", "venue / club", ["Hurricane Bar", "Hurricane Grill", "Hurricane"]),
    "Bambola Social Club": ("Pittsburgh", "venue / club", ["Bambola Social Club", "Bambola"]),
}

MONTH_RE = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"


def clean_text(value: str) -> str:
    value = (value or "").replace("\x00", " ").replace("\u00ad", "")
    value = value.replace("ﬁ", "fi").replace("ﬂ", "fl")
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def count_term(text: str, term: str) -> int:
    pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"s?\b"
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def extract_pdf_text(path: Path, max_pages: int) -> Tuple[str, dict]:
    """Extract a bounded amount of text and return status metadata."""
    try:
        reader = PdfReader(str(path), strict=False)
    except Exception as exc:
        return "", {"status": "skipped_unreadable", "error": repr(exc), "pages_total": ""}

    pages_total = len(reader.pages)
    rotations = []
    text_parts: List[str] = []
    for idx in range(min(max_pages, pages_total)):
        try:
            page = reader.pages[idx]
            rotation = page.get("/Rotate") or 0
            rotations.append(rotation)
            if rotation == 180:
                return "", {
                    "status": "skipped_upside_down_rotation_180",
                    "error": "page rotation is 180",
                    "pages_total": pages_total,
                    "rotations_sample": rotations,
                }
            text_parts.append(page.extract_text() or "")
        except Exception as exc:
            text_parts.append("")

    text = clean_text("\n\n".join(text_parts))
    words = re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text)
    status = "extracted_sample" if len(words) >= 20 else "skipped_low_text_extraction"
    return text, {
        "status": status,
        "error": "",
        "pages_total": pages_total,
        "rotations_sample": rotations[:5],
        "word_count_est": len(words),
        "character_count": len(text),
    }


def infer_city_topic(filename: str, text: str) -> Tuple[str, str]:
    haystack = f"{filename} {text[:30000]}".lower()
    buffalo = sum(haystack.count(x) for x in ["buffalo", "local 533", "colored musicians club", "kleinhans", "memorial auditorium", "genesee"])
    pittsburgh = sum(haystack.count(x) for x in ["pittsburgh", "hill district", "wylie", "crawford grill", "fullerton", "new granada"])
    city = "Buffalo" if buffalo >= pittsburgh and buffalo > 0 else "Pittsburgh" if pittsburgh > 0 else "Unknown"

    if "local 533" in haystack or "colored musicians club" in haystack:
        topic = "Buffalo Local 533 / Colored Musicians Club"
    elif "crossroads of the world" in haystack or "hill district" in haystack:
        topic = "Pittsburgh Hill District jazz history"
    elif "american federation" in haystack or "international-musician" in filename.lower():
        topic = "American Federation of Musicians / labor context"
    elif "name:" in haystack and "place:" in haystack:
        topic = "Performance contract/event listings"
    else:
        topic = "Inventoried source - extraction/verification needed"
    return city, topic


def parse_event_rows(filename: str, text: str) -> List[dict]:
    corpus = normalize(text)
    starts = [m.start() for m in re.finditer(r"\bName\s*:", corpus)]
    rows = []
    for idx, start in enumerate(starts):
        chunk = corpus[start : starts[idx + 1] if idx + 1 < len(starts) else len(corpus)]
        prior = corpus[max(0, start - 100) : start]
        date_matches = list(re.finditer(r"(19\d{2})\s+" + MONTH_RE + r"(?:\s+\d{1,2})?", prior))
        event_date = normalize(date_matches[-1].group(0)) if date_matches else ""

        def grab(field: str, next_fields: Iterable[str]) -> str:
            next_pattern = "|".join(re.escape(x) for x in next_fields)
            m = re.search(re.escape(field) + r"\s*(.*?)(?=\s+(?:" + next_pattern + r")\s*:|$)", chunk, flags=re.I)
            return normalize(m.group(1)) if m else ""

        name = grab("Name:", ["Place", "No. of personnel (if known)", "Side personnel or group(s)", "Length of job played", "Source of information", "Date of contract", "Remarks", "Name"])
        place = grab("Place:", ["No. of personnel (if known)", "Side personnel or group(s)", "Length of job played", "Source of information", "Date of contract", "Remarks", "Name"])
        if not name or not place:
            continue
        rows.append({
            "event_id": "",
            "source_file": filename,
            "event_date_raw": event_date,
            "artist_or_act": name,
            "place": place,
            "personnel_count_raw": grab("No. of personnel (if known):", ["Side personnel or group(s)", "Length of job played", "Source of information", "Date of contract", "Remarks", "Name"]),
            "side_personnel_or_groups": grab("Side personnel or group(s):", ["Length of job played", "Source of information", "Date of contract", "Remarks", "Name"]),
            "job_length": grab("Length of job played:", ["Source of information", "Date of contract", "Remarks", "Name"]),
            "source_info": grab("Source of information:", ["Date of contract", "Remarks", "Name"]),
            "contract_date_raw": grab("Date of contract:", ["Remarks", "Name"]),
            "remarks": grab("Remarks:", ["Name"]),
        })
    return rows


def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus_raw")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--max-pages", type=int, default=12)
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    texts: Dict[str, str] = {}
    sources: List[dict] = []
    for idx, path in enumerate(sorted(corpus_dir.glob("*.pdf")), 1):
        if path.name.startswith("._"):
            continue
        text, meta = extract_pdf_text(path, args.max_pages)
        city, topic = infer_city_topic(path.name, text)
        texts[path.name] = text
        sources.append({
            "source_id": f"SRC_{idx:03d}",
            "filename": path.name,
            "city_focus": city,
            "topic_focus": topic,
            "pages_total": meta.get("pages_total", ""),
            "pages_processed_for_poc": args.max_pages if meta.get("status") == "extracted_sample" else 0,
            "word_count_est": meta.get("word_count_est", 0),
            "character_count": meta.get("character_count", 0),
            "extraction_status": meta.get("status"),
            "notes": normalize(text[:500]),
            "error": meta.get("error", ""),
        })

    write_csv(out_dir / "source_inventory.csv", sources, list(sources[0].keys()) if sources else [])
    (out_dir / "source_inventory.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")

    keyword_rows = []
    for theme, terms in THEME_TERMS.items():
        for term in terms:
            total = 0
            source_hits = []
            for filename, text in texts.items():
                hits = count_term(text, term)
                if hits:
                    total += hits
                    source_hits.append(filename)
            if total:
                keyword_rows.append({
                    "theme_bin": theme,
                    "term": term,
                    "count": total,
                    "source_count": len(source_hits),
                    "sources": "; ".join(source_hits),
                })
    keyword_rows.sort(key=lambda row: (-int(row["count"]), row["theme_bin"], row["term"]))
    write_csv(out_dir / "keyword_counts.csv", keyword_rows, ["theme_bin", "term", "count", "source_count", "sources"])
    (out_dir / "keyword_counts.json").write_text(json.dumps(keyword_rows, indent=2), encoding="utf-8")

    events = []
    for filename, text in texts.items():
        events.extend(parse_event_rows(filename, text))
    for i, row in enumerate(events, 1):
        row["event_id"] = f"EVT_{i:04d}"
    event_fields = ["event_id", "source_file", "event_date_raw", "artist_or_act", "place", "personnel_count_raw", "side_personnel_or_groups", "job_length", "source_info", "contract_date_raw", "remarks"]
    write_csv(out_dir / "event_contracts.csv", events, event_fields)
    (out_dir / "event_contracts.json").write_text(json.dumps(events, indent=2), encoding="utf-8")

    place_counter = Counter(normalize(row["place"]) for row in events if row.get("place"))
    place_sources = defaultdict(set)
    place_artists = defaultdict(set)
    for row in events:
        place = normalize(row.get("place", ""))
        if place:
            place_sources[place].add(row["source_file"])
            place_artists[place].add(row["artist_or_act"])

    candidates = []
    for place, count in place_counter.most_common():
        score = count * 3 + len(place_artists[place]) * 1.5 + len(place_sources[place])
        classification = "Tier I hub candidate" if score >= 35 else "Tier II node candidate" if score >= 12 else "Lead / needs verification"
        candidates.append({
            "candidate_name": place,
            "city": "Buffalo",
            "candidate_type": "venue / event site",
            "mention_or_event_count": count,
            "unique_artist_count": len(place_artists[place]),
            "source_count": len(place_sources[place]),
            "score": round(score, 1),
            "suggested_classification": classification,
            "evidence_basis": "Extracted from performance/event listing pattern",
            "sources": "; ".join(sorted(place_sources[place])),
        })

    for name, (city, kind, variants) in CURATED_CANDIDATES.items():
        total = 0
        source_hits = []
        for filename, text in texts.items():
            hits = sum(count_term(text, variant) for variant in variants)
            if hits:
                total += hits
                source_hits.append(filename)
        if total:
            score = total * 2 + len(source_hits) * 3
            classification = "Tier I hub/corridor candidate" if total >= 20 else "Tier II node/corridor candidate" if total >= 5 else "Lead / needs verification"
            candidates.append({
                "candidate_name": name,
                "city": city,
                "candidate_type": kind,
                "mention_or_event_count": total,
                "unique_artist_count": "",
                "source_count": len(source_hits),
                "score": round(score, 1),
                "suggested_classification": classification,
                "evidence_basis": "Curated phrase counted across corpus sample",
                "sources": "; ".join(source_hits),
            })

    dedup = {}
    for row in candidates:
        key = (row["candidate_name"].lower(), row["city"])
        if key not in dedup or float(row["score"]) > float(dedup[key]["score"]):
            dedup[key] = row
    candidates = sorted(dedup.values(), key=lambda row: float(row["score"]), reverse=True)
    candidate_fields = ["candidate_name", "city", "candidate_type", "mention_or_event_count", "unique_artist_count", "source_count", "score", "suggested_classification", "evidence_basis", "sources"]
    write_csv(out_dir / "candidate_hubs_corridors.csv", candidates, candidate_fields)
    (out_dir / "candidate_hubs_corridors.json").write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    summary = {
        "source_count": len(sources),
        "event_rows_extracted": len(events),
        "candidate_target_count": len(candidates),
        "keyword_rows": len(keyword_rows),
        "note": "Deterministic Phase 0 leads for human review, not final historical claims.",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

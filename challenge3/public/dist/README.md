# Forest Routes — AmazôniaHack Challenge 3

Offline route feasibility for unmapped Amazon roads: OSM + PrevisIA, explicit walking limits, reviewable gap connectors, and evidence screening.

**Public package contains no participant road files or site coordinates.** Run against your authorised Challenge 3 data copy.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m forest_routes.benchmark \
  --data-dir "/path/to/Challenge 3" --output private/results \
  --vehicle-only --reject-gaps evidence/quarantined-gap-ids.json \
  --screened-gaps evidence/screened-candidate-gap-ids.json --export-graph
```

Expected (150 m gaps, 1 km walk/end, screened policy): **4/16 geometric candidates, 0 field-verified**.

Outputs (keep private): `report.html` (field officer review), `offline-router.html` (map visualization), routes, summary, compact graph.

## Submission materials

- [`SUBMISSION.md`](SUBMISSION.md) — form paste text (summary, description, parts, links)
- [`public/dist/submission.md`](public/dist/submission.md) — technical one-pager
- [`public/dist/results.json`](public/dist/results.json) — aggregate public-safe results
- [`public/dist/forest-routes-source.zip`](public/dist/forest-routes-source.zip) — allowlisted source archive

Rebuild the zip:

```bash
python3 scripts/package_submission.py
```

## Limits

PrevisIA age and passability are unknown. Planar junctions and proposed gaps are geometric hypotheses. Walking distances are Euclidean lower bounds. River/elevation flags are screening only. Satellite layer is downsampled Sentinel-2 — not bridge verification.

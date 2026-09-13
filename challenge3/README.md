# Forest Routes — AmazôniaHack Challenge 3

Offline route feasibility for unmapped Amazon roads.

See the **[repository README](../README.md)** for screenshots, method, and results.

Form paste text: [`SUBMISSION.md`](SUBMISSION.md)

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

Expected (screened policy): **4/16** geometric candidates, **0** field-verified.

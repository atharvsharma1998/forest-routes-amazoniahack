# AmazôniaHack Challenge 3 — submission form draft

Copy each section into the platform. Replace `[LINK]` placeholders before submit. Do **not** publish participant road files, site coordinates, imagery chips, or the municipal graph.

---

## Summary of the proposed project

**Forest Routes** helps municipal environmental inspectors decide whether a field site in Paragominas can be reached offline using official OSM roads, Imazon PrevisIA road traces, and an explicitly declared walking leg at each end. Challenge 3 is that destinations sit off the official map, PrevisIA is fragmented (not a ready network), and inventing junctions can fake a route.

Our approach measures connectivity instead of chasing coverage: compare shared vertices, planar intersections, and explicit reviewable gap connectors; keep walking as a declared lower bound; screen doubtful connections with imagery, rivers, and elevation; then export a compact municipal graph for offline browser routing. Under a screened policy we report **4/16 geometric candidates and 0 field-verified routes** — an honest ceiling, not a navigation claim.

---

## Description of the project

Inspection destinations in Amazônia often lie kilometres from any officially mapped road. PrevisIA adds detected rural traces, but crossing lines often share no node, so a router that blindly snaps gaps can invent bridges and river crossings. Forest Routes treats that failure mode as the product problem.

**How it works**

1. A Python CLI loads the two Challenge 3 GeoJSON layers and the 16 test journeys, projects to UTM 23S, and builds several graph scenarios (OSM alone, PrevisIA alone, fused shared vertices, planar noding, and explicit 50/150/300 m gap proposals).
2. A journey is a *geometric candidate* only if both ends attach to the same connected component within a declared walking allowance (default 1 km per end). Walking distances are straight-line lower bounds, not verified footpaths. Proposed gaps keep their real length and stable IDs; they are never free teleports.
3. Review decisions change the graph: quarantine doubtful gaps, or retain only imagery-screened candidates. Rerunning with the same 150 m / 1 km policy shows that exploratory connectivity (**10/16**) collapses to **4/16** when only screened gaps are allowed — coverage without evidence is not reliability.
4. Independent checks enrich the dossier: Sentinel-2 gap screening, ANA river centerline intersections, and Copernicus GLO-30 surface elevation samples along candidate corridors. These flag risk; they do not approve navigation.
5. The pipeline exports a ~23 MB compact municipal graph and a self-contained offline HTML router that computes new routes in the browser with no server or API (desktop-validated; not a phone GPS navigator).

**Intended impact**

Inspectors prepare a municipal extract while online, then inspect candidate routes offline: see road vs proposed gap vs walking, reject bad junctions, and know which journeys become unavailable. The unique emphasis is **uncertainty-first routing** — measuring what connectivity assumptions invent, and refusing to overclaim passability.

**Limits we state clearly**

Bridge state, legal access, seasonality, and trace age remain unknown. Planar crossings are hypotheses. Zero routes are field-verified. Physical Android navigation remains future work.

---

## Description of each project part submitted

| Part | What it is |
|---|---|
| **Runnable source archive** (`forest-routes-source.zip`) | Python pipeline, tests, feedback/GPX review CLI, evidence policy JSON (quarantined and screened gap IDs), README for organisers to reproduce against their authorised Challenge 3 data copy. Contains **no** participant coordinates or municipal graph. |
| **Technical submission note** (`submission.md`) | One-page method, measured results (exploratory 10/16 vs screened 4/16), validation, cost, and limits. |
| **Aggregate results** (`results.json`) | Public-safe summaries: coverage matrices, river/terrain screening aggregates, JS↔Python portable validation stats. No site coordinates. |
| **Field officer review** (`report.html`, private) | Dashboard to inspect the 16 journeys, OSM/PrevisIA layers, proposed gaps, walking legs, and imagery screening notes. **Do not publish.** |
| **Map visualization** (`offline-router.html`, private) | Dashboard to compute fresh routes on the municipal graph in the browser (no server/API). **Do not publish.** |
| **Optional slides / short demo script** | If submitted: problem → connectivity finding → screened vs exploratory contrast → two dashboards → stated limits. |

*(No public synthetic demo is submitted.)*

---

## Links to project materials

Fill these with working URLs before submit:

1. **Source + public docs (safe to share)**  
   `[LINK to forest-routes-source.zip or GitHub repo without private data]`  
   Includes: runnable code, `submission.md`, `results.json`, evidence policy IDs.

2. **Private offline router (organisers / closed demo only)**  
   `[LINK or shared drive to offline-router.html — access-controlled]`  
   Or: deliver on USB / local demo; do not put on a public website.

3. **Private evidence report (optional, same rules)**  
   `[LINK or local path to report.html]`

4. **Presentation slides (if any)**  
   `[LINK]`

5. **Team contact / deletion confirmation channel**  
   `[email or organiser form]` — confirm deletion of supplied data and coordinate-bearing derivatives after the event as required.

### Local paths ready to upload (this machine)

- Public archive: `challenge3/public/dist/forest-routes-source.zip`
- Public note: `challenge3/public/dist/submission.md`
- Public results: `challenge3/public/dist/results.json`
- Private router: `challenge3/private/reviewed/offline-router.html` (or `challenge3/private/release-validation/results/offline-router.html`)
- Private report: `challenge3/private/outputs/report.html` / `challenge3/private/reviewed/report.html`

### Checklist before pressing submit

- [ ] No OSM/PrevisIA GeoJSON, `test-pairs.csv`, imagery, or compact graph in any public link
- [ ] Screened headline number used in summary: **4/16 candidates, 0 field-verified**
- [ ] Offline router described as desktop browser prototype, not Android GPS nav
- [ ] Every pasted URL opens and matches the description above

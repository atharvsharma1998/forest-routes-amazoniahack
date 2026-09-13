# Forest Routes — AmazôniaHack Challenge 3

**Summary (13 words):** Offline routing for unmapped Amazon roads with explicit walking limits and reviewable connections.

## What runs

A reproducible Python CLI ingests the two supplied road layers and the 16 test pairs, builds graph variants, applies review decisions, compares walking policies and exports per-pair results. A compact municipal graph supports fresh route computation in a self-contained JavaScript browser map visualization. Two private dashboards are produced: field officer review and map visualization. The real municipal graph stays private.

## Method and comparison

Lengths are measured in UTM 23S for Paragominas. Compare exact shared vertices, planar intersection noding and explicit endpoint-to-line gaps at 50/150/300 m. Both journey ends must have network access within the declared walking allowance. Walking distances are straight-line lower bounds, not validated footpaths. Costs are road metres + 5 × gap metres + 10 × walking metres; these are planning weights, not ETAs.

At 150 m proposed gaps and 1 km walking per end, OSM produces 1/16 candidates, PrevisIA 0/16, and the exploratory combined method 10/16. Four doubtful gap IDs were actually excluded and rerun: coverage stayed 10/16 because alternatives used other unreviewed connections. Allowing only the four visually screened gap candidates yields **4/16**, with all others withheld. **Zero routes are field-verified.** This contrast is a central result: improving a coverage count is not evidence that the proposed journey is real.

The raw PrevisIA graph reproduces the supplied 1,874 components and 2.26% of total length in the largest. Our results are method-specific; the organisers' published 9/16 lacks a fully specified walking/attachment policy and is not directly comparable. Five test destinations are closely clustered.

## Evidence loop and validation

Eight gap proposals have dated imagery screening notes, explicit decisions and provenance. Four remain unverified candidates; four are quarantined due to alignment, cloud, resolution or corridor ambiguity. The actual exclusion files and evaluation policies are included in the source archive.

An alternate ANA service supplied 974 valid river geometries. Full exploratory routes have 127 route–river centerline intersection records; the four retained candidate routes have 51. The two zero-gap routes still have 8 and 12 crossings. These are screening flags, not findings that bridges are absent; shared crossings across journeys are not unique bridges. Numeric Copernicus GLO-30 surface elevation is sampled along complete candidate routes at roughly 100 m intervals. Surface-change gradients can include canopy and structures and must not be presented as measured road grade.

Ten Python tests check topology, attachment, origin allowance, gap cost/limits/rejection, parallel edges and feedback acceptance/revocation. The JavaScript engine matched all 16 final-policy Python outcomes, with route distance agreement within 2 m and final attachment agreement within 3 cm in the recorded desktop check. GPX tracks enter as local proposals, require a named review, and can be rejected later. No actual inspector traversal or season-long improvement is claimed.

## Offline and cost

The final municipal graph is approximately 23 MB. The private self-contained browser app performs new route queries without a server or API; network connections are disabled by its content security policy. Desktop Node validation used approximately 61 ms for graph loading and 21–27 ms for the four connected queries in one run. These are desktop measurements, **not physical Android measurements**. The full desktop preprocessing comparison took approximately 103 seconds in the screened-policy run. External API charge per route is US$0; hardware, energy, preprocessing, downloads and human review are not priced.

## Limits

Road access, one-way restrictions, bridge state, seasonality and trace acquisition dates remain unknown. Planar crossings are hypotheses. Full-length river/DSM screening and imagery review do not establish safe navigation. Physical phone testing, inspector approval and a production navigation engine remain outside the validated result. The accepted deliverable is a working offline feasibility and review tool with evidence-backed limitations.

## Public/private boundary

The public project contains runnable source, review policy IDs and aggregate results. It contains no participant roads, site coordinates, real route geometries, real imagery, municipal graph, or public synthetic demo. Organisers can run it against their own authorised input copy. Supplied data and coordinate-bearing derivatives remain private and must be deleted after the event with the required written confirmation.

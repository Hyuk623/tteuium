# Review: three-route leaflet fusion handoff

## Scope and outcome
Reviewed CLAUDE_THREE_ROUTE_LEAFLET_FUSION_2026-09-20.md against the companion hybrid handoff. Document review only; no implementation, reconstruction or inference. The route document is compatible with the companion and correctly preserves the scoped diagnostic pose-source exception. No new blocking architectural conflict was identified.

## Confirmed interpretation
- Global route: all eligible observations.
- Vertical route: 01 -> 21 -> 11; other directions use corresponding oblique/side pairs, and top 01/03 only for visible shared features.
- Circumferential route: side ring 11 through 18 with wraparound; oblique ring 21 through 28 also supported.
- Routes are alternative ways to discover/review associations in one shared graph. They are not independent 3D measurements or camera-pose propagation chains.
- Freeze ChArUco reference geometry, deduplicate shared observations and preserve baseline/diagnostic/held-out/freshness requirements from the companion.

## Implementation clarifications
1. The suggested collect_unique_point_observations(point_id, ...) interface must receive an already scoped plant/session/leaflet context or a composite physical-point key. Existing local point names such as b1/i1 may repeat on different leaflets; never combine them globally by point_id alone.
2. A partially occluded leaflet can still contain a visible, confirmed physical landmark. Exclude hidden point observations, not every point on every partial leaflet. Whole-leaf bbox-extent eligibility remains a different rule.
3. UI completeness and graph consistency are not proof of side-pose readiness. New side-only features still require another appropriately posed observation for depth.
4. Document final solver/acceptance settings before a real trial; the companion defines safeguards, not a completed numerical policy. Retain inactive-null semantics and independent validation status.

Recommended implementation order: shared route navigation and track review; scoped observation collection and deduplication; baseline reconstruction integration; optional one-side-image diagnostic pose trial when reviewed references exist. Existing source code and saved label state were not re-audited by this document-only review.

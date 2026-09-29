# Focused handoff: JSON references for the three-route 3D calculator

## Scope

Implement only the data-reference layer that lets the existing 3D calculator consult JSON when consuming observations collected through three review routes:

- Global: all associated photos.
- Vertical: top -> oblique -> side, for example 01 -> 21 -> 11.
- Circumferential: adjacent side views 11 -> 12 -> ... -> 18 -> 11, with the equivalent oblique ring supported where available.

These routes share one set of identities and observations. They are not three independent geometric measurements. This focused brief does not specify a new pose solver, learning model or PPFD calculation. Reuse the existing reconstruction and quality contracts. Creating this file executes no implementation or reconstruction.

## 1. JSON responsibilities

| Reference | Contents | Calculator use |
|---|---|---|
| Human growth JSON | Compound-leaf IDs, leaflet counts, unfolding state, growth-shoot and truss counts | Biological count and parent-identity review |
| Existing annotation/association JSON | Image and leaflet IDs, physical-point associations, route membership, visibility, review state, provenance and history | Collect the correct observations for each physical point |
| Capture/calibration/settings JSON | Image registry, camera intrinsics, camera poses and their sources, units, quality policy | Supply existing geometric calculation inputs |

Reuse current editor backups and schemas. Do not create a second independently editable copy of the labels. Existing coordinate arrays in legacy JSON snapshots remain readable. Measurement tables and computed XYZ/residual tables use CSV; JSON references those files and describes their meaning and provenance.

## 2. Reconstruction request manifest

Extend an existing equivalent manifest if possible. Otherwise add a versioned JSON request containing references to:

- plant_id, session_id and capture date;
- human growth JSON;
- immutable annotation snapshot and association/route metadata;
- capture JSON, camera calibration and pose registry;
- existing exported observation CSV files used by the reconstruction adapter;
- quality settings and selected reconstruction mode;
- output destination and relevant reference-geometry version, when applicable.

Record content hashes for referenced inputs. Document path resolution relative to the manifest location, not the shell working directory. Missing/invalid files or inconsistent identities must produce explicit findings before calculation. Changed hashes require an explicit refreshed snapshot or invalidation; do not silently use stale inputs. Preserve unknown values as unavailable/null according to existing schemas, never as fabricated zeros.

Inspect the current field names before choosing final manifest keys. Preserve backward-compatible imports and return clear migration errors without changing original files.

## 3. Growth JSON is a review reference, not geometry

Read the current plant/date file at runtime. Existing examples:

- tomato_photos_organized_/260920/dwt_01/260920/dwt_01_260920.json
- tomato_photos_organized_/260920/dwt_02/260920/dwt_02_260920.json

Use compound_leaves entries and leaflet_count to compare with unique reviewed leaflet identities assigned to that parent across the session. Keep unconfirmed IDs, unknown parents and incomplete coverage separate. Growth-shoot count is not added to leaflet count.

Example: if L01 records eight leaflets and labels contain nine distinct reviewed IDs, display a count/identity review finding. If only seven are observed, report incomplete coverage or a count discrepancy requiring review; do not create a hidden eighth leaflet. Never merge or delete labels automatically to satisfy the JSON count.

The growth JSON does not provide XYZ, 2D positions, angles or spatial order. Array order does not locate leaves. Review and correct positions against photos and actual point observations. Do not edit human growth records to make reconstructed results agree.

## 4. Collect observations from the three routes

1. Load references and confirm plant/session identity.
2. Load existing leaflet and point associations with their review states.
3. Scope a physical-point key by plant, session, leaflet and point ID; preserve parent identity where required by the existing schema.
4. Collect its observations across routes, each additionally identified by image/observation ID.
5. Deduplicate the same saved observation reached through multiple routes. Route count must not increase its statistical weight.
6. Keep contradictory coordinates/associations for review; do not silently choose one or average them.
7. Pass only eligible observations and the selected existing pose registry to the current reconstruction function; report exclusions with reasons.

Local names such as b1/i1 may repeat on different leaflets. Do not join on point_id alone. An organ identity link does not establish a physical-point match. Bbox corners and independent contour indices are not corresponding physical points.

A partially occluded leaflet can have usable visible landmarks. Point eligibility must consider whether that point is observed, separately from whole-leaf bbox eligibility. Unposed photos may assist manual identity review but cannot supply a triangulation ray until a validly represented pose is available under the existing diagnostic policy.

## 5. Existing calculator integration

User flow:

Load session and JSON references -> display growth/count review -> select leaflet and route -> review existing observations -> collect unique eligible physical points -> invoke existing 3D calculation -> inspect linked photos and 3D results.

Retain original-image pixel coordinates, current calibration, frames/units, pose-source distinctions and quality gates. Referencing JSON does not create missing depth or validate a camera pose. Do not force shapes or add points from biological counts.

Keep calculation outputs separate from input annotations: CSV for point coordinates/residuals and JSON for run provenance, statuses and artifact references. Preserve original observations and earlier runs. Label current unvalidated geometry as diagnostic; no automatic upgrade to metric or PPFD-ready status.

## 6. Changes and freshness

- Count-only changes refresh biological findings and input provenance; they do not change XYZ mathematically.
- Accepted identity/point-coordinate changes invalidate dependent geometry through the existing rebuild mechanism.
- Calibration/pose changes invalidate affected geometric outputs.
- Route-navigation-only changes do not alter geometry.
- Store snapshot hashes and revisions so every result identifies the exact inputs it used.

## 7. Focused acceptance checks

- The calculator loads the correct growth, annotation and camera references without modifying them.
- Missing/malformed JSON, mismatched identity, unresolved relative paths and stale hashes are reported clearly.
- A leaflet/observation linked through several routes is counted once.
- Identical local point names on different leaflets remain separate.
- Count mismatches generate findings, not automatic label changes or invented geometry.
- Visible points on partial leaves remain assessable; hidden points stay unobserved.
- Raw image coordinates, legacy backups, histories and human records are preserved.
- Identical observations and poses yield identical reconstruction regardless of navigation route.
- Geometry-relevant changes mark affected outputs stale; count-only and navigation-only changes behave as specified.
- Verify the integrated editor -> server -> existing rebuild -> viewer path, not only a JSON loader in isolation.

## Deliverable

A backward-compatible JSON reference adapter, count/association review display and unique-observation collection connected to the existing 3D calculator, with focused tests and an English implementation report. Do not introduce a parallel app or change the underlying solver under this focused task.

# Manual cross-view organ labels

Implemented in `tools/leaf_point_annotator.html`; generated local copy in
`build/leaf_point_annotator/leaf_point_annotator.html`.

- Existing leaf identities can be selected across views; each physical leaflet keeps
  its existing `(organ_id, leaflet_id)` and physical landmark IDs.
- New flower/bud boxes receive an `organ_id` such as `flower_001`. Each image observation
  retains its separate UUID `annotation_id`. The bbox CSV now includes `organ_id`.
- Same subject: select an existing label, then mark it in another view. Different
  subject: choose the new-label button. Linked image buttons open the reference in the
  opposite pane. Labels are drawn on both images.
- Corrections move one image's complete leaf observations/contour or one selected bbox
  to another label. Splitting creates a new label. Conflicting same-image observations
  and incompatible leaf boundary counts are rejected without overwriting data.
- Box class correction applies to all linked observations in the selected variant and
  is undoable. A wrongly associated observation should be split first.
- Old boxes without organ IDs remain explicitly `unavailable`/unlinked. No inferred
  associations, cross-date tracking, or automatic recognition are claimed.
- JSON backups, local storage, CSV round-trips and existing remote payloads retain IDs.
  Options, links, edits and exports are restricted to the selected image subset.

Validation: 18 Node controller/model regressions passed via
`python -m pytest tools/tests/test_leaf_annotator.py -q`. Browser checks on synthetic
example images verified leaf split/relink, a shared flower ID across two views,
flower split/relink, and reference-view controls; no browser console errors.
File-chooser automation timed out twice, so actual browser file import/download was
not verified in this pass. The CSV import/export controllers were tested directly.
The hosted Claude artifact was not republished. User photographs were not labeled.

The subsequent user request expands priorities to individual-plant physics/vision and
canopy density/lighting comparisons. Growth forecasting is deferred explicitly by the
user until crop time-series data exist. RAG/environment prescriptions are later work.

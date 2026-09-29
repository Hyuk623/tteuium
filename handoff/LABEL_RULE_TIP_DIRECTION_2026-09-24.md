# Model 2 tip-direction labels: class rule (2026-09-24)

Source: the user's decision saved from the human-check page (`human_checks_20260924_142611.json`,
`direction_rule`): "잎끝이 카메라면 front, 뒤면 back".

## Classes (per leaflet box, judged in that photo)

| Class | Rule |
| --- | --- |
| `front` | the leaflet tip points toward the camera (user rule) |
| `back` | the leaflet tip points away from the camera (user rule) |
| `side_left` | the tip points sideways, to the left of the image (Claude's completion, **not yet confirmed by the user**) |
| `side_right` | the tip points sideways, to the right of the image (Claude's completion, **not yet confirmed by the user**) |

## How to make the export

1. In Roboflow, copy the model 1 leaflet boxes of the photo (same box, same annotation id).
2. Change only the class to one of the four above. Do not move or resize boxes.
3. Export per plant; set `direction_labels` for that plant in `tools/plant_pipeline_plants.json`.
   S5 is still `unavailable` after that: its importer is written against the first real export.

Open point: when the tip is between two classes (e.g. diagonal), the rule above does not say which wins.
Ask the user before the importer fixes a tie-break.

# Simulation results tab — 2026-10-19

Request: determine whether the repository simulates observed plants and add a simulation image tab. Inspected tools/microtom_forecast.py and vtc_development.py::collect: conditional forecasts and collected results/viewer.html exist; current remote source explicitly says real geometry has not yet been run. Local build contains no engine result images/viewers. Do not imply current mock plant has a real simulation or run inference.

Implement a separate simulation-result registry and read-only tab supporting copied PNG/JPEG and self-contained exported HTML viewers. Preserve plant/run/scenario/time/input-origin/file-hash metadata. Local CLI imports explicitly selected results; no automatic mapping by filename. Sandbox HTML without same-origin/network access. Empty state must be honest. Validate registration, persistence, plant isolation, traversal protection and asset headers; keep server available after restart.

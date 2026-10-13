# Build prompt — mobile daily-record web form, cloud-hosted (2026-10-12)

**Implementer: a Claude session that has the `Artifact` tool** (claude.ai chat / Cowork). The Claude Code CLI
cannot publish artifacts, so this one does not go to a CLI session. Load the `artifact-capabilities` skill
BEFORE writing any page code, and declare the shared-database (`db`) capability — browser storage alone is wrong
here, because the rows must survive a phone change and must be readable back by Claude.

## 0. Why cloud, and what this replaces
The measurements happen standing at the tray with a phone in one hand and an EC meter in the other, often while
the PC is off. A hosted page with a shared database needs no install and no local server. It replaces hand-typing
into `data/records/*.csv`, where free text reliably breaks three things: fixed vocabularies (`axis`, `tray_id`,
`event_kind`), the `__status` convention, and the difference between **blank (unavailable) and 0**.

Read first: `build/nutrient_records_template/` (README_KO + the two CSVs — the column order is the contract),
`build/side_shoot_registry_template/side_shoot_registry.csv`,
`build/truss_registry_template/truss_registry.csv`, `data/records/env_light_20261010/`,
`docs/정의집_토마토_2026-10-11.md` §axes and §nutrient rows, `handoff/MTG_CONVENTION_2026-10-10.md` A4/A5
(axis names and the two-leaf registration rule).

## 1. Hard data rules (these decide the build, not the looks)
1. **Blank is `unavailable`, never 0.** An empty numeric field stores no value and the row's `<field>__status`
   becomes `unavailable`. A typed `0` stores 0 with status `measured`. The UI must make this visible — show
   "미측정" on an empty field rather than a grey zero.
2. **Append-only.** No row is ever edited or deleted in place. A correction writes a NEW row carrying
   `supersedes = <old row id>` and a reason. (Same discipline as `handoff/LOG.md`.)
3. **Time**: device clock, always stored as ISO 8601 with `+09:00` (Asia/Seoul fixed). Default = now, editable to
   a past time within 48 h; a future time is refused.
4. **Fixed vocabularies, chosen not typed**: `tray_id` from the settings list, `event_kind` ∈
   {`supply`, `measure_only`, `remove`}, `axis` ∈ {`M`, `S1`, `S2`, `S3`, `S4`}, `axis_state` ∈
   {`axis_shoot`, `substem`}, `plant_id` from the settings list.
5. Every row also stores `observer` (default from settings), `source_kind = measured`, `method` (e.g. `EC_meter`,
   `ruler`, `jug`), `app_version`, and the client-generated `row_id`.
6. **Offline queue.** Writes that fail (no signal at the shelf) are queued in `localStorage` wrapped in
   try/catch, the pending count is shown, and they flush on the next successful load. A queued row keeps the
   time it was measured, never the time it was sent. The page must render and accept input with storage
   unavailable or the db unreachable.
7. No photo upload. The HEIC originals stay on the phone/PC — the pipeline reads them from the folder by hash.
   The form only records that a capture session happened and which plants were in it.

## 2. The four sections (Korean UI, in this order)
**① 촬영** — `세션` (11:00 / 00:00 / 기타 + 시각), 개체 체크리스트(settings list, tap to toggle, 전체 선택),
`비고`. Purpose: a missed plant is visible later. Shows the previous session's time and count.

**② 양분 (트레이별 1건)** — tray chips first, then fields **in the order the work actually happens**:
급액 전 `고인 깊이(mm)` → 급액 전 `고인 EC(mS/cm)` → `급액량(ml)` → `급액 EC(mS/cm)` → 급액 후 `고인 깊이(mm)`
→ (선택) `질산 시험지(mg/L)`, `수온(℃)`, `덜어낸 양(ml)`, `비고`.
`event_kind = measure_only` hides the supply fields. **Show that tray's last values beside each field** so a
drift or a typo is obvious at the moment of entry. The blank tray is an ordinary tray chip marked `대조`, and the
section header states that skipping it stops the uptake calculation.

**③ 점등·소등** — two large buttons `점등 지금` / `소등 지금` stamping the time, plus a manual time field for
"아까 켰음". Shows today's pair and the resulting hours; warns if a day has an on without an off.

**④ 새로 생긴 것** — two small forms:
- 곁순: `plant_id`, `axis`, `parent_rank`(정수, 본줄기 겨드랑이 몇 번째 잎), `axis_state`, `first_observed`,
  `비고`. Helper line: "잎 2장이 함께 보이면 `axis_shoot`, 그 두 잎이 완전히 펴지면 `substem`으로 한 줄 더".
- 화방: `plant_id`, `axis`, `above_rank`(그 축에서 몇 번째 잎 위), `first_observed`, `비고`.
Both list what is already registered for that plant so nothing is registered twice.

**설정** — tray list (id + 대조 여부), plant list, observer, EC-meter calibration note. Stored in the db so a new
phone inherits it.

## 3. Database and export
One collection per record type: `capture_sessions`, `nutrient_log`, `light_events`, `side_shoots`, `trusses`,
`settings`. Document id = `<ISO time>_<row_id>` so rows sort chronologically. Store raw values plus each
`__status`; never store a computed value (pool volume, DLI, hours) — those are derived later in the pipeline.

Export: a per-collection CSV download **with the repo template's column order unchanged**, so a file can go into
`data/records/` as-is. `nutrient_log` and `tray_spec` must match `build/nutrient_records_template/`;
`side_shoots` and `trusses` must match their registry templates. Rows carrying `supersedes` are exported too,
marked — the consumer decides, the form never silently drops a correction.

## 4. Mobile UX requirements
One-handed reach, 44 px+ targets, `inputmode="decimal"` on every numeric field, unit printed inside the field,
no horizontal scroll at phone width, dark mode from the same tokens, section tabs that remember the last tab
per viewer (`localStorage`, try/catch). After each save: a single confirmation line with what was written and an
`되돌리기` that writes a superseding row, not a delete.

## 5. Validation (messages in Korean, warn rather than block unless noted)
- Future time → **block**. Time more than 48 h old → confirm once.
- Same tray + same `event_kind` + same calendar day already recorded → warn, allow (a second watering is real).
- 급액 후 깊이 < 급액 전 깊이 → warn ("급액했는데 깊이가 줄었습니다 — 값 확인").
- Pool EC changed by more than 50 % since that tray's last reading → warn.
- `parent_rank` / `above_rank` not a positive integer → block.
- A side shoot registered as `substem` with no earlier `axis_shoot` row for that axis → warn (the two-leaf rule
  expects the earlier row).
- Blank tray not recorded on a day when a planted tray was → warn on that day's summary.

## 6. Acceptance
Save a row with every numeric blank → the export shows empty fields with `unavailable`, not zeros. Save a
`0` → it exports as `0` with `measured`. Kill the network, save two rows, reload → both arrive once, with their
measured times. Export each collection and diff the header against the template file. Open at 390 px width →
no horizontal scroll. Reload with `localStorage` blocked → the page still works.

## 7. Out of scope
Photo upload, in-place editing, charts and analytics, any computed agronomic value, writing into
`data/records/` (the export is handed to the human, who copies it — agents do not write that folder).

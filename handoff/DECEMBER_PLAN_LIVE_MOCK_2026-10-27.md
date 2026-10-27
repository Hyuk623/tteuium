# December delivery plan and continuous mock feed

User requests delivery by the final week of December 2026 and continuous virtual sensor input. Planning window: October 27–December 31, with acceptance December 28–31 and feature freeze December 18. Smart-farm applicability is background motivation, not extra MVP scope.
Inspect: local seed_demo --live currently sends every minute, exits on HTTP outage; dashboard refreshes every 30 seconds, queries cap readings at 10,000. Pages is a static snapshot.
Changes: document dated delivery milestones and acceptance gates; configurable mock interval, default 300 seconds to keep a rolling 30-day window within the current read cap, retry transient network errors. Keep synthetic provenance, existing data, analysis engine and static Pages semantics. Validate tests and actual successive HTTP observations.

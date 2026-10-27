# Calendar date editor

Request: replace the always-visible journal composer with a date-triggered popup.
Current behavior: calendar selects a filter and the composer always records the current timestamp.
Plan: native modal dialog with selected date, existing daily entries, save/cancel and Escape; retain draft on dismissal. Add nullable action_date separately from creation timestamp, migrate existing SQLite databases without modifying records, support static demo storage. Calendar/list use action_date with legacy timestamp fallback. No analysis engine changes.
Validation: date persistence and migration tests, full product tests, JavaScript syntax, browser open/close and selected-date save; deploy personal fork.

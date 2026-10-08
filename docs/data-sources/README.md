# Football source counts — 2025/26

Updated 7 October 2026; generated UTC 2026-10-07T01:00:09.261138+00:00.

Empty or dash cells in an existing numeric column are zero under the user-specified policy. Original snapshots are preserved. Absent rows/columns, failed requests, explicit N/A, identity text and unavailable calculated features are not manufactured as zeros. No 90% gate applies.

| Source | Players | Native player fields | Performance columns | Event attributes | Scope |
|---|---|---|---|---|---|
| opta | 2685 | 87 | 67 | 0 | complete cached inventory; retained records |
| pitchapi | 2688 | 233 | 127 | 18 | complete cached inventory; retained records |
| understat | 2693 | 18 | 12 | 0 | complete cached inventory; retained records |
| whoscored | 2842 displayed entries; 69 captured IDs; full unique total not yet deduplicated | 117 | 113 | 0 | partial/blocked/nonqualifying; see source report |
| fbref | unknown | unknown | unknown | unknown | partial/blocked/nonqualifying; see source report |
| sofascore | unknown | unknown | unknown | unknown | partial/blocked/nonqualifying; see source report |
| fotmob | 17 captured IDs in one team sample; full total unknown | 13 | 2 | 0 | partial/blocked/nonqualifying; see source report |
| statbunker | unknown | 88 | 67 | 0 | partial/blocked/nonqualifying; see source report |
| statsbomb | 0 | 0 | 0 | 0 | partial/blocked/nonqualifying; see source report |


Native totals count collected source columns, not independent abilities. They include identity and context; Scout-calculated columns are excluded. Player totals are distinct provider IDs unless explicitly labelled as sample IDs or displayed rows. Unknown means not measured, not zero. StatsBomb zero means no qualifying target-season competition.

## Source reports

- [Opta](opta.md)
- [Pitchapi](pitchapi.md)
- [Understat](understat.md)
- [Whoscored](whoscored.md)
- [Fbref](fbref.md)
- [Sofascore](sofascore.md)
- [Fotmob](fotmob.md)
- [Statbunker](statbunker.md)
- [Statsbomb](statsbomb.md)

## Reproduce

[Four-source master dataset and merge rules](master-dataset.md).

```powershell
scout audit-data-sources
scout collect-source-tables --budget 160
```

Browser observations are kept separately in `data/source-audit/2025-26/browser-whoscored-20261007/`. Static collection alone does not capture the WhoScored browser tables. No database migration, source activation or rating change occurs.

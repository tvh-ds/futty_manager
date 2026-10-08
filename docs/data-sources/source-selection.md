# Source stack status

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

Opta and PitchAPI remain the existing core; Understat remains private. This update inventories counts rather than ranking sources by coverage. WhoScored is now confirmed browser-accessible and supplies a Fouled column. Full collection, player identity mapping and public reuse remain separate implementation work.

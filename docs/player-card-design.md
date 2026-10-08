# Player cards and dashboard revision — 7 October 2026

Shared cards on Players, the Liverpool pitch and bench use an original beveled-metal frame, layered facets, portrait lighting and grounded shadows. Source Sans 3 remains the control and data font. No game artwork or fictional player faces are used.

## Card finishes

| Raw OVR | Finish |
|---|---|
| Below 50 | Cool graphite |
| 50–69.99 | Burnished bronze |
| 70–79.99 | Silver |
| 80–89.99 | Champagne gold |
| 90 and above | Amethyst elite |
| Unavailable | Neutral slate |

Bands use unrounded ratings; scores are not capped at 99. Position, country flag and club crest form a vertical identity column. Missing identity assets use explicit flag/shield placeholders. Country is never inferred from league, name or club.

Portraits and crests come from checksum-verified cached PitchAPI metadata. Liverpool country labels use the existing sourced roster. Two additional national-team labels are recorded in `src/scout/card_identity.py`: [Harry Kane, England Football](https://www.englandfootball.com/england/mens-senior-team/squad/harry-kane) and [Kylian Mbappé, FFF](https://www.fff.fr/equipe-nationale/joueur/8566-mbappe-kylian/fiche.html). Labels describe national-team representation, not all citizenships. Broader country metadata remains incomplete. Local SVG flags are from flag-icons 7.5.0; its MIT licence is retained in `frontend/public/flags/LICENSE.txt`.

## Browser annotation changes

| Comment | Implemented change |
|---|---|
| 1 | Removed the snapshot/zero-filled banner from Players details. |
| 2 | Removed the shared ability-view snapshot banner. |
| 3 | Removed repeated peer/gap/reliability footers. Full evidence remains inspectable/exportable. |
| 4 | Reduced feature padding, headings, distribution height and inspect-button size. |
| 5 | Removed the radar scale caption; dynamic rings still accommodate uncapped scores. |
| 6 | Sources & mapping contains season, identity status, providers and a short provenance note. |
| 7 | Renamed the disclosure to Full attributes list. |
| 8 | Rating method contains shrinkage, standardization, weighting, peer eligibility and zero handling; complete evidence export remains. |
| 9 | Plain X close control with accessible label and focus treatment. |
| 10 | Removed visible season/evidence card footers; page and accessible context remain. |
| 11 | Desktop pitch/card heights respond to available viewport and formation spacing. All eleven fit at 1384 × 704. |
| 12 | Pitch-card click opens details; hover/focus exposes Sub and Explore. Bench cards open details unless previewing a substitution. Drag and keyboard swap controls remain. |
| 13 | Removed Rating settings and its drawer. |
| 14 | Removed STRICT from the starting-XI summary. |
| 15 | Renamed Link chemistry to Chemistry and removed the DEMO badge. Separate familiarity/evidence context remains. |
| 16 | Removed the lineup/link-coverage summary block. |
| 17 | Replaced the LFC placeholder with Liverpool's sourced crest. |

## Verification and limits

Production build and focused card/catalogue checks passed. Desktop visual review confirmed eleven complete pitch cards, sourced flags/crests, compact analysis and click-to-open details. Screenshots are in `docs/screenshots/`.

The browser's mobile viewport override did not take effect during final verification; a mobile visual pass is not claimed. Mobile styles retain compact cards, bottom sheets and a horizontally pannable pitch. Reduced-motion styles remove transitions. Rating calculations, source priorities and identity matching are unchanged. Chemistry remains illustrative; non-ST ability models remain unavailable.

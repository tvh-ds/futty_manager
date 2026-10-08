# Striker data feasibility — checked 6 October 2026

The full requested monthly numeric product remains incomplete. A new direct probe of Understat's public-page AJAX interface retrieved and validated **2,121 real player records for2026/27 and2,775 for2025/26 across all five leagues**, privately. Seven of the37 unique requested metrics can be derived from those league aggregates. These counts include all positions, not reviewed striker cohorts. **No real rated release is activated.**

| Source | Verified evidence | Engineering decision |
|---|---|---|
| FotMob | Its published terms disallow automatic services and systematic/regular use. The player-page fetch did not provide a usable numeric response in this environment. | No monthly crawler, hidden endpoint workaround or numeric coverage claim. [Terms](https://www.fotmob.com/terms-of-service). |
| FBref | Sports Reference's20January2026 announcement states its advanced feed was removed; the current FBref home page links that announcement. Direct blog fetch returned403, while its official indexed announcement was available. | Do not implement the old possession/passing/GCA/defense-table assumption as a working current source. [Official announcement](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/), [current site](https://fbref.com/en/). |
| API-Football | Official documentation and provider guide describe player totals and statistics, but no account/key is configured here. Free historical/current entitlements and actual responses remain untested. Public-use conditions require review. | Disabled provisional adapter; retain absent fields and refuse incomplete rating activation. [Provider guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide), [terms](https://api-sports.io/terms). |
| Historical StatsBomb Open Data | Existing historical research uses eligible older event data, documented separately. | It does not establish current2026/27 five-league coverage; do not silently substitute historical observations for current squad skills. |
| Understat | The initial plain endpoint request returned404. Its own `league.min.js` calls `getLeagueData/{league}/{season}` with the normal jQuery AJAX header. Using that public interface returned actual teams/players/fixtures JSON in all five leagues. Real numeric field normalization and snapshot checksums are now verified. | One-off private probe implemented; no publication or recurring collection enabled. Only7/37 metrics are available from these league aggregates. Identity/role mapping, permissions and the remaining advanced measurements are still required. [Official page](https://understat.com/league/EPL/2026). |
| Sofascore | Its official FAQ says provider agreements prevent supplying sports-data API endpoints. | No unofficial endpoint integration. [Official FAQ](https://sofascore.helpscoutdocs.com/article/129-sports-data-api-availability). |

A direct read of the official StatsBomb competition catalogue on2026-10-06 returned80 records (SHA256 `e6cd42f5d8956d6aa30fb917ce8d4c3b3df1879a93f02f8feba820930a6971fa`). None of the five senior men's league catalogues contained2024/25 or newer. Latest listed seasons: Premier League2015/16, LaLiga2020/21, Bundesliga2023/24, SerieA2015/16, Ligue12022/23. These are catalogue listings, not proof of complete match coverage. [Official catalogue](https://github.com/hudl/open-data/blob/master/data/competitions.json). Local metadata reports are `.cache/striker-source-probe-20261006.json` and `.cache/understat-source-probe-20261006.json`; neither is a player-statistics release.

The conservative API-Football adapter can potentially derive13 of37 requested unique metrics when corresponding counts and denominators are actually present: NPG/90, shots/90, SoT/90, SoT%, assists/90, key passes/90, take-ons attempted/successful/success%, duels won/90/success%, fouls won/90 and interceptions/90. This is a **schema mapping**, not verified account coverage or numeric correctness. Missing penalties leave NPG unavailable; pass accuracy is not interpreted as completed-pass count. Overall duels are not treated as independent from aerial duels.

The remaining24 are not established by that adapter: npxG/90, NPG−npxG/90, goals/non-penalty shot, npxG/non-penalty shot, box shots, open-play xG, headed shots, opposition box touches, offsides, xA, SCA, passes into penalty area, through balls, pass completion, box carries, final-third carries, progressive carrying distance, miscontrols, dispossessed, aerial wins/90, aerial win%, attacking-third tackles, recoveries and blocks. Their raw values must remain null until a permitted source or eligible events prove their definitions and coverage.

Required acceptance evidence before a real release:

1. Authorized free collection/public display and an actual successful numeric sample for every required field.
2. A common completed or current evaluation window with adequate minutes, across all five leagues; separate same-league cohorts until league adjustment is evaluated.
3. Reviewed exact player/season/team mappings, transfer-stint treatment, numerator definitions and units. Never infer event context or equate different provider definitions casually.
4. A monthly run producing a complete immutable release, freshness metadata, coverage/quarantine report, smoke-tested activation and demonstrated failed-refresh preservation.

Provider keys and cloud accounts remain placeholders as requested. Adding a scheduler or a fictional reference population does not close these gates.

A further check of the official API-Football coverage/pricing pages on6October confirms advertised competition coverage,100 daily free requests and season restrictions on the free plan. The advertised list does not prove that this unconfigured account can retrieve2026/27, all37 measurements or a consistent observation cutoff. Actual responses and public-use rights remain unverified. [Coverage](https://www.api-football.com/coverage), [pricing](https://www.api-football.com/pricing).

## Verified Understat numeric probe

The implemented `scout probe-understat NEW_OUTPUT_DIRECTORY --season 2026` command performs five bounded requests, validates actual source fields, retains private checksummed bronze plus normalized measurements/quarantine/coverage and never activates a release. The normal AJAX header is required by the same interface used by the public page; no authentication, challenge evasion or access-control bypass was used.

| League | Validated2026/27 players | Maximum source minutes | Players with900 minutes | Validated2025/26 players | Players with900 minutes |
|---|---:|---:|---:|---:|---:|
| England |421|450|0|537|340|
| Spain |461|720|0|600|345|
| Germany |367|360|0|499|284|
| Italy |448|450|0|586|338|
| France |424|450|0|553|278|

Both actual runs quarantined0 rows. All2026/27 league responses list their latest completed fixture on20September2026. The fixture timestamps have no verified timezone; they are retained as source times and never relabelled as approved UTC observation cutoffs. Availability of pages labelled2026/27 therefore does not by itself prove up-to-the-minute coverage. Current-source exposure cannot support the900-minute season-rating rule; completed2025/26 has sufficient exposure across positions, but detailed ST eligibility/cohorts are unreviewed.

Verified derived metrics: NPG/90, npxG/90, (NPG−npxG)/90, shots/90, assists/90, xA/90 and key passes/90. Non-penalty shot counts are absent, so goals/shot and npxG/shot remain unavailable; total shots are not substituted. All carrying, duel and defensive measurements remain unavailable from this response. An API-Football/Understat union could potentially cover16/37 metrics if account responses and compatible definitions are verified; that is a mapping estimate, not demonstrated merged coverage.

Actual private snapshots are under `data/striker-source-probes/understat-2026-57246e766d844f649b3127fab706756c/` and `data/striker-source-probes/understat-2025-426b9ed19c784a8ea498ea97f8731a7d/`. These ignored research artifacts are not serving releases. The user selected completed **2025/26 performance data** for the Liverpool2026/27 planning squad. The source configuration now targets2025; squad membership and performance seasons remain separate. A permitted source/export for missing advanced data is still pending.

## Verified shot-level extension

The public player page's own `getPlayerData/{id}` response supplies shots. The new `scout probe-understat-player OUTPUT LEAGUE_BRONZE_JSON PLAYER_ID --season 2025` command makes one bounded request and writes private checksummed evidence. It joins shots to completed fixture IDs in the exact league and season, rejects duplicate IDs/unsupported categories, and reconciles shot count, non-penalty goals and summed npxG against league aggregates before deriving measurements. Different seasons and leagues are excluded. Fixture dates cannot be relabelled into another season.

Actual Alexander Isak (`5232`) evidence reconciled17 shots and3 non-penalty goals for2025/26. Source minutes are717, so he does not satisfy the900-minute rating threshold. Actual Cody Gakpo (`11296`) evidence reconciled87 shots; the private snapshot is `data/striker-source-probes/gakpo-2025-ca35b97303e44fcba6fea32d238d692d/`.

This proves four additional metrics for these inspected players: goals/non-penalty shot, npxG/non-penalty shot, open-play xG/90 and headed shots/90. Combined with league aggregates, **11/37 features** are numerically verified. It does not establish shot completeness for every player across five leagues. SOT and box-shot metrics are withheld until result-category and coordinate definitions are approved. The remaining26 fields stay unavailable; no six-ability or overall ST rating is fabricated. Reviewed eligibility, source permissions and complete cohorts are still required for activation. This adapter does not enable bulk collection, monthly scheduling or public display.

## StatsBomb Open Data recheck requested by the user

On6October2026, the official repository's current revision remained `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. A fresh bounded check archived its catalogue, README, licence, all five latest league match lists and one actual event file under `data/striker-source-probes/statsbomb-check-8571a3fefc7d4edcbf4580e8e7970bbb/`, with URL/byte/checksum provenance in `coverage.json`.

| Senior men's league | Latest available season | Listed matches |
|---|---|---:|
| Premier League |2015/16|380|
| La Liga |2020/21|35|
| Bundesliga |2023/24|34|
| Serie A |2015/16|380|
| Ligue1 |2022/23|32|

None has2024/25 or newer, including the selected2025/26 performance window. Counts describe listed matches; they do not certify event completeness or suitable role cohorts. Distinct clubs appearing in a selected-match sample do not establish full-league coverage.

The actual Union Berlin–Bayer Leverkusen event file (`3895292`,6April2024) contains3,843 events, including905 Carry,26 Miscontrol,23 Dispossessed,76 Duel,101 Ball Recovery,45 Block,29 Dribble,25 Foul Won and20 Interception events. This proves numeric event availability, not exact equivalence to all37 requested metric definitions. Touch counts, progressive distances and duel denominators still need explicit provider-specific definitions. Historical events cannot be merged into2025/26 totals or represented as current Liverpool player evidence.

StatsBomb remains usable for the existing historical xG/action-value research and a separately labelled historical feature experiment. Its [official README](https://github.com/hudl/open-data#terms--conditions) requests source acknowledgement and logo attribution for published analysis; the full licence is archived for review. No current serving release or source configuration was replaced by this check.

## PitchAPI update — 6 October 2026

The user has confirmed free access and reuse rights and configured a private key.
Authenticated 2025/26 collection is implemented, including raw snapshots, checksums,
resumption, strict normalization, coverage, invalid-match quarantine and opt-in refresh
integration. All five expected league fixture inventories are present (1,752 matches).
The first live 15-match sample parsed 462 player/league observations. Opposition-box
touches and offsides are present in actual base statistics, with omissions kept unknown.
Attacking-third tackles remain unavailable; complete ratings and reviewed ST identity
cohorts are still required before activation. See [PitchAPI integration](pitchapi-integration.md).

Earlier source research above remains historical context.

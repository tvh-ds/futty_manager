# Alternative striker data sources — checked 6 October 2026

Target: the 26 features missing from the inspected Understat samples, completed2025/26, senior men's top-five leagues, free ongoing access and permitted public portfolio use. Documentation, website visibility and tested numeric coverage are different evidence levels.

## PitchAPI — implemented and authenticated

Update: the user confirmed free access and reuse rights and configured the key locally.
The new authenticated adapter successfully parsed 15 matches (three per league),
462 player/league observations, and completed 2025/26 inventories totaling 1,752 matches.
Live stats also establish opposition-box touches and offsides, although optional fields
are omitted in some appearances and remain unknown. Attacking-third tackles remain
unavailable. Full season collection is resumable; publication still requires complete
features and reviewed striker identities. See [integration notes](pitchapi-integration.md).

Full backfill result: all 1,752 match payload sets fetched; 1,747 valid matches,
five quarantined for unmatched shot actors, 2,770 player/league rows. No rated release
was activated. Optional-field omissions are material, beyond the missing tackle metric.

The paragraph below records the earlier documentation-only research state.

[Official documentation](https://pitchapi.dev/) advertises free access, five-league coverage and history from2021. No authenticated sample was tested. Collection/display rights remain unverified. Its inferred carries, modified SCA and interception definitions require separate versions; xAG is not xA. Advanced coverage varies. Three gaps remain undocumented: box touches, offsides and attacking-third tackles. The match timeline is not a full action feed.

Documented leads for the other23 metrics, grouped:

| Requested features | Candidate surface |
|---|---|
| SOT/90, SOT%, box shots/90 | Shots |
| SCA/90 | Creation |
| PPA/90, through balls/90, pass% | Passing |
| Take-ons/90, successes/90, success% | Carrying |
| Box carries/90, third carries/90, progressive distance/90 | Carrying |
| Miscontrols/90, dispossessions/90 | Carrying |
| Duels won/90, win%, aerial wins/90, aerial% | Player stats/defending |
| Fouls won/90, recoveries/90 | Player stats |
| Interceptions/90, blocks/90 | Defending/player stats |

These are provisional schema leads, not accepted values or complete league coverage.

## Other sources checked

| Source | Evidence | Decision for Scout |
|---|---|---|
| Opta Analyst | Its [public hub](https://theanalyst.com/competition/premier-league/stats) actually rendered numeric tables. Browser inspection confirmed through-ball counts, pass successes/attempts, interceptions, possession won, blocks, ground/aerial duel successes/attempts and progressive carry distance. The inspected season was2026/27; its season button was disabled. Five league navigation entries are present, but2025/26 access and equal field coverage were not verified. | Strong reference/permission lead. [Terms](https://www.statsperform.com/terms-and-conditions/) limit website material to personal noncommercial use and require written consent for reuse on another website. Do not enable a public serving pipeline from visible tables. Possession won must not silently become recoveries. |
| xG Stat | [Product page](https://www.xgstat.com/fbref-alternative) advertises advanced player metrics and a2025/26 archive. Premier League has event depth; three other leagues have statistics depth. Ligue1 is not listed there. | [Terms](https://www.xgstat.com/terms), sections3–4, prohibit automated extraction and redistribution without written permission. Useful for personal reference or an explicitly granted partnership, not an automatic replacement crawler. |
| DataMB | [Guide](https://datamb.football/guide/) lists five-league coverage, weekly updates and100+ raw metrics in Pro. Free radars use seven metrics and percentiles rather than raw values. Completed-season database eligibility is1000minutes, which omits some players eligible under Scout's900-minute rule. | No verified free raw-data API/export. Existing percentiles cannot reconstruct raw totals or Scout's own cohorts. Pro access does not establish redistribution permission; [terms](https://datamb.football/tos/) need review for any proposed agreement. |
| Sportmonks | [Permanent free plan](https://www.sportmonks.com/football-api/free-plan/) covers Danish Superliga and Scottish Premiership. Wider access is a time-limited trial or paid plan. | Does not satisfy free ongoing top-five data. No subscription or trial started. |
| FootyStats | [Player schema](https://footystats.org/api/documentations/player-individual) documents pass totals/completions, duel totals/wins, dispossessions and aerial values. Some descriptions inconsistently say player versus team; averages and percentages do not always have raw denominators. [Pricing](https://footystats.org/api) lists paid subscriptions; its public example key is for older EPL data. | Potential partial paid source, outside the current free-only scope. Sample responses and semantics need validation before importing anything. |
| TheStatsAPI | [Official comparison](https://www.thestatsapi.com/blog/thestatsapi-vs-api-football) states no free tier and a7-day trial. Its about page uses different wording about a free tier. | Treat current offering as unresolved/paid until clarified; no free ongoing acceptance, account or trial. |
| football-data.org | [Official reference](https://www.football-data.org/documentation/quickstart) documents fixtures, squads, scorers and basic person/match aggregates. | No documented solution for the missing carrying/possession/duel registry. Useful for basic context only. |
| SkillCorner Open Data | [Official article](https://www.skillcorner.com/us/articles/skillcorner-open-data-3-building-archetypes) identifies2024/25 Australian A-League physical, passing and off-ball-run aggregates. [Repository](https://github.com/SkillCorner/opendata) provides selected tracking matches. | Useful separate tracking/physical research, not completed2025/26 five-league striker totals. |
| Squawka | A2025/26 EPL stats page is indexed, but direct retrieval returned403. [Terms](https://www.squawka.com/us/terms-and-conditions/) restrict use to private noncommercial purposes and prohibit commercial scraping. | No bypass or coverage claim. Requires clarification for public reuse. |
| Statbunker / Futmetrik | Public sites and indexed player pages were found. No suitable documented free API, complete field export and reuse grant were verified in this check. | Unproven leads; do not claim they close the missing features. |

## Concrete validation before implementation

1. Obtain the provider's free key through its own account process; keep it in a local environment variable, never chat or frontend code. Confirm storage, derived ratings, public display and monthly refresh rights.
2. Retrieve actual2025/26 league match inventories. Check completeness by league and quantify advanced-data availability rather than interpreting a missing match as zero events.
3. Inspect player and advanced responses for one Liverpool fixture and one fixture in each other league. Audit raw denominators, minutes, player IDs, stints and missing fields. Documentation examples are not live proof.
4. Reconcile aggregate totals and definitions. Carry/SCA/interception differences require versioned features or an explicitly accepted model change; no silent substitution into the existing weights.
5. Only then backfill, evaluate role eligibility and same-league cohorts, and test release gates. If required features remain unavailable, report missing ratings rather than redistributing their weights.

No application code, ranking, source activation, accounts or paid services were changed by this research. `continue_strictly_mainplan.md` was not updated.

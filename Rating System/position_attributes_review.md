# Position attribute proposals — review index

**Eight draft registries · 2025/26 · 7 October 2026.** Each file has six abilities, parent-to-OVR weights, within-parent feature weights, exact master inputs, calculations, directions, observed-input counts and limits. All weights are proposed Scout defaults for your review; nothing is activated in the engine.

| Role | Six abilities and overall weights | Specification |
|---|---|---|
| LW / RW | Carrying/1v1 24%; Creation 22%; Scoring 20%; Box Threat 14%; Retention 10%; Defensive Support 10% | [lw_rw_attributes.md](lw_rw_attributes.md) |
| CM | Progression 24%; Retention/Circulation 20%; Creation 18%; Recovery 18%; Duels 12%; Goal Threat 8% | [cm_attributes.md](cm_attributes.md) |
| CAM | Creation 30%; Combination/Retention 18%; Carrying/1v1 18%; Scoring 16%; Box Threat 10%; Defensive Support 8% | [cam_attributes.md](cam_attributes.md) |
| CDM | Screening/Recovery 24%; Ground Duels 18%; Retention 20%; Build-Up/Progression 20%; Aerial Contribution 10%; Discipline 8% | [cdm_attributes.md](cdm_attributes.md) |
| LM / RM | Wide Creation 24%; Carrying/Progression 20%; Retention 16%; Defensive Support 20%; Duels 10%; Goal Threat 10% | [lm_rm_attributes.md](lm_rm_attributes.md) |
| CB | Ground Defending 24%; Aerial Defending 22%; Reading/Interventions 18%; Build-Up Passing 16%; Carrying/Control 10%; Discipline 10% | [cb_attributes.md](cb_attributes.md) |
| RB / LB | Ground Defending 20%; Recovery/Cover 16%; Progression 18%; Wide Creation 22%; Retention 14%; Aerial Contribution 10% | [rb_lb_attributes.md](rb_lb_attributes.md) |
| GK | Shot Stopping 40%; Claims 15%; Sweeping 10%; Build-Up Distribution 15%; Long Distribution 10%; Ball Security 10% | [gk_attributes.md](gk_attributes.md) |

Left/right positions are grouped. LM/RM remains distinct from LW/RW because the wide-midfield role has greater defensive and circulation responsibility. Wing-backs may reuse full-back features with a later separate overall preset. No forced ST weights or generic 1.5 multiplier are applied to these new proposals.

## Design choices

**Use measured football functions.** EA's six outfield families and goalkeeper families are a useful presentation reference, but the current data cannot reproduce speed, reaction time or pure strength. Scout's ability names therefore describe retrievable production and outcomes. EA's published chemistry-style table is a legacy gameplay reference, not a statistical recipe for real-world OVR. [Official EA reference](https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf).

The more recent FC 26 documentation explains attribute-dependent gameplay and PlayStyles. It does not supply the event-statistic weights used in these Scout proposals; gameplay tuning and statistical player evaluation are different calculations. [EA FC 26 gameplay documentation](https://www.ea.com/games/ea-sports-fc/fc-26/news/pitch-notes-fc26-gameplay-deep-dive).

**Separate style from quality.** Positional radar research emphasizes creation, carrying and scoring for attacking roles, contextual defensive interpretation, and distinct goalkeeper functions. Scout's allocation is an inference from that research and its actual inventory. It does not claim access to commercial OBV, pressure-adjusted models or private club formulas. [StatsBomb position templates](https://blogarchive.statsbomb.com/articles/soccer/new-statsbomb-radars-2023-update/).

**Prefer expected creation and open-play measures.** Give open-play xA/chances more weight than realized assists. Keep shot production and execution distinct; avoid accidentally making set-piece responsibility the main creative signal. Ordinary pass completion receives limited weight, not a blanket playmaking label.

**Keep defensive proxies honest.** Ground/aerial outcomes are preferable to counting tackle attempts alone, but even duel success is context-dependent. Centre-back ratings especially need review alongside tactical style and video. [Centre-back scouting research](https://blogarchive.statsbomb.com/articles/soccer/how-do-you-scout-for-centre-backs-statistically/). Full-back templates balance delivery and safety rather than assuming every full-back must cross frequently. [Full-back recruitment example](https://blogarchive.statsbomb.com/articles/soccer/using-statsbomb-iq-for-player-recruitment-full-backs/).

**GK uses retained raw evidence.** The wide master has Opta shot-stopping inputs for 190 rows. PitchAPI appearance observations contain claim/sweep/distribution fields for 188 provider player/league records, plus general passing/control fields. Five proposed GK parents need new aggregation and definition validation before a six-ability season rating is possible. Ball Security and Sweeping are provisional proxies, not measured catching technique or positioning. [Goalkeeper metric research](https://blogarchive.statsbomb.com/articles/soccer/introducing-goalkeeper-radars/).

## Review in this order

1. Six ability names and relative overall priorities for each role.
2. Feature membership, directions and within-ability weights.
3. Proxy limitations and whether any parent should change after richer data is available.
4. Cohort assignment and data-window compatibility before implementation.

[Shared methods](position_attribute_methods.md) specify source-bundle priority, per-90/ratio rules, pooled top-five role peers, shrinkage, re-standardization, uncapped ratings and zero-filled-only redistribution. Each proposed ability and OVR weight vector totals 100%.

The private master, current serving catalogue, ST registry and application are unchanged. `continue_strictly_mainplan.md` remains untouched.

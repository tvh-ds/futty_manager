# Pitchapi — player and feature counts

**Performance season: 2025/26.**

Distinct provider player IDs: **2688**. Player/league records: **2770**. Player/team or normalized records: **2770**.

Native player-field paths: **233**; season/match performance columns: **127**; event-attribute paths: **18**. Identity, exposure, formatting and provider-rating fields remain in the native total. Scout-calculated columns are excluded from source feature totals.

Empty or dash cells in an existing numeric column are zero under the user-specified policy. Original snapshots are preserved. Absent rows/columns, failed requests, explicit N/A, identity text and unavailable calculated features are not manufactured as zeros. No 90% gate applies.

## Player counts by league

| League | Distinct source players |
|---|---|
| England | 537 |
| Spain | 598 |
| Germany | 499 |
| Italy | 586 |
| France | 550 |

## All native player columns

Cells count distinct players with numeric observations, including existing empty numeric cells interpreted as zero. Categorical fields have their recorded-player count in the last column. Zeros include the stated cell policy; they are not proof of a measured event absence.

| Native column | Type | England | Spain | Germany | Italy | France | Total numeric players | Recorded players | Zero players | Engine |
|---|---|---|---|---|---|---|---|---|---|---|
| `advanced.actions` | context | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 0 | raw only |
| `advanced.carrying.carries` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 1510 | raw only |
| `advanced.carrying.carries_into_box` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2673 | imported/used |
| `advanced.carrying.carries_into_final_third` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2650 | imported/used |
| `advanced.carrying.carry_distance` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 1510 | raw only |
| `advanced.carrying.dispossessed` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2644 | imported/used |
| `advanced.carrying.miscontrols` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2608 | imported/used |
| `advanced.carrying.progressive_carries` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2633 | raw only |
| `advanced.carrying.progressive_carry_distance` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 1827 | imported/used |
| `advanced.carrying.take_ons` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2597 | imported/used |
| `advanced.carrying.take_ons_won` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2655 | imported/used |
| `advanced.creation.chances_created` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2657 | raw only |
| `advanced.creation.gca` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2673 | raw only |
| `advanced.creation.sca` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2595 | imported/used |
| `advanced.creation.sca_breakdown.defensive` | metric | 211 | 220 | 182 | 220 | 212 | 1041 | 1041 | 0 | raw only |
| `advanced.creation.sca_breakdown.pass_dead` | metric | 232 | 272 | 199 | 274 | 200 | 1159 | 1159 | 0 | raw only |
| `advanced.creation.sca_breakdown.pass_live` | metric | 482 | 526 | 448 | 526 | 472 | 2388 | 2388 | 0 | raw only |
| `advanced.creation.sca_breakdown.shot` | metric | 316 | 321 | 289 | 340 | 287 | 1541 | 1541 | 0 | raw only |
| `advanced.creation.sca_breakdown.take_on` | metric | 249 | 250 | 218 | 259 | 212 | 1174 | 1174 | 0 | raw only |
| `advanced.creation.second_assists` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2679 | raw only |
| `advanced.creation.xag` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2657 | raw only |
| `advanced.creation.xg_buildup` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2136 | raw only |
| `advanced.creation.xg_chain` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 1989 | raw only |
| `advanced.defending.aerials` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2480 | raw only |
| `advanced.defending.aerials_won` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2616 | imported/used |
| `advanced.defending.blocks` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2665 | imported/used |
| `advanced.defending.clearances` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2440 | raw only |
| `advanced.defending.duels_won` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2609 | raw only |
| `advanced.defending.interceptions` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2617 | imported/used |
| `advanced.defending.tackles` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2597 | raw only |
| `advanced.goalkeeping` | metric | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | raw only |
| `advanced.goalkeeping.avg_pass_length` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 0 | raw only |
| `advanced.goalkeeping.claim_rate` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 171 | raw only |
| `advanced.goalkeeping.claims` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 170 | raw only |
| `advanced.goalkeeping.claims_won` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 171 | raw only |
| `advanced.goalkeeping.distribution_accuracy` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 2 | raw only |
| `advanced.goalkeeping.distributions` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 0 | raw only |
| `advanced.goalkeeping.launch_pct` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 21 | raw only |
| `advanced.goalkeeping.launches` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 21 | raw only |
| `advanced.goalkeeping.sweeper_actions` | metric | 39 | 39 | 30 | 42 | 38 | 188 | 188 | 8 | raw only |
| `advanced.minutes_played` | context | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 0 | imported/used |
| `advanced.passing.assists` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2676 | raw only |
| `advanced.passing.crosses` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2615 | raw only |
| `advanced.passing.key_passes` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2657 | imported/used |
| `advanced.passing.pass_accuracy` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 715 | raw only |
| `advanced.passing.passes` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 399 | imported/used |
| `advanced.passing.passes_into_box` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2652 | imported/used |
| `advanced.passing.progressive_pass_distance` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2577 | raw only |
| `advanced.passing.progressive_passes` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2577 | raw only |
| `advanced.passing.switches` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2663 | raw only |
| `advanced.passing.through_balls` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 2674 | imported/used |
| `advanced.player.id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2679 | 0 | raw only |
| `advanced.player.name` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2679 | 0 | raw only |
| `advanced.player.shirt_number` | identity | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 0 | raw only |
| `advanced.possession_value.pv_defensive` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 405 | raw only |
| `advanced.possession_value.pv_offensive` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 62 | raw only |
| `advanced.possession_value.pv_total` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 37 | raw only |
| `advanced.possession_value.vaep_defensive` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 112 | raw only |
| `advanced.possession_value.vaep_offensive` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 30 | raw only |
| `advanced.possession_value.vaep_total` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 16 | raw only |
| `advanced.possession_value.xt_total` | metric | 534 | 598 | 498 | 585 | 546 | 2679 | 2679 | 659 | raw only |
| `advanced.team_id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2679 | 0 | raw only |
| `metadata.player.id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `metadata.player.image_url` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2675 | 0 | imported/used |
| `metadata.player.name` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `metadata.player.position_id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | imported/used |
| `metadata.team_id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `shot.blocked_x` | event | 421 | 462 | 397 | 459 | 428 | 2111 | 2111 | 0 | raw only |
| `shot.blocked_y` | event | 421 | 462 | 397 | 459 | 428 | 2111 | 2111 | 64 | raw only |
| `shot.event_type` | event | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.expected_goals` | event | 448 | 498 | 421 | 484 | 450 | 2237 | 2237 | 121 | raw only |
| `shot.expected_goals_on_target` | event | 444 | 498 | 420 | 484 | 448 | 2230 | 2230 | 2197 | raw only |
| `shot.goal_crossed_y` | event | 448 | 498 | 421 | 484 | 450 | 2237 | 2237 | 0 | raw only |
| `shot.goal_crossed_z` | event | 448 | 498 | 421 | 484 | 450 | 2237 | 2237 | 0 | raw only |
| `shot.id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.is_blocked` | event | 0 | 0 | 0 | 0 | 0 | 0 | 1922 | 0 | raw only |
| `shot.is_inside_box` | event | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.is_on_target` | event | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.is_own_goal` | event | 0 | 0 | 0 | 0 | 0 | 0 | 121 | 0 | raw only |
| `shot.is_saved_off_line` | event | 0 | 0 | 0 | 0 | 0 | 0 | 326 | 0 | raw only |
| `shot.keeper.id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 1961 | 0 | raw only |
| `shot.keeper.image_url` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 1961 | 0 | raw only |
| `shot.keeper.name` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 1961 | 0 | raw only |
| `shot.keeper.position_id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | raw only |
| `shot.minute` | event | 448 | 498 | 421 | 484 | 450 | 2237 | 2237 | 1 | raw only |
| `shot.minute_added` | event | 368 | 377 | 336 | 377 | 337 | 1763 | 1763 | 691 | raw only |
| `shot.player.id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.player.image_url` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2234 | 0 | raw only |
| `shot.player.name` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.player.position_id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | raw only |
| `shot.shot_type` | event | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.situation` | event | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.team_id` | identity | 0 | 0 | 0 | 0 | 0 | 0 | 2237 | 0 | raw only |
| `shot.x` | event | 448 | 498 | 421 | 484 | 450 | 2237 | 2237 | 0 | raw only |
| `shot.y` | event | 448 | 498 | 421 | 484 | 450 | 2237 | 2237 | 0 | raw only |
| `stats.Offsides.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 1403 | 0 | imported/used |
| `stats.Offsides.value` | metric | 292 | 319 | 264 | 294 | 260 | 1403 | 1403 | 0 | imported/used |
| `stats.ShotsOffTarget.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2227 | 0 | raw only |
| `stats.ShotsOffTarget.value` | metric | 444 | 496 | 419 | 484 | 448 | 2227 | 2227 | 2063 | raw only |
| `stats.ShotsOnTarget.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2227 | 0 | imported/used |
| `stats.ShotsOnTarget.value` | metric | 444 | 496 | 419 | 484 | 448 | 2227 | 2227 | 2168 | imported/used |
| `stats.accurate_crosses.calculated_percentage` | metric | 430 | 459 | 401 | 473 | 412 | 2118 | 2118 | 2025 | raw only |
| `stats.accurate_crosses.total` | metric | 430 | 459 | 401 | 473 | 412 | 2118 | 2118 | 0 | raw only |
| `stats.accurate_crosses.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2118 | 0 | raw only |
| `stats.accurate_crosses.value` | metric | 430 | 459 | 401 | 473 | 412 | 2118 | 2118 | 2025 | raw only |
| `stats.accurate_passes.calculated_percentage` | metric | 530 | 595 | 495 | 585 | 544 | 2670 | 2670 | 432 | raw only |
| `stats.accurate_passes.total` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 579 | imported/used |
| `stats.accurate_passes.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `stats.accurate_passes.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 832 | imported/used |
| `stats.aerials_won.calculated_percentage` | metric | 504 | 552 | 464 | 547 | 501 | 2498 | 2498 | 2148 | raw only |
| `stats.aerials_won.total` | metric | 531 | 589 | 497 | 573 | 541 | 2649 | 2649 | 2304 | imported/used |
| `stats.aerials_won.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2649 | 0 | imported/used |
| `stats.aerials_won.value` | metric | 531 | 589 | 497 | 573 | 541 | 2649 | 2649 | 2439 | imported/used |
| `stats.assists.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2509 | 0 | imported/used |
| `stats.assists.value` | metric | 501 | 560 | 471 | 544 | 515 | 2509 | 2509 | 2491 | imported/used |
| `stats.big_chance_created_team_title.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 1560 | 0 | raw only |
| `stats.big_chance_created_team_title.value` | metric | 325 | 341 | 293 | 330 | 290 | 1560 | 1560 | 0 | raw only |
| `stats.big_chance_missed_title.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 1426 | 0 | raw only |
| `stats.big_chance_missed_title.value` | metric | 303 | 295 | 273 | 302 | 275 | 1426 | 1426 | 0 | raw only |
| `stats.blocked_shots.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 1923 | 0 | raw only |
| `stats.blocked_shots.value` | metric | 390 | 414 | 360 | 417 | 382 | 1923 | 1923 | 0 | raw only |
| `stats.chances_created.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2561 | 0 | raw only |
| `stats.chances_created.value` | metric | 514 | 570 | 481 | 555 | 523 | 2561 | 2561 | 2466 | raw only |
| `stats.clearance_off_the_line.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 283 | 0 | raw only |
| `stats.clearance_off_the_line.value` | metric | 73 | 57 | 59 | 54 | 40 | 283 | 283 | 0 | raw only |
| `stats.clearances.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | raw only |
| `stats.clearances.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2465 | raw only |
| `stats.conceded_penalties.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 465 | 0 | raw only |
| `stats.conceded_penalties.value` | metric | 80 | 106 | 93 | 92 | 94 | 465 | 465 | 0 | raw only |
| `stats.corners.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 868 | 0 | raw only |
| `stats.corners.value` | metric | 176 | 187 | 148 | 206 | 172 | 868 | 868 | 0 | raw only |
| `stats.defensive_actions.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | raw only |
| `stats.defensive_actions.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2114 | raw only |
| `stats.dispossessed.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2494 | 0 | imported/used |
| `stats.dispossessed.value` | metric | 497 | 559 | 469 | 540 | 511 | 2494 | 2494 | 2460 | imported/used |
| `stats.dribbled_past.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2494 | 0 | raw only |
| `stats.dribbled_past.value` | metric | 497 | 559 | 469 | 540 | 511 | 2494 | 2494 | 2466 | raw only |
| `stats.dribbles_succeeded.calculated_percentage` | metric | 464 | 511 | 426 | 496 | 461 | 2289 | 2289 | 2012 | raw only |
| `stats.dribbles_succeeded.total` | metric | 464 | 511 | 426 | 496 | 461 | 2289 | 2289 | 0 | raw only |
| `stats.dribbles_succeeded.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2289 | 0 | raw only |
| `stats.dribbles_succeeded.value` | metric | 464 | 511 | 426 | 496 | 461 | 2289 | 2289 | 2012 | raw only |
| `stats.duel_lost.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2538 | 0 | imported/used |
| `stats.duel_lost.value` | metric | 512 | 570 | 472 | 549 | 511 | 2538 | 2538 | 0 | imported/used |
| `stats.duel_won.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2560 | 0 | imported/used |
| `stats.duel_won.value` | metric | 511 | 573 | 481 | 556 | 518 | 2560 | 2560 | 0 | imported/used |
| `stats.errors_led_to_goal.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 523 | 0 | raw only |
| `stats.errors_led_to_goal.value` | metric | 124 | 104 | 92 | 107 | 96 | 523 | 523 | 0 | raw only |
| `stats.expected_assists.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2403 | 0 | imported/used |
| `stats.expected_assists.value` | metric | 486 | 526 | 462 | 521 | 477 | 2403 | 2403 | 0 | imported/used |
| `stats.expected_goals.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2226 | 0 | raw only |
| `stats.expected_goals.value` | metric | 444 | 496 | 419 | 484 | 447 | 2226 | 2226 | 0 | raw only |
| `stats.expected_goals_non_penalty.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2219 | 0 | raw only |
| `stats.expected_goals_non_penalty.value` | metric | 443 | 495 | 416 | 484 | 445 | 2219 | 2219 | 0 | raw only |
| `stats.expected_goals_on_target_faced.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 190 | 0 | raw only |
| `stats.expected_goals_on_target_faced.value` | metric | 39 | 39 | 30 | 43 | 39 | 190 | 190 | 0 | raw only |
| `stats.expected_goals_on_target_variant.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2226 | 0 | raw only |
| `stats.expected_goals_on_target_variant.value` | metric | 444 | 496 | 419 | 484 | 447 | 2226 | 2226 | 2169 | raw only |
| `stats.fantasy_points.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 537 | 0 | raw only |
| `stats.fantasy_points.value` | rating | 537 | 0 | 0 | 0 | 0 | 537 | 537 | 257 | raw only |
| `stats.fouls.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | raw only |
| `stats.fouls.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2631 | raw only |
| `stats.goals.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2494 | 0 | raw only |
| `stats.goals.value` | metric | 497 | 559 | 469 | 540 | 511 | 2494 | 2494 | 2492 | raw only |
| `stats.goals_conceded.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.goals_conceded.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 159 | raw only |
| `stats.goals_prevented.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 191 | 0 | raw only |
| `stats.goals_prevented.value` | metric | 40 | 39 | 30 | 43 | 39 | 191 | 191 | 15 | raw only |
| `stats.ground_duels_won.calculated_percentage` | metric | 518 | 578 | 483 | 560 | 525 | 2586 | 2586 | 2115 | raw only |
| `stats.ground_duels_won.total` | metric | 518 | 578 | 483 | 560 | 525 | 2586 | 2586 | 0 | raw only |
| `stats.ground_duels_won.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2586 | 0 | raw only |
| `stats.ground_duels_won.value` | metric | 518 | 578 | 483 | 560 | 525 | 2586 | 2586 | 2115 | raw only |
| `stats.headed_clearance.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2121 | 0 | raw only |
| `stats.headed_clearance.value` | metric | 425 | 462 | 403 | 460 | 412 | 2121 | 2121 | 0 | raw only |
| `stats.interceptions.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `stats.interceptions.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2662 | imported/used |
| `stats.keeper_diving_save.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.keeper_diving_save.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 163 | raw only |
| `stats.keeper_high_claim.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.keeper_high_claim.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 179 | raw only |
| `stats.keeper_sweeper.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.keeper_sweeper.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 183 | raw only |
| `stats.last_man_tackle.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 422 | 0 | raw only |
| `stats.last_man_tackle.value` | metric | 92 | 92 | 82 | 72 | 84 | 422 | 422 | 0 | raw only |
| `stats.long_balls_accurate.calculated_percentage` | metric | 500 | 556 | 456 | 543 | 490 | 2486 | 2486 | 2085 | raw only |
| `stats.long_balls_accurate.total` | metric | 500 | 556 | 456 | 543 | 490 | 2486 | 2486 | 0 | raw only |
| `stats.long_balls_accurate.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2486 | 0 | raw only |
| `stats.long_balls_accurate.value` | metric | 500 | 556 | 456 | 543 | 490 | 2486 | 2486 | 2085 | raw only |
| `stats.matchstats.headers.tackles.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | raw only |
| `stats.matchstats.headers.tackles.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2611 | raw only |
| `stats.minutes_played.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `stats.minutes_played.value` | context | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 0 | imported/used |
| `stats.missed_penalty.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 110 | 0 | raw only |
| `stats.missed_penalty.value` | metric | 13 | 25 | 21 | 23 | 28 | 110 | 110 | 0 | raw only |
| `stats.owngoal.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 121 | 0 | raw only |
| `stats.owngoal.value` | metric | 34 | 23 | 20 | 19 | 25 | 121 | 121 | 0 | raw only |
| `stats.passes_into_final_third.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2540 | 0 | raw only |
| `stats.passes_into_final_third.value` | metric | 510 | 566 | 469 | 551 | 516 | 2540 | 2540 | 0 | raw only |
| `stats.penalties_won.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 306 | 0 | raw only |
| `stats.penalties_won.value` | metric | 55 | 72 | 63 | 53 | 63 | 306 | 306 | 0 | raw only |
| `stats.player_throws.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.player_throws.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 69 | raw only |
| `stats.punches.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.punches.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 180 | raw only |
| `stats.rating_title.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2574 | 0 | raw only |
| `stats.rating_title.value` | rating | 515 | 579 | 477 | 560 | 520 | 2574 | 2574 | 0 | raw only |
| `stats.recoveries.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `stats.recoveries.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2195 | imported/used |
| `stats.saved_penalties.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 62 | 0 | raw only |
| `stats.saved_penalties.value` | metric | 9 | 14 | 9 | 14 | 16 | 62 | 62 | 0 | raw only |
| `stats.saves.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.saves.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 127 | raw only |
| `stats.saves_inside_box.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 194 | 0 | raw only |
| `stats.saves_inside_box.value` | metric | 40 | 39 | 30 | 46 | 39 | 194 | 194 | 156 | raw only |
| `stats.shot_accuracy.calculated_percentage` | metric | 435 | 483 | 407 | 473 | 438 | 2179 | 2179 | 2052 | raw only |
| `stats.shot_accuracy.total` | metric | 435 | 483 | 407 | 473 | 438 | 2179 | 2179 | 0 | raw only |
| `stats.shot_accuracy.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2179 | 0 | raw only |
| `stats.shot_accuracy.value` | metric | 435 | 483 | 407 | 473 | 438 | 2179 | 2179 | 2052 | raw only |
| `stats.shot_blocks.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2494 | 0 | imported/used |
| `stats.shot_blocks.value` | metric | 497 | 559 | 469 | 540 | 511 | 2494 | 2494 | 2485 | imported/used |
| `stats.shots_woodwork.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 610 | 0 | raw only |
| `stats.shots_woodwork.value` | metric | 148 | 110 | 116 | 132 | 105 | 610 | 610 | 0 | raw only |
| `stats.total_shots.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2227 | 0 | raw only |
| `stats.total_shots.value` | metric | 444 | 496 | 419 | 484 | 448 | 2227 | 2227 | 0 | raw only |
| `stats.touches.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | raw only |
| `stats.touches.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 218 | raw only |
| `stats.touches_opp_box.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2494 | 0 | imported/used |
| `stats.touches_opp_box.value` | metric | 497 | 559 | 469 | 540 | 511 | 2494 | 2494 | 2394 | imported/used |
| `stats.unnamed.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | raw only |
| `stats.unnamed.value` | context | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2533 | raw only |
| `stats.was_fouled.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2688 | 0 | imported/used |
| `stats.was_fouled.value` | metric | 537 | 598 | 499 | 586 | 550 | 2688 | 2688 | 2653 | imported/used |
| `stats.xg_and_xa.type` | context | 0 | 0 | 0 | 0 | 0 | 0 | 2443 | 0 | raw only |
| `stats.xg_and_xa.value` | context | 493 | 539 | 468 | 532 | 485 | 2443 | 2443 | 0 | raw only |

## Season and freshness

| League | Recorded metadata |
|---|---|
| England | {"first_match": "2025-08-15", "inventory_matches": 380, "last_match": "2026-05-24", "provider_updated": null, "retrieved_first": "2026-10-06T07:32:05.383923+00:00", "retrieved_last": "2026-10-06T07:37:25.629108+00:00", "validated_matches": 380} |
| France | {"first_match": "2025-08-15", "inventory_matches": 306, "last_match": "2026-05-17", "provider_updated": null, "retrieved_first": "2026-10-06T07:33:54.308653+00:00", "retrieved_last": "2026-10-06T07:45:56.308696+00:00", "validated_matches": 302} |
| Germany | {"first_match": "2025-08-22", "inventory_matches": 306, "last_match": "2026-05-16", "provider_updated": null, "retrieved_first": "2026-10-06T07:33:53.632735+00:00", "retrieved_last": "2026-10-06T07:42:52.034480+00:00", "validated_matches": 306} |
| Italy | {"first_match": "2025-08-23", "inventory_matches": 380, "last_match": "2026-05-24", "provider_updated": null, "retrieved_first": "2026-10-06T07:33:53.934912+00:00", "retrieved_last": "2026-10-06T07:44:25.937168+00:00", "validated_matches": 380} |
| Spain | {"first_match": "2025-08-15", "inventory_matches": 380, "last_match": "2026-05-24", "provider_updated": null, "retrieved_first": "2026-10-06T07:33:53.359206+00:00", "retrieved_last": "2026-10-06T07:41:44.427065+00:00", "validated_matches": 379} |

## Non-player fields

These do not contribute player or performance-feature counts.

- match: `away_team.id`, `away_team.image_url`, `away_team.name`, `date`, `home_team.id`, `home_team.image_url`, `home_team.name`, `id`, `score_away`, `score_home`, `status`, `time_utc`

Rights: existing user-confirmed source permission retained

Full schema/provenance is retained in the content-addressed audit snapshot. No rating or application release is changed.

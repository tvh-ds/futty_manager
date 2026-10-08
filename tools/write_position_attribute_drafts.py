"""Write review-only positional specifications from the private master inventory.

Reads SQLite in read-only mode. Does not change data, scoring or serving releases.
"""
import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Rating System'
DB = ROOT / 'data/master/2025-26-v2/master.sqlite'

# key: label, master columns, formula, direction, interpretation
FEATURES = {
 'npg': ('Non-penalty goals /90', ['np_goals'], '90 × np_goals / minutes', '+', 'Realized scoring; noisy at low shot exposure. Compatible alternatives: PitchAPI non_penalty_goals; Understat npg.'),
 'npxg': ('Non-penalty xG /90', ['np_xg'], '90 × np_xg / minutes', '+', 'Chance production, not pure finishing technique. Alternatives: PitchAPI npxg; Understat npxG, with their own model definitions.'),
 'finish': ('Goals above non-penalty xG /90', ['np_goals_vs_xg'], '90 × np_goals_vs_xg / minutes', '+', 'Signed residual; shrink strongly. Validate against same-provider np_goals − np_xg.'),
 'npsot': ('Non-penalty shots on target /90', ['np_shots_on_target'], '90 × np_shots_on_target / minutes', '+', 'Shot production; do not substitute all-shot on-target totals without preserving the different scope.'),
 'accuracy': ('Non-penalty on-target share', ['np_shots_on_target','np_shots'], '100 × np_shots_on_target / np_shots', '+', 'Uses all non-penalty attempts consistently, including blocked attempts. This is a Scout ratio, not Opta shooting accuracy, which excludes blocked shots.'),
 'xgshot': ('Non-penalty xG / shot', ['np_xg','np_shots'], 'np_xg / np_shots', '+', 'Shot selection/opportunity quality; not shot power. Recalculate from the same provider, rather than assume a published ratio uses identical attempts.'),
 'boxshots': ('Shots inside box /90', ['shots_inside_box'], '90 × shots_inside_box / minutes', '+', 'PitchAPI aggregate; verify shot scope and complete match coverage.'),
 'boxtouch': ('Opposition box touches /90', ['touches_opposition_box'], '90 × touches_opposition_box / minutes', '+', 'Box involvement proxy, not tracking-based off-ball movement.'),
 'opxg': ('Open-play xG /90', ['open_play_xg'], '90 × open_play_xg / minutes', '+', 'PitchAPI open-play shot context; not interchangeable with non-penalty xG including set pieces.'),
 'opxa': ('Open-play xA /90', ['op_xa'], '90 × op_xa / minutes', '+', 'Open-play creation reduces set-piece responsibility bias. Total xa/xA is a separately labelled fallback, not an identical feature.'),
 'opkp': ('Open-play chances created /90', ['op_chances_created'], '90 × op_chances_created / minutes', '+', 'Opta chance-creation definition; do not silently equate with every provider key_passes.'),
 'assist': ('Open-play assists /90', ['op_assists'], '90 × op_assists / minutes', '+', 'Realized creation with teammate finishing noise; keep a modest share.'),
 'sca': ('Shot-creating actions /90', ['sca'], '90 × sca / minutes', '+', 'PitchAPI SCA definition must be retained; includes overlapping creation signals and potentially dead-ball actions.'),
 'ppa': ('Passes into penalty area /90', ['passes_into_penalty_area'], '90 × passes_into_penalty_area / minutes', '+', 'Spatial delivery; establish completion/cross-inclusion contract before activation.'),
 'through': ('Successful through balls /90', ['successful_through_balls'], '90 × successful_through_balls / minutes', '+', 'Prefer successful deliveries to attempted-volume alone.'),
 'cross': ('Successful open-play crosses /90', ['successful_op_crosses'], '90 × successful_op_crosses / minutes', '+', 'Open-play delivery; opportunity and target-player context matter.'),
 'crosspct': ('Open-play cross completion', ['successful_op_crosses','op_crosses'], '100 × successful_op_crosses / op_crosses', '+', 'Same-provider open-play counts; do not combine an all-cross cross_perc with open-play attempts.'),
 'dribble': ('Successful take-ons /90', ['take_ons_successful'], '90 × take_ons_successful / minutes', '+', 'On-ball opponent beating, not sprint speed.'),
 'dribblepct': ('Take-on success', ['take_ons_successful','take_ons_attempted'], '100 × take_ons_successful / take_ons_attempted', '+', 'Shrink using take-on attempts; zero attempts produce N/A.'),
 'carrybox': ('Carries into penalty area /90', ['carries_into_penalty_area'], '90 × carries_into_penalty_area / minutes', '+', 'Territorial carrying; overlaps successful take-ons only partially.'),
 'carrythird': ('Carries into final third /90', ['carries_into_final_third'], '90 × carries_into_final_third / minutes', '+', 'Field advancement; not proof of beating a defensive line.'),
 'progcarry': ('Progressive carries /90', ['progressive_carries'], '90 × progressive_carries / minutes', '+', 'Opta progressive-carry criterion; preserve definition/version.'),
 'progdist': ('Progressive carry distance /90', ['progressive_distance'], '90 × progressive_distance / minutes', '+', 'Opta carries.overall.progressive_distance, not progressive passing distance. Signed observations are retained; do not force absolute values. PitchAPI progressive_carry_distance is not automatically equivalent.'),
 'passpct': ('Pass completion', ['successful_passes','passes'], '100 × successful_passes / passes', '+', 'Same-provider denominator. Ordinary completion is a limited retention proxy, not vision or pressured-pass quality.'),
 'passvolume': ('Successful passes /90', ['successful_passes'], '90 × successful_passes / minutes', '+', 'Small-weight circulation activity; heavily team-style dependent.'),
 'ftpass': ('Successful final-third passes /90', ['successful_final_third_passes'], '90 × successful_final_third_passes / minutes', '+', 'Provider final-third passing category. Do not rename as progressive passes or entries until start/end-zone semantics are verified.'),
 'ftpct': ('Final-third pass completion', ['successful_final_third_passes','total_final_third_passes'], '100 × successful_final_third_passes / total_final_third_passes', '+', 'Completion within the same provider category; no pressure inference.'),
 'buildup': ('xGBuildup /90', ['xGBuildup'], '90 × xGBuildup / Understat time', '+', 'Understat possession-chain involvement before shot/assist; team-dependent, private-use evidence, not OBV or xT.'),
 'mis': ('Miscontrols /90', ['miscontrols'], '90 × miscontrols / minutes', '−', 'Recorded control losses; low counts can also reflect limited receiving responsibility.'),
 'dis': ('Dispossessed /90', ['dispossessed'], '90 × dispossessed / minutes', '−', 'Loss while in possession; use carrying/role context and do not infer pressure resistance directly.'),
 'tackle': ('Tackles /90', ['tackles'], '90 × tackles / minutes', '+', 'Activity proxy. Opta tackles include won/lost possession outcomes; not attempted challenges or tackle success.'),
 'intercept': ('Interceptions /90', ['interceptions'], '90 × interceptions / minutes', '+', 'Reading/action activity; opportunities depend on opposition possession.'),
 'recover': ('Recoveries /90', ['recoveries'], '90 × recoveries / minutes', '+', 'Ball recovery activity; not a measured pressing-success rate.'),
 'block': ('Shot blocks /90', ['blocks'], '90 × blocks / minutes', '+', 'Use Opta shot-block scope. A fallback must confirm the same definition; do not assume blocked passes/crosses are equivalent.'),
 'clear': ('Clearances /90', ['clearances'], '90 × clearances / minutes', '+', 'Emergency/box intervention volume; low-block context can inflate it, so its weight is limited.'),
 'ground': ('Ground duels won /90', ['ground_duels_won'], '90 × ground_duels_won / minutes', '+', 'Opta ground duels are broad contests, not exclusively defensive 1v1 challenges.'),
 'groundpct': ('Ground duel win share', ['ground_duels_won','ground_duels'], '100 × ground_duels_won / ground_duels', '+', 'Pair matched outcomes/attempts from Opta. This is not tackle/dribbled-past success.'),
 'aerial': ('Aerial duels won /90', ['aerial_duels_won'], '90 × aerial_duels_won / minutes', '+', 'Successful aerial involvement; height itself is excluded.'),
 'aerialpct': ('Aerial duel win share', ['aerial_duels_won','aerial_duels'], '100 × aerial_duels_won / aerial_duels', '+', 'Use Opta pair. PitchAPI fallback uses aerial_duels_won / (aerial_duels_won + aerial_duels_lost), with its own minutes.'),
 'foul': ('Fouls committed /90', ['fouls_commited'], '90 × fouls_commited / minutes', '−', 'Native spelling retained. Tactical foul context and referee effects require caution.'),
 'pen': ('Penalties conceded /90', ['pens_conceded'], '90 × pens_conceded / minutes', '−', 'Rare damaging events; not goalkeeping penalty-save ability.'),
 'yellow': ('Yellow cards /90', ['yellows'], '90 × yellows / minutes', '−', 'Discipline proxy; do not imply aggression or effort is intrinsically bad.'),
 'red': ('Red cards /90', ['reds'], '90 × reds / minutes', '−', 'Rare events; heavy stabilization and review of second-yellow semantics required.'),
 'prevent': ('Goals prevented /90', ['goals_prevented'], '90 × goals_prevented / keeper minutes', '+', 'Opta signed shot-stopping residual; confirm xGOT, own-goal and penalty conventions. Do not replace with raw conceded goals.'),
 'savepct': ('Save percentage', ['save_perc'], 'Use provider save_perc; validate its attempts contract', '+', 'Less chance-adjusted than goals prevented; includes shot-difficulty and team effects.'),
}

# Raw observations already inside master.sqlite; not wide season columns.
RAW = {
 'claimpct': ('Claim success', ['advanced.goalkeeping.claims_won','advanced.goalkeeping.claims'], '100 × Σclaims_won / Σclaims', '+', 'Claim attempts and successful outcomes; not crosses-claimed/opponent-crosses unless the provider establishes that denominator.'),
 'claim90': ('Successful claims /90', ['advanced.goalkeeping.claims_won'], '90 × Σclaims_won / matched keeper minutes', '+', 'Activity proxy, not chance-adjusted command of area. Do not add stats.keeper_high_claim to overlapping claims_won.'),
 'sweep90': ('Sweeper actions /90', ['advanced.goalkeeping.sweeper_actions'], '90 × Σsweeper_actions / matched keeper minutes', '+', 'Outside-goal intervention activity; higher frequency does not establish safer decision-making.'),
 'gkclear': ('Keeper clearances /90', ['stats.clearances.value'], '90 × Σkeeper clearances / matched keeper minutes', '+', 'Only verified GK appearances. Not automatically outside-area clearances; context and location needed.'),
 'gkinter': ('Keeper interceptions /90', ['stats.interceptions.value'], '90 × Σkeeper interceptions / matched keeper minutes', '+', 'Only verified GK appearances; broad intervention proxy, not exact sweeping quality.'),
 'distpct': ('Distribution completion', ['advanced.goalkeeping.distribution_accuracy','advanced.goalkeeping.distributions'], 'Σ(match accuracy × distributions) / Σdistributions, after verifying percentage unit', '+', 'Weighted completion, never mean of match percentages. Recover exact numerator where available; rounded percentages can only give an approximate aggregate.'),
 'gkpasspct': ('Pass completion', ['stats.accurate_passes.value','stats.accurate_passes.total'], '100 × Σaccurate_passes.value / Σaccurate_passes.total', '+', 'Keeper-specific appearances; use common match window and verify numerator/denominator metadata.'),
 'gkpass90': ('Successful passes /90', ['stats.accurate_passes.value'], '90 × Σaccurate_passes.value / matched keeper minutes', '+', 'Small style-dependent build-up involvement signal, not a pure quality measure.'),
 'longpct': ('Long-ball completion', ['stats.long_balls_accurate.value','stats.long_balls_accurate.total'], '100 × Σaccurate long balls / Σattempted long balls', '+', 'Keeper-only appearances. No claim that launch_pct measures accuracy; launch_pct measures propensity.'),
 'long90': ('Accurate long balls /90', ['stats.long_balls_accurate.value'], '90 × Σaccurate long balls / matched keeper minutes', '+', 'Successful long distribution volume; tactical responsibility strongly affects opportunities.'),
 'gkmis': ('Keeper miscontrols /90', ['advanced.carrying.miscontrols'], '90 × Σkeeper miscontrols / matched keeper minutes', '−', 'Rare control-loss signal; absence of pressure exposure limits interpretation.'),
 'gkdis': ('Keeper dispossessions /90', ['advanced.carrying.dispossessed'], '90 × Σkeeper dispossessed / matched keeper minutes', '−', 'Rare on-ball loss; only complete known windows support zero-event interpretation.'),
}

# Six parents per role: name, card abbreviation, OVR weight, rationale, feature weights.
ROLES = {
 'lw_rw': ('LW / RW', 'Wide forward: prioritize creating separation, creating chances and scoring; both flanks share one statistical cohort.', [
  ('Carrying / 1v1','CAR',24,'Breaking an opponent and entering dangerous territory.', [('dribble',30),('dribblepct',20),('carrybox',25),('carrythird',15),('progdist',10)]),
  ('Chance Creation','CRE',22,'Open-play chance delivery rather than only realized assists.', [('opxa',30),('opkp',25),('ppa',20),('cross',15),('through',10)]),
  ('Scoring','SCO',20,'Blend chance production with strongly stabilized shot execution.', [('npg',25),('npxg',15),('finish',30),('npsot',15),('accuracy',15)]),
  ('Penalty-Area Threat','BOX',14,'Involvement near goal; this is an output proxy for movement.', [('boxtouch',40),('boxshots',30),('opxg',30)]),
  ('Ball Retention','RET',10,'Penalize control losses while giving passing only modest influence.', [('mis',40),('dis',40),('passpct',20)]),
  ('Defensive Support','DEF',10,'Contribution to recovery and defensive actions, not inferred pressing.', [('recover',40),('intercept',25),('tackle',25),('block',10)]),
 ]),
 'cm': ('CM', 'Central midfielder: balanced circulation, advancement, creation and recovery. LCM/RCM share the same role.', [
  ('Ball Progression','PRO',24,'Reward carrying and territorial passing; do not claim unavailable line-breaking pass counts.', [('ftpass',30),('progcarry',25),('progdist',20),('carrythird',15),('through',10)]),
  ('Retention / Circulation','RET',20,'Control losses matter more than uncontextualized completion.', [('mis',30),('dis',30),('passpct',20),('ftpct',10),('passvolume',10)]),
  ('Chance Creation','CRE',18,'Final delivery and involvement earlier in scoring possessions.', [('opxa',30),('opkp',25),('ppa',20),('through',10),('buildup',15)]),
  ('Ball Recovery','REC',18,'Balanced recovery and interception activity.', [('recover',40),('intercept',35),('tackle',25)]),
  ('Duel Contribution','DUE',12,'Ground contribution receives most emphasis; aerial play is supplementary.', [('groundpct',40),('ground',30),('aerialpct',20),('aerial',10)]),
  ('Goal Threat','SCO',8,'Secondary scoring responsibility avoids rewarding only attacking eights.', [('npxg',40),('npg',25),('npsot',20),('boxtouch',15)]),
 ]),
 'cam': ('CAM', 'Central attacking midfielder: chance creation and combination play first; carrying and scoring remain substantial.', [
  ('Chance Creation','CRE',30,'Prioritize expected output and repeatable chance delivery.', [('opxa',35),('opkp',25),('ppa',20),('through',10),('sca',10)]),
  ('Combination / Retention','LNK',18,'Maintain involvement in attacks without repeatedly losing the ball.', [('mis',25),('dis',25),('passpct',20),('ftpct',15),('buildup',15)]),
  ('Carrying / 1v1','CAR',18,'Carry into central danger and beat opponents.', [('dribble',25),('dribblepct',20),('carrybox',25),('carrythird',15),('progdist',15)]),
  ('Scoring','SCO',16,'Attacking-midfield shooting production and execution.', [('npxg',15),('npg',25),('finish',30),('npsot',15),('accuracy',15)]),
  ('Penalty-Area Threat','BOX',10,'Late arrivals and box involvement measured through actions.', [('boxtouch',45),('boxshots',30),('opxg',25)]),
  ('Defensive Support','DEF',8,'Secondary recovery contribution without invented pressure data.', [('recover',45),('intercept',30),('tackle',25)]),
 ]),
 'cdm': ('CDM', 'Holding midfielder: screening, retention and progression; LDM/RDM share the same role.', [
  ('Screening / Recovery','SCR',24,'Pass interception and recovery with some tackling activity.', [('intercept',40),('recover',35),('tackle',15),('block',10)]),
  ('Ground Duels','DUE',18,'Ground contest outcomes, not unobserved pure tackling success.', [('groundpct',60),('ground',40)]),
  ('Ball Retention','RET',20,'A pivot must limit control losses; safe passing alone is insufficient.', [('mis',30),('dis',30),('passpct',25),('passvolume',15)]),
  ('Build-Up / Progression','PRO',20,'Advance and connect possessions without needing to make the final assist.', [('ftpass',30),('progcarry',20),('progdist',15),('through',15),('buildup',20)]),
  ('Aerial Contribution','AIR',10,'Second-ball and aerial-contest outcomes, without height scoring.', [('aerialpct',65),('aerial',35)]),
  ('Discipline','DIS',8,'Constrain avoidable damaging infringements; stabilize rare outcomes.', [('foul',45),('yellow',15),('red',20),('pen',20)]),
 ]),
 'lm_rm': ('LM / RM', 'Wide midfielder: greater recovery and retention responsibility than a wide forward; both flanks grouped.', [
  ('Wide Creation','CRE',24,'Open-play crossing plus creation beyond crosses.', [('opxa',30),('opkp',20),('cross',25),('crosspct',15),('ppa',10)]),
  ('Carrying / Progression','CAR',20,'Advance down the flank while retaining a 1v1 threat.', [('dribble',25),('dribblepct',20),('carrythird',25),('progdist',20),('carrybox',10)]),
  ('Ball Retention','RET',16,'Protect possession during repeated circulation and transitions.', [('mis',30),('dis',30),('passpct',25),('passvolume',15)]),
  ('Defensive Support','DEF',20,'Recovery and defensive contribution deserve more emphasis than for LW/RW.', [('recover',35),('intercept',30),('tackle',25),('block',10)]),
  ('Duel Contribution','DUE',10,'Ground contests primarily, with limited aerial contribution.', [('groundpct',45),('ground',30),('aerialpct',15),('aerial',10)]),
  ('Goal Threat','SCO',10,'Supplementary scoring, with room for back-post/box involvement.', [('npxg',40),('npg',25),('boxtouch',20),('npsot',15)]),
 ]),
 'cb': ('CB', 'Centre-back: aerial and ground contests, interventions and useful build-up. LCB/RCB grouped; left-foot suitability stays separate.', [
  ('Ground Defending','GRD',24,'Use contest outcomes and interceptions; counts alone cannot establish isolation defending.', [('groundpct',50),('ground',20),('tackle',20),('intercept',10)]),
  ('Aerial Defending','AIR',22,'Win share dominates volume to limit low-block/opportunity bias.', [('aerialpct',70),('aerial',30)]),
  ('Reading / Interventions','INT',18,'Interceptions and recovery plus limited blocks/clearances.', [('intercept',35),('recover',25),('block',25),('clear',15)]),
  ('Build-Up Passing','PAS',16,'Retain and advance circulation; modest volume contribution.', [('passpct',35),('ftpass',30),('ftpct',15),('through',10),('passvolume',10)]),
  ('Carrying / Control','CAR',10,'Step forward with the ball without penalizing through a fictional position penalty.', [('progcarry',30),('progdist',25),('carrythird',15),('mis',15),('dis',15)]),
  ('Discipline','DIS',10,'Rare damaging actions matter but need heavy stabilization.', [('foul',40),('pen',30),('red',20),('yellow',10)]),
 ]),
 'rb_lb': ('RB / LB', 'Full-back: balance flank defending, progression and creation. LWB/RWB can use this registry with a later wing-back OVR preset.', [
  ('Ground Defending','GRD',20,'Flank challenge outcomes with limited tackle-volume weighting.', [('groundpct',55),('ground',25),('tackle',20)]),
  ('Recovery / Cover','REC',16,'Recovery, interception and block activity; no tracking-based recovery-speed claim.', [('recover',40),('intercept',35),('block',15),('clear',10)]),
  ('Ball Progression','PRO',18,'Carry and circulate forward without relabelling distance as pace.', [('carrythird',30),('progcarry',25),('progdist',20),('ftpass',25)]),
  ('Wide Creation','CRE',22,'Support overlapping, crossing and underlapping delivery.', [('opxa',30),('opkp',20),('cross',25),('crosspct',15),('ppa',10)]),
  ('Ball Retention','RET',14,'Control losses and passing; no measured under-pressure claim.', [('mis',30),('dis',30),('passpct',25),('ftpct',15)]),
  ('Aerial Contribution','AIR',10,'Back-post/long-ball aerial contests without assuming where each duel occurred.', [('aerialpct',65),('aerial',35)]),
 ]),
 'gk': ('GK', 'Goalkeeper: separate peer population; use measured shot stopping, claims, interventions and distribution rather than fake speed/reflex ratings.', [
  ('Shot Stopping','STP',40,'Chance-adjusted prevention is primary; save percentage is supplementary.', [('prevent',75),('savepct',25)]),
  ('Claims / Aerial Control','CLM',15,'Successful claim outcomes and limited activity weighting.', [('claimpct',75),('claim90',25)]),
  ('Sweeping / Interventions','SWP',10,'A provisional intervention profile; exact sweeping success/location remain missing.', [('sweep90',70),('gkclear',20),('gkinter',10)]),
  ('Build-Up Distribution','BLD',15,'Completion and small-weight circulation volume, without claiming short/pressured passing isolation.', [('gkpasspct',60),('distpct',25),('gkpass90',15)]),
  ('Long Distribution','LNG',10,'Completion dominates launch volume; distance/launch propensity is descriptive only.', [('longpct',80),('long90',20)]),
  ('Ball Security','SEC',10,'Conservative control-loss proxy; cannot stand in for catching/handling or positioning.', [('gkmis',60),('gkdis',40)]),
 ]),
}

LINKS = {
 'ea': ('EA official attribute families (legacy chemistry-style reference)', 'https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf'),
 'radar': ('Hudl StatsBomb positional radar methodology', 'https://blogarchive.statsbomb.com/articles/soccer/new-statsbomb-radars-2023-update/'),
 'opta': ('Opta event definitions', 'https://www.statsperform.com/opta-event-definitions/'),
 'fb': ('StatsBomb full-back recruitment example', 'https://blogarchive.statsbomb.com/articles/soccer/using-statsbomb-iq-for-player-recruitment-full-backs/'),
 'cb': ('StatsBomb centre-back scouting approach', 'https://blogarchive.statsbomb.com/articles/soccer/how-do-you-scout-for-centre-backs-statistically/'),
 'gk': ('StatsBomb goalkeeper radar measures', 'https://blogarchive.statsbomb.com/articles/soccer/introducing-goalkeeper-radars/'),
}

def link(key):
    label, url = LINKS[key]
    return f'[{label}]({url})'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path, default=DB.parent,
                        help='Master snapshot directory; defaults to the original review snapshot.')
    args = parser.parse_args()
    database = (args.master / 'master.sqlite').resolve(strict=True)
    con = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    cols = {label: (cid, json.loads(members)) for cid, label, members in con.execute('SELECT column_id,label,members_json FROM columns')}
    counts = defaultdict(lambda: {'recorded': 0, 'zero': 0, 'providers': set()})
    for cid, status, provider, n in con.execute('SELECT column_id,status,selected_provider,COUNT(*) FROM cells GROUP BY column_id,status,selected_provider'):
        counts[cid]['zero' if status == 'unrecorded_zero' else 'recorded'] += n
        if provider:
            counts[cid]['providers'].add(provider)
    raw_paths = sorted({path for f in RAW.values() for path in f[1]})
    # Scope/player identity remain provider-native. Counts are not season aggregates.
    placeholders = ','.join('?' for _ in raw_paths)
    raw_counts = {field: (n, players) for field, n, players in con.execute(
        f'SELECT field,COUNT(*),COUNT(DISTINCT league||\':\'||player_id) FROM observations WHERE provider=\'pitchapi\' AND scope=\'appearance\' AND status=\'numeric\' AND field IN ({placeholders}) GROUP BY field', raw_paths)}
    total = con.execute('SELECT COUNT(*) FROM players').fetchone()[0]
    for stem, (position, summary, abilities) in ROLES.items():
        assert len(abilities) == 6 and sum(a[2] for a in abilities) == 100
        keys = set()
        lines = [f'# {position} Attributes', '', '**Status: proposed review draft v1 — not implemented or activated.**', '',
                 '**Performance season:** 2025/26. **Research/inventory date:** 7 October 2026.', '', summary, '',
                 'All weights below are provisional Scout design judgments, not fitted results or proprietary EA coefficients. Left/right variants have identical weights and a shared peer population; foot preference, side experience and tactical fit remain separate.', '',
                 '## Six abilities and overall weights', '', '| Ability | Card label | OVR weight |', '|---|---|---:|']
        for name, abbr, weight, _, _ in abilities:
            lines.append(f'| {name} | {abbr} | {weight}% |')
        lines += ['', '**Overall weights sum to 100%.** Standardize each ability before combining them, then re-standardize OVR. '+
                  'Display `max(1, 50 + 15 × z)` with no upper cap. See [shared calculation and source rules](position_attribute_methods.md).', '',
                  '## Feature definitions and weights', '', 'Each table sums to 100% **within that ability**. `+` means higher is preferable; `−` means lower is preferable after stabilization. `/90` uses matched provider exposure, not a different source’s season minutes.', '']
        for i, (name, abbr, weight, rationale, features) in enumerate(abilities, 1):
            assert sum(w for _, w in features) == 100
            lines += [f'### {i}. {name} — {weight}% of OVR', '', rationale, '',
                      '| Feature | Master input | Calculation | Direction | Within-ability weight |', '|---|---|---|:---:|---:|']
            for key, w in features:
                keys.add(key)
                label, inputs, formula, direction, note = (FEATURES | RAW)[key]
                for field in inputs:
                    if key not in RAW:
                        assert field in cols, field
                storage = 'raw appearance: ' if key in RAW else ''
                fields = ', '.join(f'`{v}`' for v in inputs)
                lines.append(f'| {label} | {storage}{fields} | `{formula}` | {direction} | {w}% |')
            lines += ['', 'Interpretation:', '']
            for key, _ in features:
                label, _, _, _, note = (FEATURES | RAW)[key]
                lines.append(f'- **{label}:** {note}')
            lines.append('')
        lines += ['## What is actually in the master', '',
                  f'The inspected private master has **{total:,} player/league rows and {len(cols)} wide columns**. Counts below are recorded input cells, including recorded zeros, excluding `unrecorded_zero`. They include low-minute players and all roles; they are **not** eligible-role counts or guaranteed derived-feature coverage. No 90% gate is applied.', '',
                  '| Season-column input | Recorded master rows | Zero-filled rows | Selected sources |', '|---|---:|---:|---|']
        fields = sorted({f for k in keys if k in FEATURES for f in FEATURES[k][1]})
        for field in fields:
            cid, _ = cols[field]
            d = counts[cid]
            lines.append(f'| `{field}` | {d["recorded"]:,} | {d["zero"]:,} | '+', '.join(sorted(d['providers']))+' |')
        if stem == 'gk':
            lines += ['', '### Raw-match inputs retained in the master', '',
                      'These exist in `observations`, not the 227-column wide season view. Numeric player/league counts include recorded zeros; generic passing/control fields include outfield players. GK-only counts for those fields need a verified position join. Counts are neither complete-season coverage nor a merged-player total.', '',
                      '| PitchAPI native path | Numeric observations | Provider player/league records |', '|---|---:|---:|']
            for field in sorted({f for k in keys if k in RAW for f in RAW[k][1]}):
                n, players = raw_counts.get(field, (0, 0))
                lines.append(f'| `{field}` | {n:,} | {players:,} |')
            lines += ['', '**GK implementation boundary:** Shot Stopping has wide season inputs for 190 master rows. The other five ability templates require a new GK aggregation/mapping path over captured appearances. A numeric raw path does not authorize a full-season sum. Confirm match deduplication, actual keeper exposure, units, attempts and complete windows first. Missing whole abilities cannot be replaced by zeros or silently dropped from OVR.', '',
                      'Ball Security and Sweeping are deliberately labelled provisional proxies. If their stabilized reference variance is zero, withhold the affected ability and OVR; do not award every goalkeeper a high score for a flat zero population. Save technique, reflex time, positioning error, claimable-cross opportunity, sweeping success and one-on-one shot context remain unmeasured. These are future investigations, not hidden scored features.', '']
        lines += ['## Role-specific limits and review decisions', '']
        if stem in {'lw_rw','lm_rm'}:
            lines += ['- LW/RW and LM/RM are distinct roles: wide midfielders receive more defensive responsibility. Existing broad winger labels are insufficient for this split; verify detailed season roles before building cohorts.',
                      '- Crossing and dribbling reflect intended style. An inverted winger can be excellent with few crosses. A later archetype preset can change parent weights; do not automatically change the baseline for individual players.']
        if stem in {'cm','cam','cdm'}:
            lines += ['- Detailed position evidence must distinguish CM, CAM and CDM. Do not infer the role from whichever weighted score is highest.',
                      '- Build-up xG is possession-chain involvement, not marginal action value. Completion is a modest proxy; it cannot establish vision, press resistance or ball speed.']
        if stem in {'cb','rb_lb','cdm'}:
            lines += ['- Defensive volume depends on opposition possession, territory and tactical assignment. These are transparent provisional production scores, not a claim of isolated defensive quality.',
                      '- High-line recovery pace, marking, coordination and pressured receiving need spatial/tracking evidence. They are not measured by tackles, interceptions or carrying metres.']
        if stem == 'rb_lb':
            lines.append('- Wing-backs and inverted full-backs should later get separate OVR presets; the balanced default here does not settle which style fits a particular team.')
        lines += ['- Correlated inputs (e.g. goals/xG; take-on wins/success share; duel wins/share) are intentionally limited to a parent/family budget. Review correlations and weight sensitivity before implementation; do not add totals and /90 forms as extra abilities.',
                  '- Repeated inputs across different parents are stored once. Overall influence is the parent-weight × feature-weight path before standardization; overlapping standardized composites still need empirical sensitivity checks.',
                  '- Exclude provider overall ratings, age, nationality, fee, height, weight and unverified pace/stamina/strength guesses from performance scoring.',
                  '- Review: approve the six parent names and OVR weights; then approve feature semantics, within-parent weights and each contextual proxy. No engine, UI or data-release changes are made by this document.', '',
                  '## Research basis', '',
                  'EA’s published attribute families inform the six-part presentation, but Scout uses retrievable performance observations. Pace, reflexes and pure strength cannot be reconstructed from the current aggregate event data. '+link('ea')+'.', '',
                  'The proposed feature allocation is Scout’s inference from role duties and the local inventory, not a copied commercial rating formula. '+link('opta')+' supplies event-meaning checks. Detailed shared research notes are in [the review index](position_attributes_review.md).', '']
        if stem == 'cb':
            lines.append('Defender activity and style must be separated from pure quality: '+link('cb')+'.')
        elif stem == 'rb_lb':
            lines.append('The source example distinguishes attacking delivery from defensively safe full-back profiles: '+link('fb')+'.')
        elif stem == 'gk':
            lines.append('Keep shot stopping, claims, interventions and distribution distinct, while avoiding an invented positioning score: '+link('gk')+'.')
        else:
            lines.append('Role templates support balancing production, creation, carrying and defensive context: '+link('radar')+'.')
        lines += ['', f'**Feature slots:** {sum(len(a[4]) for a in abilities)}. **Distinct proposed metrics:** {len(keys)}. Repeated inputs are not additional raw features.', '']
        (OUT / f'{stem}_attributes.md').write_text('\n'.join(lines), encoding='utf-8')
    con.close()
    print('Wrote eight review-only position attribute files; no database changes.')

if __name__ == '__main__':
    main()

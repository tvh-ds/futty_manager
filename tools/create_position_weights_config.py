"""One-time transcription of reviewed position documents into editable YAML."""
import importlib.util,re,sys,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('drafts',ROOT/'tools/write_position_attribute_drafts.py'); drafts=importlib.util.module_from_spec(spec); spec.loader.exec_module(drafts)
from scout.striker_features import FEATURES,ABILITIES,ST_WEIGHTS
features={f.key:dict(label=f.label,numerator=f.numerator,denominator=f.denominator,unit=f.unit,direction=f.direction) for f in FEATURES}
st={name:dict(weights) for name,weights in ABILITIES.items()}
remaining={k:v for k,v in st['Finishing'].items() if k not in ('finishing_delta90','npxg90')}
st['Finishing'].update({k:.55*v/sum(remaining.values()) for k,v in remaining.items()})
st['Finishing'].update(finishing_delta90=.30,npxg90=.15)
st['Link-Up / Creation'].update(key_passes90=.20,pass_pct=.08)
st['Carrying / 1v1'].update(take_on_pct=.20,successful_take_ons90=.14)
st['Physicality']=dict(duels_won90=.10,duel_pct=.30,aerials_won90=.10,aerial_pct=.25,dispossessed90=.25)
roles={'ST':dict(label='ST',abilities=[dict(name=n,abbreviation=a,overall_weight=ST_WEIGHTS[n],features=w) for (n,w),a in zip(st.items(),['FIN','BOX','LNK','CAR','PHY','DEF'],strict=True)])}
for key,(label,inputs,formula,direction,note) in (drafts.FEATURES|drafts.RAW).items():
 kind='appearance' if key in drafts.RAW else 'aggregate'
 denom=inputs[1] if len(inputs)>1 else 'attempts' if key=='savepct' else 'minutes'
 unit='%' if len(inputs)>1 or key=='savepct' else 'per90'
 features['pos_'+key]=dict(label=label,numerator=inputs[0],denominator=denom,unit=unit,direction=-1 if direction=='−' else 1,inputs=inputs,scope=kind,formula=formula,note=note)
for stem,(label,summary,parents) in drafts.ROLES.items():
 text=(ROOT/'Rating System'/f'{stem}_attributes.md').read_text(encoding='utf-8')
 abilities=[]
 for name,abbr,ovr,_,items in parents:
  section=text.split('### ')[next(i for i,s in enumerate(text.split('### ')) if s.startswith(tuple(f'{n}. {name} —' for n in range(1,7))))]
  weights={key:int(re.search(r'^\| '+re.escape((drafts.FEATURES|drafts.RAW)[key][0])+r' \|.*\| (\d+)% \|$',section,re.M).group(1))/100 for key,_ in items}
  abilities.append(dict(name=name,abbreviation=abbr,overall_weight=ovr/100,features={'pos_'+k:v for k,v in weights.items()}))
 roles[stem.upper()]=dict(label=label,abilities=abilities)
data=dict(version='position-weights-v1-20261008',season='2025/26',minimum_minutes=900,minimum_peers=30,features=features,positions=roles)
path=ROOT/'Rating System/position_rating_weights_config.yaml'
path.write_text('# Editable position rating weights. Values are fractions; each level must sum to 1.\n# Rebuild with: .venv/Scripts/python.exe -m scout.cli build-player-catalogue\n# Only unrecorded_zero features redistribute weight. Recorded zeros keep weight.\n'+yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')
print('Wrote',path)

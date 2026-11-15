#!/usr/bin/env python3
"""Derive a C2b GUI replay from H117's independently bounded native witness.

The new C2b action trace is a regression snapshot of a previously accepted
functional execution, not a newly inferred historical instruction sequence.
It MUST be anchored to H117's control-run, first-epoch and loop assertions.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
import re

IDENT = 'au_h117_two_epochs'
PROGRAM = 'examples/operator_scenarios/inputs/au_h117_two_epochs.k41'
SCENARIO = 'examples/operator_scenarios/au_h117_two_epochs.json'
H117_STATUS = 'PASS_FUNCTIONAL_LOOP_TWO_EPOCHS_NOT_HISTORICAL'  # immutable legacy H117 result
RECONSTRUCTION = '05000000000042'
FIRST = 97
ORIGIN = 'RECONSTRUCTED_ASSUMPTION'


def sha(data): return hashlib.sha256(data).hexdigest()
def demand(ok, why):
    if not ok: raise ValueError(why)

def read_witness(directory: Path):
    report = json.loads((directory/'RESULT.json').read_text('utf8'))
    raw = (directory/'TRACE.tsv').read_bytes()
    demand(report.get('decision')==H117_STATUS, 'H117_REFERENCE_NOT_ACCEPTED')
    for name in ('first_epoch_source_boundary', 'first_epoch_invariant',
                 'reconstructed_jump', 'second_epoch_reaches_boundary'):
        demand(report.get(name) is True, 'H117_REFERENCE_HOLD_'+name)
    demand(isinstance(report.get('sessions'),list) and len(report['sessions'])==2,'H117_SESSION_COUNT')
    ctrl,model=report['sessions']
    demand(ctrl.get('session')=='CONTROL' and model.get('session')=='RECONSTRUCTED','H117_SESSION_ORDER')
    demand(ctrl['first'].get('steps')==FIRST and model['first'].get('steps')==FIRST,'H117_FIRST_STEPS')
    demand(ctrl['first'].get('result')=='BOUNDARY_0360' and model['first'].get('result')=='BOUNDARY_0360','H117_FIRST_BOUNDARY')
    second_steps = model.get('second',{}).get('steps')
    demand(type(second_steps)==int and 1<=second_steps<=400 and report.get('second_epoch_steps')==second_steps,'H117_SECOND_STEPS')
    demand(model['second'].get('result')=='BOUNDARY_0360','H117_SECOND_BOUNDARY')
    demand(model.get('jump')=={'path':'0360','pc':'0042','T':'0'},'H117_JUMP_INVARIANT')
    source = (directory/'au_functional_private.k41').read_bytes()
    demand(source.startswith(b'KYIV41-OCT1\n') and source.endswith(b'\n') and b'\r' not in source, 'H117_COMPOSITE_IMAGE_FORMAT')
    entries={}
    for line in source.decode('ascii').splitlines()[1:]:
        a,v=line.split()
        demand(re.fullmatch(r'[0-7]{4}',a) and re.fullmatch(r'[0-7]{14}',v),'H117_COMPOSITE_RECORD')
        demand(1<=int(a,8)<0o2000 and a not in entries,'H117_COMPOSITE_RAM_ONLY_UNIQUE')
        entries[a]=v
    demand(len(entries)==222 and entries['0042']=='01306600000353' and entries['0334']=='05000000000360'
           and entries['0360']==RECONSTRUCTION,'H117_SOURCE_VS_RECONSTRUCTION_DRIFT')
    for key in ('0347','0353','0357'):
        a=model.get('before_0360_ram_'+key)
        demand(isinstance(a,str) and re.fullmatch(r'[0-7]{14}',a),'H117_BOUNDARY_DUMP_MISSING_'+key)
        demand(ctrl.get('before_0360_ram_'+key)==a,'H117_CONTROL_DUMP_DIFFERENT_'+key)
    inp=json.loads((directory/'INPUT_MANIFEST.json').read_text('utf8'))
    demand(inp['patched']['composite_sha256']==sha(source) and inp['patched']['reconstructed_0360']==RECONSTRUCTION,'H117_PROVENANCE_DRIFT')
    demand(inp['patched']['canonical_image_count']==20 and inp['patched']['source_word_count']==220,'H117_SOURCE_COMPOSITION')
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf8')),delimiter='\t'))
    demand(rows and set(rows[0])=={'epoch','index','before','after','T','A','P'},'H117_TRACE_FORMAT')
    return report,source,rows


def rows_for(rows,phase):
    return [x for x in rows if x['epoch']==phase]

def validate_rows(rows,phase,n,start,end):
    demand(len(rows)==n,phase+'_ROW_COUNT')
    demand(rows[0]['before']==start and rows[-1]['after']==end,phase+'_START_END')
    for i,e in enumerate(rows):
        demand(e['index']==str(i+1) and e['T']=='0',phase+'_INDEX_STOP_'+str(i))
        for k in ('before','after','A','P'):
            demand(bool(re.fullmatch(r'[0-7]{4}',e[k])),phase+'_BAD_REGISTER_'+k)
        if i: demand(rows[i-1]['after']==e['before'],phase+'_TRACE_DISCONTINUITY_'+str(i))


def build_actions(report,rows):
    ctrl=rows_for(rows,'CONTROL_FIRST')
    first=rows_for(rows,'RECONSTRUCTED_FIRST')
    jump=rows_for(rows,'RECONSTRUCTED_JUMP')
    second=rows_for(rows,'RECONSTRUCTED_SECOND')
    demand(len(ctrl)==FIRST,'H117_CONTROL_TRACE_COUNT')
    validate_rows(ctrl,'CONTROL_FIRST',FIRST,'0042','0360')
    validate_rows(first,'RECONSTRUCTED_FIRST',FIRST,'0042','0360')
    for a,b in zip(ctrl,first):
        demand(all(a[k]==b[k] for k in ('before','after','T','A','P')),'H117_CONTROL_TRACE_DIVERGENCE')
    validate_rows(jump,'RECONSTRUCTED_JUMP',1,'0360','0042')
    n=report['second_epoch_steps']
    validate_rows(second,'RECONSTRUCTED_SECOND',n,'0042','0360')
    # Refuse unqualified device / optional replaceable ROM access.
    for e in first+jump+second:
        pc=int(e['before'],8)
        demand(pc not in (0o232,0o252) and pc<0o3300,'H117_UNQUALIFIED_DEVICE_OR_REPLACEABLE_ROM')
    def action(op,**kw):return {'op':op,'origin':ORIGIN,**kw}
    actions=[action('state',expect={'C':'0042','STEPS':0}),
             action('set_nk',address='3000',word='20000000000000')]
    steps=0
    def segments(entries):
        nonlocal steps
        for j in range(0,len(entries),32):
            chunk=entries[j:j+32]
            steps+=len(chunk)
            last=chunk[-1]
            actions.append(action('step',count=len(chunk),expect={'executed':len(chunk),
                           'path':[e['before'] for e in chunk],
                           'state':{'C':last['after'],'A':last['A'],'P':last['P'],
                                    'T':last['T'],'STEPS':steps}}))
    segments(first)
    demand(steps==97,'FIRST_ACTION_TOTAL')
    actions.append(action('state',expect={'C':'0360','STEPS':97,'T':'0'}))
    for addr in ('0347','0353','0357'):
        actions.append(action('dump',address=addr,count=1,expect=[report['sessions'][1]['before_0360_ram_'+addr]]))
    segments(jump)
    demand(steps==98,'JUMP_ACTION_TOTAL')
    actions.append(action('state',expect={'C':'0042','STEPS':98,'T':'0'}))
    segments(second)
    demand(steps==98+n,'SECOND_ACTION_TOTAL')
    actions.append(action('state',expect={'C':'0360','STEPS':steps,'T':'0'}))
    demand(len(actions)<=64 and steps<=10000,'C2B_ACTION_LIMIT')
    return actions,steps


def generate(directory:Path):
    report,program,rows=read_witness(directory)
    actions,steps=build_actions(report,rows)
    spec={'schema':'KYIV_H116_OPERATOR_SCENARIO_V1',
          'id':IDENT,
          'description':'H117 АУ: дві епохи на одному CPU; 0360 — явно функціонально реконструйований перехід',
          'origin':ORIGIN,'rom_set':'math_module1',
          'program':{'path':PROGRAM,'sha256':sha(program)},
          'entry':'0042','max_steps':steps,'actions':actions}
    manifest_bytes=(json.dumps(spec,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
    return ({PROGRAM:program,SCENARIO:manifest_bytes},
           {'program_sha256':sha(program),'scenario_sha256':sha(manifest_bytes),
            'first_steps':97,'jump_steps':1,'second_steps':report['second_epoch_steps'],'total_steps':steps,'actions':len(actions),
            'first_boundary_ram':{a:report['sessions'][1]['before_0360_ram_'+a] for a in ('0347','0353','0357')},
            'derived_action_oracle':'H117 native trace constrained by H117 control-session and two-epoch invariants'})

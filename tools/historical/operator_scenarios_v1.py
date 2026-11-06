#!/usr/bin/env python3
"""H116-C2b. Declarative bounded operator sessions on the existing Kyiv_t backend.

Not a CPU interpreter, not a historical panel/hardware oracle. One backend process
preserves CPU, RAM, panel NK and checkpoint state across actions. ROM sets come
from the validated H116-C1a catalog and are installed via H116-C1b C++ loader.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

SCHEMA = 'KYIV_H116_OPERATOR_SCENARIO_V1'
FIXED_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
OCT = re.compile(r'[0-7]{4}\Z')
WORD = re.compile(r'[0-7]{14}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[a-z][a-z0-9_]{1,47}\Z')
ORIGINS = {'HOST_TEST', 'OPERATOR_DOCUMENTED', 'RECONSTRUCTED_ASSUMPTION'}
STATE_FIELDS = {'C','K','A','P','LOOP','T','STEPS'}

class Hold(ValueError): pass

def fail(reason): raise Hold(reason)
def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(d): return json.dumps(d,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
def module_at(path,name):
    if not path.is_file() or path.is_symlink():fail('DEPENDENCY_MISSING_'+name)
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def require_keys(value,keys,tag):
    if not isinstance(value,dict) or set(value)!=set(keys):fail('SCHEMA_FIELDS_'+tag)

def valid_addr(value):return isinstance(value,str) and bool(OCT.fullmatch(value))
def valid_word(value):return isinstance(value,str) and bool(WORD.fullmatch(value)) and int(value,8)<1<<41

def check_state(value):
    if not isinstance(value,dict) or not value or not set(value).issubset(STATE_FIELDS):fail('STATE_ORACLE_KEYS')
    for k,v in value.items():
        if k=='STEPS':
            if type(v)!=int or not 0<=v<=100000:fail('STATE_ORACLE_STEPS')
        elif k=='T':
            if v not in ('0','1'):fail('STATE_ORACLE_T')
        elif k=='K':
            if not valid_word(v):fail('STATE_ORACLE_K')
        elif not valid_addr(v):fail('STATE_ORACLE_ADDRESS')

def validate(repo,scenario_id,scenarios_dir=None):
    repo=Path(repo).resolve()
    if not isinstance(scenario_id,str) or not ID.fullmatch(scenario_id):fail('SCENARIO_ID')
    base=repo/'examples/operator_scenarios' if scenarios_dir is None else Path(scenarios_dir)
    if not base.is_absolute():base=repo/base
    # Candidate scripts may be checked in tempkyiv, but never read arbitrary folders.
    if base.is_symlink():fail('SCENARIO_DIRECTORY_SYMLINK')
    base=base.resolve()
    if base!=repo/'examples/operator_scenarios' and not base.is_relative_to((repo/'tempkyiv').resolve()):
        fail('SCENARIO_DIRECTORY_UNSAFE')
    file=base/(scenario_id+'.json')
    if file.is_symlink() or not file.is_file() or file.stat().st_size>32768:fail('SCENARIO_FILE_MISSING_OR_LARGE')
    c2a=module_at(repo/'tools/historical/rom_scenarios_v1.py','h116_c2a_existing')
    try:manifest=c2a.load_json(file)
    except ValueError as e:fail('INVALID_JSON '+str(e))
    require_keys(manifest,('schema','id','description','origin','rom_set','program','entry','max_steps','actions'),'ROOT')
    if manifest['schema']!=SCHEMA or manifest['id']!=scenario_id:fail('SCENARIO_ID_OR_SCHEMA')
    if not isinstance(manifest['description'],str) or not 1<=len(manifest['description'])<=200:
        fail('SCENARIO_DESCRIPTION')
    if not isinstance(manifest['origin'],str) or manifest['origin'] not in ORIGINS:fail('SCENARIO_ORIGIN')
    if not isinstance(manifest['rom_set'],str) or not ID.fullmatch(manifest['rom_set']):fail('ROM_SET_ID')
    require_keys(manifest['program'],('path','sha256'),'PROGRAM')
    prog=manifest['program']
    if not isinstance(prog['sha256'],str) or not SHA.fullmatch(prog['sha256']):fail('PROGRAM_SHA_FORMAT')
    try:program=c2a.existing_in_repo(repo,prog['path'])
    except (ValueError,OSError) as e:fail('PROGRAM_PATH '+str(e))
    if program.suffix!='.k41' or sha(program.read_bytes())!=prog['sha256']:fail('PROGRAM_SHA_MISMATCH')
    catalog=module_at(repo/'tools/historical/rom_catalog_v1.py','h116_c1a_existing')
    # RAM images may contain documented source comments and blank lines. The
    # replaceable-ROM catalog deliberately uses a stricter, comment-free parser.
    words=parse_ram_program(program,prog['sha256'])
    try:
        rom_report,rom_words=catalog.validate_set(repo,manifest['rom_set'])
    except (ValueError,OSError,KeyError,TypeError) as e:fail('CATALOG_OR_IMAGE '+str(e))
    if not valid_addr(manifest['entry']) or int(manifest['entry'],8) not in words:
        fail('PROGRAM_ENTRY_MISSING')
    if type(manifest['max_steps'])!=int or not 1<=manifest['max_steps']<=10000:fail('STEP_BUDGET')
    actions=manifest['actions']
    if not isinstance(actions,list) or not 1<=len(actions)<=64:fail('ACTION_COUNT')
    seen_save=False;steps=0
    for i,a in enumerate(actions):
        if not isinstance(a,dict) or not isinstance(a.get('origin'),str) or a.get('origin') not in ORIGINS:fail('ACTION_ORIGIN_'+str(i))
        op=a.get('op');keys={'origin','op'}
        if op=='set_nk':
            keys|={'address','word'}
            if a.get('address') not in ('3000','3001','3002') or not valid_word(a.get('word')):
                fail('SET_NK_INVALID')
        elif op=='clear_nk':
            keys.add('address')
            if a.get('address') not in ('3000','3001','3002'):fail('CLEAR_NK_INVALID')
        elif op=='step':
            keys|={'count','expect'}
            if type(a.get('count'))!=int or not 1<=a['count']<=32:fail('STEP_COUNT')
            e=a.get('expect');require_keys(e,('executed','path','state'),'STEP_EXPECT')
            if type(e['executed'])!=int or not 1<=e['executed']<=a['count']:fail('STEP_EXECUTED')
            if not isinstance(e['path'],list) or len(e['path'])!=e['executed'] or not all(valid_addr(x) for x in e['path']):fail('STEP_PATH')
            check_state(e['state']);steps+=a['count']
        elif op=='dump':
            keys|={'address','count','expect'}
            if not valid_addr(a.get('address')) or type(a.get('count'))!=int or not 1<=a['count']<=64 or int(a['address'],8)+a['count']>0o4000:
                fail('DUMP_RANGE')
            if not isinstance(a.get('expect'),list) or len(a['expect'])!=a['count'] or not all(valid_word(x) for x in a['expect']):fail('DUMP_ORACLE')
        elif op=='state':
            keys.add('expect');check_state(a.get('expect'))
        elif op=='save':seen_save=True
        elif op=='restore':
            if not seen_save:fail('RESTORE_WITHOUT_SAVE')
        else:fail('UNSUPPORTED_ACTION_'+str(op))
        if set(a)!=keys:fail('ACTION_FIELDS_'+str(i))
    if steps<1 or steps>manifest['max_steps']:fail('STEP_TOTAL_BUDGET')
    return manifest,program,rom_report

def parse_ram_program(path, expected_sha):
    """C++ host-image-compatible RAM input, distinct from strict C1a ROM records.

    SHA pins the *original bytes*, including any source comments. Blank and
    #-comment lines are valid in historic RAM `.k41` images; unknown data words
    and malformed octal records are never repaired or filled.
    """
    raw=path.read_bytes()
    if not isinstance(expected_sha,str) or not SHA.fullmatch(expected_sha):
        fail('PROGRAM_SHA_FORMAT')
    if sha(raw)!=expected_sha:fail('PROGRAM_SHA_MISMATCH')
    if len(raw)>32768:fail('PROGRAM_TOO_LARGE')
    try:lines=raw.decode('utf-8-sig').splitlines()
    except UnicodeDecodeError:fail('PROGRAM_UTF8_INVALID')
    seen_header=False
    words={}
    for line in lines:
        text=line.split('#',1)[0].strip()
        if not text:continue
        if not seen_header:
            if text!='KYIV41-OCT1':fail('PROGRAM_HEADER_INVALID')
            seen_header=True
            continue
        parts=text.split()
        if len(parts)!=2 or not valid_addr(parts[0]) or not valid_word(parts[1]):
            fail('PROGRAM_RECORD_INVALID')
        addr=int(parts[0],8)
        if not 1<=addr<0o2000:fail('PROGRAM_RAM_ONLY')
        if addr in words:fail('PROGRAM_DUPLICATE_ADDRESS')
        words[addr]=parts[1]
    if not seen_header or not words:fail('PROGRAM_EMPTY_OR_MISSING_HEADER')
    return words

def command_for(action):
    op=action['op']
    if op=='set_nk':return 'SETNK\t'+action['address']+'\t'+action['word']
    if op=='clear_nk':return 'CLEARNK\t'+action['address']
    if op=='step':return 'STEP\t'+str(action['count'])
    if op=='dump':return 'DUMP\t'+action['address']+'\t'+str(action['count'])
    if op=='state':return 'STATE'
    return 'SAVE' if op=='save' else 'RESTORE'

def fields_for(line,verb):
    fields=line.rstrip('\n').split('\t')
    if len(fields)<2 or fields[0]!='OK' or fields[1]!=verb:fail('BACKEND_PROTOCOL_'+verb+' '+line[:160])
    data={}
    for item in fields[2:]:
        if '=' not in item:fail('BACKEND_FIELD_MALFORMED')
        k,v=item.split('=',1)
        if not k or k in data:fail('BACKEND_DUPLICATE_FIELD')
        data[k]=v
    return data

def test_state(data,expected):
    for k,v in expected.items():
        if data.get(k)!=str(v):fail('STATE_MISMATCH_'+k)

def evaluate_action(action,row):
    op=action['op'];verb={'set_nk':'SETNK','clear_nk':'CLEARNK','step':'STEP','dump':'DUMP','state':'STATE','save':'SAVE','restore':'RESTORE'}[op]
    data=fields_for(row,verb)
    if op=='set_nk' and (data.get('ADDR')!=action['address'] or data.get('WORD')!=action['word']):fail('NK_SET_REPLY')
    if op=='clear_nk' and data.get('ADDR')!=action['address']:fail('NK_CLEAR_REPLY')
    if op=='step':
        e=action['expect'];path=','.join(e['path'])
        if data.get('EXECUTED')!=str(e['executed']) or data.get('PATH')!=path:fail('STEP_PATH_OR_COUNT_MISMATCH')
        test_state(data,e['state'])
    if op=='state':test_state(data,action['expect'])
    if op=='dump':
        if data.get('START')!=action['address'] or data.get('COUNT')!=str(action['count']):fail('DUMP_REPLY_RANGE')
        if data.get('DATA')!=','.join(action['expect']):fail('DUMP_VALUE_MISMATCH')
    return {'op':op,'origin':action['origin'],'reply':row}

def run(repo,scenario_id,backend,out,scenarios_dir=None,timeout=60):
    repo=Path(repo).resolve()
    manifest,program,report=validate(repo,scenario_id,scenarios_dir)
    backend=Path(backend);out=Path(out)
    if backend.is_symlink() or not backend.is_file():fail('BACKEND_EXE_MISSING_OR_SYMLINK')
    backend=backend.resolve()
    if out.exists() or out.is_symlink() or not out.resolve().is_relative_to((repo/'tempkyiv').resolve()):
        fail('OUTPUT_MUST_BE_NEW_UNDER_TEMPKYIV')
    out.mkdir(parents=True,exist_ok=False)
    catalog=module_at(repo/'tools/historical/rom_catalog_v1.py','h116_c1a_exec')
    try:
        catalog.prepare(repo,manifest['rom_set'],out/'rom')
        overlay=out/'rom/replaceable.k41'
        overlay_sha=sha(overlay.read_bytes())
        rom=repo/'mem/ROM.txt'
        commands=['PING','LOAD\t'+str(program.resolve())+'\t'+manifest['entry']]
        commands.extend(command_for(x) for x in manifest['actions'])
        commands.append('QUIT')
        # All commands are prevalidated; private subprocess has strict timeout.
        exe_args=[str(backend),str(rom),'--rom-set-image',str(overlay),'--rom-set-sha256',overlay_sha]
        completed=subprocess.run(exe_args,input='\n'.join(commands)+'\n',text=True,
            capture_output=True,timeout=timeout,cwd=repo)
        (out/'BACKEND_STDOUT.txt').write_text(completed.stdout,encoding='utf-8')
        (out/'BACKEND_STDERR.txt').write_text(completed.stderr,encoding='utf-8')
        if completed.returncode!=0:fail('BACKEND_RETURN_CODE_'+str(completed.returncode))
        lines=completed.stdout.splitlines()
        if len(lines)!=len(commands):fail('BACKEND_REPLY_COUNT')
        ping=fields_for(lines[0],'PING')
        if ping.get('PROTOCOL')!='1' or ping.get('ROM_SHA256')!=FIXED_SHA or ping.get('ROMSET_SHA256')!=overlay_sha:
            fail('BACKEND_ROM_IDENTITY')
        loaded=fields_for(lines[1],'LOAD')
        if loaded.get('C')!=manifest['entry'] or loaded.get('STEPS')!='0':fail('BACKEND_LOAD_STATE')
        results=[]
        for a,row in zip(manifest['actions'],lines[2:-1]):results.append(evaluate_action(a,row))
        fields_for(lines[-1],'QUIT')
        result={'status':'PASS_H116_C2B_PERSISTENT_OPERATOR_HOST_NOT_HISTORICAL',
            'id':scenario_id,'rom_set':manifest['rom_set'],
            'actions':len(results),'sha256_rom_set':overlay_sha,'cpu_steps_requested':sum(a['count'] for a in manifest['actions'] if a['op']=='step'),
            'native_cpu':True,'hardware_oracle':False,'log':results}
        (out/'RUN.json').write_text(write_json(result),encoding='utf-8')
        return result
    except Exception as e:
        (out/'HOLD.json').write_text(write_json({'status':'HOLD_H116_C2B','reason':str(e)}),encoding='utf-8')
        raise

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    ap.add_argument('--scenarios-dir',type=Path)
    sub=ap.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate');v.add_argument('scenario')
    r=sub.add_parser('run');r.add_argument('scenario');r.add_argument('--backend',type=Path,required=True);r.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.command=='validate':
            spec,_,report=validate(a.repo,a.scenario,a.scenarios_dir)
            print('H116_C2B_PREFLIGHT_PASS '+write_json({'id':spec['id'],'rom_set':report['set'],'actions':len(spec['actions'])}).strip())
        else:
            result=run(a.repo,a.scenario,a.backend,a.out,a.scenarios_dir)
            print(result['status']+' '+write_json({'id':result['id'],'actions':result['actions']}).strip())
        return 0
    except (Hold,OSError,ValueError,subprocess.TimeoutExpired,subprocess.SubprocessError) as exc:
        print('H116_C2B_HOLD '+str(exc),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())

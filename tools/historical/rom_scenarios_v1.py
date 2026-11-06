#!/usr/bin/env python3
"""H116-C2a: declarative, bounded ROM-set scenarios via existing production CLI.

No CPU implementation and no special program/ROM-specific branches. JSON is
strict data, with SHA-256 program and module pins and an external result oracle.
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

SCHEMA = 'KYIV_H116_ROM_SCENARIO_V1'
IDS = re.compile(r'[a-z][a-z0-9_]{1,47}\Z')
OCT4 = re.compile(r'[0-7]{4}\Z')
OCT14 = re.compile(r'[0-7]{14}\Z')
SHA = re.compile(r'[a-f0-9]{64}\Z')
FIXED_SHA = 'a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38'
FIELDS = {'schema','id','description','origin','rom_set','mode','program',
          'entry','max_steps','end_pointer','watches','expect'}
class ScenarioError(ValueError): pass
def reject(why): raise ScenarioError(why)
def digest(data):return hashlib.sha256(data).hexdigest()
def no_duplicate_pairs(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:reject('DUPLICATE_JSON_KEY')
        obj[k]=v
    return obj
def valid_id(value):return isinstance(value,str) and IDS.fullmatch(value) is not None
def valid_addr(value):return isinstance(value,str) and OCT4.fullmatch(value) is not None
def valid_word(value):return isinstance(value,str) and OCT14.fullmatch(value) is not None and int(value,8)<1<<41
def staged_root(repo,root):
    """Candidate package inputs may live only under tempkyiv, never elsewhere."""
    if root is None:return None
    repo=Path(repo).resolve()
    raw=Path(root)
    if not raw.is_absolute():reject('STAGED_PROGRAM_ROOT_NOT_ABSOLUTE')
    try:parts=raw.relative_to(repo).parts
    except ValueError:reject('STAGED_PROGRAM_ROOT_UNSAFE')
    at=repo
    for part in parts:
        at=at/part
        if at.is_symlink():reject('STAGED_PROGRAM_ROOT_SYMLINK')
    canonical=raw.resolve()
    if (not canonical.is_relative_to((repo/'tempkyiv').resolve()) or
            canonical==(repo/'tempkyiv').resolve() or not canonical.is_dir()):
        reject('STAGED_PROGRAM_ROOT_UNSAFE')
    return canonical

def existing_in_repo(repo,rel,prefix='examples',staged=None):
    if not isinstance(rel,str) or not rel.startswith(prefix+'/') or '\\' in rel or ':' in rel:
        reject('UNSAFE_PROGRAM_PATH')
    parts=rel.split('/')
    if not parts or any(x in ('','.','..') for x in parts):reject('UNSAFE_PROGRAM_PATH')
    # Prefer the already installed canonical input. Only absent new inputs may
    # be read from the explicit package stage, and only with the same SHA gate.
    for root in (repo,staged):
        if root is None:continue
        at=Path(root)
        for part in parts:
            at=at/part
            if at.is_symlink():reject('SYMLINK_NOT_ALLOWED')
        if at.is_file():
            if not at.resolve().is_relative_to(Path(root).resolve()):
                reject('PROGRAM_MISSING_OR_UNSAFE')
            return at
        if at.exists():reject('PROGRAM_MISSING_OR_UNSAFE')
    reject('PROGRAM_MISSING_OR_UNSAFE')

def load_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32768:
        reject('SCENARIO_MANIFEST_MISSING_OR_TOO_LARGE')
    try:return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=no_duplicate_pairs)
    except (UnicodeError,ValueError) as exc:reject('SCENARIO_INVALID_JSON '+str(exc))

def catalog_module(repo):
    path=repo/'tools/historical/rom_catalog_v1.py'
    if not path.is_file() or path.is_symlink():reject('CATALOG_MISSING')
    spec=importlib.util.spec_from_file_location('h116_c2a_catalog',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def check(repo:Path,scenario_id:str,scenarios_dir=None,program_staging_root=None):
    repo=Path(repo).resolve()
    if not valid_id(scenario_id):reject('SCENARIO_ID_INVALID')
    staged=staged_root(repo,program_staging_root)
    base=Path(scenarios_dir).resolve() if scenarios_dir is not None else repo/'examples/rom_scenarios'
    allowed=(repo/'examples/rom_scenarios',repo/'tempkyiv')
    if not (base==allowed[0] or base.is_relative_to(allowed[1])):
        reject('SCENARIO_DIRECTORY_OUTSIDE_ALLOWED_AREA')
    file=base/(scenario_id+'.json')
    spec=load_json(file)
    if not isinstance(spec,dict) or set(spec)!=FIELDS or spec['schema']!=SCHEMA or spec['id']!=scenario_id:
        reject('SCENARIO_SCHEMA_OR_ID')
    for k in ('description','origin'):
        if not isinstance(spec[k],str) or not spec[k].strip() or len(spec[k])>200:
            reject('SCENARIO_TEXT_INVALID')
    mode=spec['mode']
    if mode not in ('image','fp-image'):reject('SCENARIO_MODE_INVALID')
    if not valid_id(spec['rom_set']):reject('SCENARIO_SET_ID')
    prog=spec['program']
    if not isinstance(prog,dict) or set(prog)!={'path','sha256'}:
        reject('SCENARIO_PROGRAM_FIELDS')
    if not isinstance(prog['sha256'],str) or not SHA.fullmatch(prog['sha256']):reject('SCENARIO_PROGRAM_SHA_FORMAT')
    program=existing_in_repo(repo,prog['path'],staged=staged)
    if not program.name.endswith('.k41'):reject('SCENARIO_PROGRAM_EXTENSION')
    raw=program.read_bytes()
    if digest(raw)!=prog['sha256']:reject('SCENARIO_PROGRAM_SHA_DRIFT')
    cat=catalog_module(repo)
    # The same strict octal parser as C1a, but RAM-only for user program.
    records=cat.parse_k41(program,prog['sha256'])
    if any(a<1 or a>=0o2000 for a in records):reject('SCENARIO_NOT_RAM_PROGRAM')
    entry=spec['entry']
    if not valid_addr(entry) or int(entry,8) not in records:reject('SCENARIO_ENTRY_MISSING')
    limit=spec['max_steps']
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=100000:
        reject('SCENARIO_STEP_LIMIT')
    end=spec['end_pointer']
    if mode=='image':
        if end is not None:reject('SCENARIO_IMAGE_END_POINTER_FORBIDDEN')
    elif not valid_addr(end) or int(end,8) not in records:
        reject('SCENARIO_FP_END_POINTER_MISSING')
    watches=spec['watches']
    if not isinstance(watches,dict) or not watches or len(watches)>32:
        reject('SCENARIO_WATCH_COUNT')
    for addr,word in watches.items():
        if not valid_addr(addr) or (not 1<=int(addr,8)<0o2000 and not 0o3000<=int(addr,8)<0o4000):
            reject('SCENARIO_WATCH_ADDRESS')
        if not valid_word(word):reject('SCENARIO_WATCH_WORD')
    expect=spec['expect']
    if not isinstance(expect,dict) or set(expect)!={'status','steps','dispatches'}:
        reject('SCENARIO_EXPECT_FIELDS')
    if expect['status']!=('END_POINTER' if mode=='fp-image' else 'CPU_STOP'):
        reject('SCENARIO_EXPECT_STATUS')
    if (isinstance(expect['steps'],bool) or not isinstance(expect['steps'],int)
            or not 1<=expect['steps']<=limit):reject('SCENARIO_EXPECT_STEPS')
    if mode=='image':
        if expect['dispatches'] is not None:reject('SCENARIO_IMAGE_DISPATCHES')
    elif (isinstance(expect['dispatches'],bool) or not isinstance(expect['dispatches'],int)
            or expect['dispatches']<1 or expect['dispatches']>expect['steps']):
        reject('SCENARIO_FP_DISPATCHES')
    report,words=cat.validate_set(repo,spec['rom_set'])
    if mode=='fp-image' and 0o3300 not in words:reject('SCENARIO_FP_DISPATCHER_NOT_PRESENT')
    if mode=='image' and any(int(a,8) in records for a in watches if int(a,8)<0o2000):
        pass # Program RAM watches are allowed and tested after execution.
    return spec,report

def evaluate(spec,completed):
    if completed.returncode!=0:reject('SCENARIO_CPU_RETURN_CODE_'+str(completed.returncode))
    mode=spec['mode']
    prefix='H115-FP-' if mode=='fp-image' else 'D15A2-'
    run_lines=[line for line in completed.stdout.splitlines() if line.startswith(prefix+'RUN STATUS=')]
    if len(run_lines)!=1:reject('SCENARIO_RUN_RECORD_COUNT')
    line=run_lines[0]
    m=re.match(r'^'+re.escape(prefix)+r'RUN STATUS=([A-Z_]+) STEPS=(\d+)(?: DISPATCHES=(\d+))?\b',line)
    if m is None:reject('SCENARIO_RUN_RECORD_FORMAT')
    exp=spec['expect']
    if m.group(1)!=exp['status']:reject('SCENARIO_RESULT_STATUS_MISMATCH')
    if int(m.group(2))!=exp['steps']:reject('SCENARIO_RESULT_STEPS_MISMATCH')
    if mode=='fp-image' and (m.group(3) is None or int(m.group(3))!=exp['dispatches']):
        reject('SCENARIO_RESULT_DISPATCHES_MISMATCH')
    if mode=='image' and m.group(3) is not None:reject('SCENARIO_UNEXPECTED_DISPATCHES')
    found={}
    for row in completed.stdout.splitlines():
        if not row.startswith(prefix+'WATCH ADDR='):continue
        matched=re.fullmatch(re.escape(prefix)+r'WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})',row)
        if not matched:reject('SCENARIO_WATCH_FORMAT')
        address=matched.group(1)
        if address in found:reject('SCENARIO_WATCH_DUPLICATE')
        found[address]=matched.group(2)
    if set(found)!=set(spec['watches']):reject('SCENARIO_WATCH_SET_MISMATCH')
    if found!=spec['watches']:reject('SCENARIO_WATCH_VALUE_MISMATCH')
    return {'status':'PASS_H116_C2A_NATIVE_SCENARIO_NOT_HISTORICAL',
            'id':spec['id'],'rom_set':spec['rom_set'], 'mode':mode,
            'steps':exp['steps'],'dispatches':exp['dispatches'],'watches':found,
            'native_executed':True,'historical_hardware':'NOT_TESTED'}

def execute(repo:Path,scenario_id:str,exe:Path,out:Path,timeout:int=60,scenarios_dir=None,program_staging_root=None):
    repo=Path(repo).resolve()
    spec,report=check(repo,scenario_id,scenarios_dir,program_staging_root) # All inputs validated before outputs/CPU.
    exe=Path(exe).resolve()
    if not exe.is_file():reject('SCENARIO_EXE_MISSING')
    out=Path(out)
    root=repo/'tempkyiv'
    if not out.resolve().is_relative_to(root.resolve()) or out.is_symlink() or out.exists():
        reject('SCENARIO_OUTPUT_NOT_NEW_UNDER_TEMPKYIV')
    out.mkdir(parents=True,exist_ok=False)
    cat=catalog_module(repo)
    try:
        cat.prepare(repo,spec['rom_set'],out/'rom')
        rom_file=out/'rom/replaceable.k41'
        romsha=digest(rom_file.read_bytes())
        program=existing_in_repo(repo,spec['program']['path'],staged=staged_root(repo,program_staging_root))
        if digest(program.read_bytes())!=spec['program']['sha256']:reject('SCENARIO_PROGRAM_SHA_DRIFT')
        opts=([str(exe),spec['mode'],str(program),spec['entry'],str(spec['max_steps'])])
        if spec['mode']=='fp-image':
            opts += ['--fp-rom',str(rom_file),'--fp-sha256',romsha,
                     '--end-pointer',spec['end_pointer']]
        else:
            opts += ['--rom-set-image',str(rom_file),'--rom-set-sha256',romsha,
                     '--rom-file',str(repo/'mem/ROM.txt'),'--rom-sha256',FIXED_SHA]
        for a in spec['watches']:opts+=['--watch',a]
        completed=subprocess.run(opts,cwd=repo,capture_output=True,text=True,
                encoding='utf-8',errors='replace',timeout=timeout,check=False)
        (out/'STDOUT.txt').write_text(completed.stdout,encoding='utf-8')
        (out/'STDERR.txt').write_text(completed.stderr,encoding='utf-8')
        result=evaluate(spec,completed)
        result.update({'rom_sha256':romsha,'program_sha256':spec['program']['sha256'],
                       'command_argv':opts,'catalog_report':report})
    except (ScenarioError,subprocess.TimeoutExpired,OSError) as exc:
        result={'status':'HOLD_H116_C2A','id':scenario_id,'reason':str(exc)}
        (out/'RUN.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        raise
    (out/'RUN.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    sums=''.join(f'{digest((out/name).read_bytes())}  {name}\n' for name in ['RUN.json','STDOUT.txt','STDERR.txt','rom/replaceable.k41','rom/RESULT.json'])
    (out/'SHA256SUMS.txt').write_text(sums,encoding='ascii')
    return result

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    ap.add_argument('--scenarios-dir',type=Path,help='Optional isolated scenario directory under tempkyiv/')
    ap.add_argument('--program-staging-root',type=Path,help='Explicit candidate payload directory under tempkyiv (absent programs only)')
    sub=ap.add_subparsers(dest='action',required=True)
    sub.add_parser('list')
    val=sub.add_parser('validate');val.add_argument('scenario_id')
    run=sub.add_parser('run');run.add_argument('scenario_id');run.add_argument('--exe',type=Path,required=True);run.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.action=='list':
            root=args.scenarios_dir if args.scenarios_dir else args.repo/'examples/rom_scenarios'
            ids=[p.stem for p in sorted(root.glob('*.json')) if valid_id(p.stem) and not p.is_symlink()]
            print(json.dumps(ids))
        elif args.action=='validate':
            spec,report=check(args.repo,args.scenario_id,args.scenarios_dir,args.program_staging_root)
            print(json.dumps({'status':'PASS_H116_C2A_SCENARIO_VALIDATED_NOT_NATIVE','id':spec['id'],'catalog':report},sort_keys=True))
        else:print(json.dumps(execute(args.repo,args.scenario_id,args.exe,args.out,scenarios_dir=args.scenarios_dir,program_staging_root=args.program_staging_root),sort_keys=True))
    except (ScenarioError,OSError,ValueError,subprocess.TimeoutExpired) as e:
        print('H116_C2A_HOLD '+str(e),file=sys.stderr)
        return 2
    return 0
if __name__=='__main__':raise SystemExit(main())

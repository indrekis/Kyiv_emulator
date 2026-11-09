#!/usr/bin/env python3
"""H116-H1: validated catalog/scenario bridge for the Qt frontend.

The bridge delegates ROM rules to C1a and scenario rules to C2a. It never
executes the CPU and only prepares new pinned images below tempkyiv.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


class BrowserError(ValueError):
    pass


def mod(path: Path, name: str):
    if not path.is_file() or path.is_symlink():
        raise BrowserError('BRIDGE_DEPENDENCY_MISSING')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BrowserError('BRIDGE_IMPORT_FAILED')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_components(repo: Path):
    tools = repo / 'tools' / 'historical'
    return (mod(tools / 'rom_catalog_v1.py', 'h116_h1_catalog'),
            mod(tools / 'rom_scenarios_v1.py', 'h116_h1_scenarios'))


def list_items(repo: Path):
    cat, sc = load_components(repo)
    base = repo / 'examples' / 'rom_catalog' / 'sets'
    if not base.is_dir():
        raise BrowserError('SET_CATALOG_MISSING')
    sets = []
    for p in sorted(base.iterdir()):
        if p.suffix != '.json':
            continue
        if p.is_symlink() or not cat.id_ok(p.stem):
            raise BrowserError('SET_CATALOG_UNSAFE')
        info, _ = cat.validate_set(repo, p.stem)
        sources = sorted({m['provenance'] for m in info['modules']})
        sets.append({'id': p.stem, 'description': cat.read_json(p)['description'],
                     'provenance': ', '.join(sources), 'unknown': info['unknown_slots_words'],
                     'words': info['words']})
    scenarios_dir = repo / 'examples' / 'rom_scenarios'
    if not scenarios_dir.is_dir():
        raise BrowserError('SCENARIO_DIRECTORY_MISSING')
    scenarios = []
    for p in sorted(scenarios_dir.iterdir()):
        if p.suffix != '.json':
            continue
        if p.is_symlink() or not sc.valid_id(p.stem):
            raise BrowserError('SCENARIO_FILE_UNSAFE')
        spec, _ = sc.check(repo, p.stem)
        scenarios.append({'id': spec['id'], 'description': spec['description'],
                          'origin': spec['origin'], 'rom_set': spec['rom_set'],
                          'program': spec['program']['path'], 'entry': spec['entry'],
                          'mode': spec['mode'], 'end_pointer': spec['end_pointer']})
    if not sets:
        raise BrowserError('EMPTY_ROM_CATALOG')
    return {'status': 'PASS_H116_H1_CATALOG_VALIDATED',
            'sets': sets, 'scenarios': scenarios}


def prepare(repo: Path, set_id: str, out: Path, scenario_id: str | None):
    cat, sc = load_components(repo)
    if not cat.id_ok(set_id):
        raise BrowserError('INVALID_SET_ID')
    scenario = None
    program_bytes = None
    if scenario_id:
        scenario, _ = sc.check(repo, scenario_id)
        if scenario['rom_set'] != set_id:
            raise BrowserError('SCENARIO_SET_MISMATCH')
        src = sc.existing_in_repo(repo, scenario['program']['path'])
        program_bytes = src.read_bytes()
        if hashlib.sha256(program_bytes).hexdigest() != scenario['program']['sha256']:
            raise BrowserError('SCENARIO_PROGRAM_SHA_DRIFT')
    # C1a enforces a NEW, symlink-safe destination under tempkyiv and validates
    # every selected module, the cabinet ROM pin, occupied slots and unknowns.
    result = cat.prepare(repo, set_id, out)
    rom_image = out / 'replaceable.k41'
    rom_sha = hashlib.sha256(rom_image.read_bytes()).hexdigest()
    response = {'status': 'PASS_H116_H1_PREPARED_NOT_NATIVE', 'set': set_id,
                'rom_path': str(rom_image), 'sha256': rom_sha,
                'provenance': sorted({m['provenance'] for m in result['modules']}),
                'unknown': result['unknown_slots_words']}
    if scenario is not None:
        copied = out / 'program.k41'
        copied.write_bytes(program_bytes)
        if hashlib.sha256(copied.read_bytes()).hexdigest() != scenario['program']['sha256']:
            raise BrowserError('PROGRAM_COPY_SHA_MISMATCH')
        response.update({'scenario_id': scenario_id, 'program_path': str(copied),
                         'entry': scenario['entry'], 'program_sha256': scenario['program']['sha256']})
    return response


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    cmd = parser.add_subparsers(dest='command', required=True)
    cmd.add_parser('list')
    p = cmd.add_parser('prepare')
    p.add_argument('set_id')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scenario')
    a = parser.parse_args(argv)
    repo = a.repo.resolve()
    try:
        if a.command == 'list':
            result = list_items(repo)
        else:
            result = prepare(repo, a.set_id, a.out, a.scenario)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (BrowserError, OSError, ValueError, TypeError, KeyError) as e:
        print('H116_H1_HOLD ' + str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""H118: fail-closed C2b operator-program preparation for the production Qt GUI.

This bridge does NOT run the CPU: Qt sends the validated operations to its
existing persistent production Kyiv_t backend. All work is new tempkyiv files.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


class Hold(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path, name: str):
    if not path.is_file() or path.is_symlink():
        raise Hold('DEPENDENCY_MISSING_' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Hold('IMPORT_FAILED_' + name)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def components(repo: Path):
    tools = repo / 'tools/historical'
    return (load(tools / 'operator_scenarios_v1.py', 'h118_existing_c2b'),
            load(tools / 'rom_catalog_v1.py', 'h118_existing_c1a'))


def list_items(repo: Path):
    op, _ = components(repo)
    directory = repo / 'examples/operator_scenarios'
    if directory.is_symlink() or not directory.is_dir():
        raise Hold('OPERATOR_CATALOG_INVALID')
    items = []
    for path in sorted(directory.iterdir()):
        if path.suffix != '.json':
            continue
        if path.is_symlink() or not re.fullmatch(r'[a-z][a-z0-9_]{1,47}', path.stem):
            raise Hold('OPERATOR_UNSAFE_ID')
        scenario, _, report = op.validate(repo, path.stem)
        items.append({'id': scenario['id'], 'description': scenario['description'],
                      'origin': scenario['origin'], 'entry': scenario['entry'],
                      'rom_set': scenario['rom_set'], 'actions': len(scenario['actions']),
                      'source': 'C2b; HOST bounded, not physical hardware'})
    if not items:
        raise Hold('OPERATOR_CATALOG_EMPTY')
    return {'status': 'PASS_H118_OPERATOR_LIST', 'items': items}


def prepare(repo: Path, scenario_id: str, out: Path):
    op, cat = components(repo)
    scenario, program, _ = op.validate(repo, scenario_id)
    root = repo / 'tempkyiv'
    if root.is_symlink() or not root.is_dir():
        raise Hold('TEMPKYIV_MISSING_OR_SYMLINK')
    out = out.absolute()
    if out.exists() or out.is_symlink() or not out.resolve().is_relative_to(root.resolve()):
        raise Hold('OUTPUT_NOT_NEW_UNDER_TEMPKYIV')
    if program.is_symlink() or sha(program.read_bytes()) != scenario['program']['sha256']:
        raise Hold('PINNED_PROGRAM_DRIFT')
    # All input validation precedes any private output. No tracked mutation.
    out.mkdir(parents=True, exist_ok=False)
    cat.prepare(repo, scenario['rom_set'], out / 'rom')
    rom = out / 'rom/replaceable.k41'
    program_copy = out / 'program.k41'
    program_copy.write_bytes(program.read_bytes())
    if sha(program_copy.read_bytes()) != scenario['program']['sha256']:
        raise Hold('PROGRAM_COPY_SHA_MISMATCH')
    result = {
        'status': 'PASS_H118_OPERATOR_PREPARED_NOT_EXECUTED',
        'id': scenario['id'], 'description': scenario['description'],
        'origin': scenario['origin'], 'rom_set': scenario['rom_set'],
        'entry': scenario['entry'], 'max_steps': scenario['max_steps'],
        'program_path': str(program_copy), 'program_sha256': scenario['program']['sha256'],
        'rom_path': str(rom), 'rom_sha256': sha(rom.read_bytes()),
        'actions': scenario['actions'], 'hardware_oracle': False,
        'execution_scope': 'HOST_OPERATOR_ON_EXISTING_PERSISTENT_KYIV_T',
    }
    manifest = out / 'RESULT.json'
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (out / 'SHA256SUMS.txt').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in
        [manifest, program_copy]), encoding='ascii')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    p = sub.add_parser('prepare')
    p.add_argument('scenario_id')
    p.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        repo = args.repo.resolve()
        result = list_items(repo) if args.command == 'list' else prepare(repo, args.scenario_id, args.out)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('H118_OPERATOR_HOLD ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

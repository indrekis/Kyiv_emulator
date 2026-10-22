#!/usr/bin/env python3
"""H3/C2: external termination at precisely signaled test-only B3 boundaries.

No modifications to production files; private headers live in a temp directory.
No crash durability or concurrent-writer claim. Independent KYIVDRM1 oracle.
"""
import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = '9ff476b9cf4d5a632f4af2649ff46aca918d4377'
PROFILE = 'h3c2-kill'
DRUMS, TRACKS, SLOTS = 3, 2, 8
N = DRUMS * TRACKS * SLOTS
SIGN = 1 << 40
WORD_MASK = (1 << 41) - 1
POLY = 0x42F0E1EBA9EA3693
U64 = (1 << 64) - 1
INITIAL = (0, SIGN, 0x111001)
UPDATED = (SIGN, 0, 0x22334)
GUARD = '.h3c2-private-sandbox'
GUARD_BYTES = b'H3C2-PRIVATE-TEST-ONLY\n'
PHASES = ('PARTIAL_TEMP', 'PRE_RENAME', 'POST_RENAME')


def check(ok, code, proc=None):
    if not ok:
        suffix = '' if proc is None else (
            f' rc={proc.returncode} stdout={proc.stdout[-600:]!r}'
            f' stderr={proc.stderr[-600:]!r}')
        raise AssertionError(code + suffix)


def crc64(data):
    state = 0
    for byte in data:
        state ^= byte << 56
        for _ in range(8):
            state = ((state << 1) ^ (POLY if state & (1 << 63) else 0)) & U64
    return state


def canonical(values=None):
    label = PROFILE.encode('ascii')
    words = {} if values is None else {3+i: v for i,v in enumerate(values)}
    assert all(0 <= v <= WORD_MASK for v in words.values())
    bitmap = bytearray((N+7)//8)
    payload = [0] * N
    for i, v in words.items():
        bitmap[i//8] |= 1 << (i % 8)
        payload[i] = v
    head = struct.pack('<8sIIQQQQQII', b'KYIVDRM1', 1, 64, DRUMS,
                       TRACKS, SLOTS, N, len(words), len(label), 0)
    blob = head + label + bitmap + b''.join(struct.pack('<Q', p) for p in payload)
    return blob + struct.pack('<Q', crc64(blob))


def ins(op, a1, a2, a3):
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3


def expressions(values, read):
    pairs = [(0o500, ins(0o25, 0 if read else 1, 0o100, 3))]
    if read:
        pairs += [(0o501, ins(0o24, 0o210, 0o212, 0o502))]
        pairs += [(0o502+i, ins(0o14, 0o210+i, 0, 0o3)) for i in range(3)]
        pairs += [(0o505, ins(0o33, 0, 0, 0))]
    else:
        pairs += [(0o501, ins(0o23, 0o200, 0o202, 0o502)),
                  (0o502, ins(0o33, 0, 0, 0))]
        pairs += [(0o200+i, w) for i, w in enumerate(values)]
    return ['expression', *(f'({addr},{val})' for addr,val in pairs), '0500']


def args_attach(image):
    return ['--experimental-drum', str(image), PROFILE,
            str(TRACKS), str(SLOTS), '1']


def call(binary, args, cwd, timeout, env=None):
    return subprocess.run([str(binary), *map(str, args)], cwd=cwd,
                          capture_output=True, text=True, errors='replace',
                          encoding='utf-8', timeout=timeout, env=env, check=False)


def seeded(creator, emu, directory, timeout):
    image = directory/'crash.kdr'
    p = call(creator, ['create', image, PROFILE, TRACKS, SLOTS], directory, timeout)
    check(p.returncode == 0 and 'D14C2H3B1-CREATE PASS' in p.stdout,
          'CREATE_FAILED', p)
    check(image.read_bytes() == canonical(), 'NONCANONICAL_EMPTY', p)
    p = call(emu, expressions(INITIAL, False) + args_attach(image), directory, timeout)
    check(p.returncode == 0 and 'Result:' in p.stdout, 'SEED_WRITE_FAILED', p)
    check(image.read_bytes() == canonical(INITIAL), 'NONCANONICAL_SEED', p)
    return image


def fresh_read(emu, image, values, timeout):
    before = image.read_bytes()
    p = call(emu, expressions(values, True) + args_attach(image),
             image.parent, timeout)
    check(p.returncode == 0 and 'Result:' in p.stdout, 'FRESH_READ_FAILED', p)
    raw = [int(t[3:]) for s in p.stdout.splitlines()
           if (t := s.strip()).startswith('orr') and t[3:].isdigit()]
    check(raw == list(values), f'RAW_FRESH_MISMATCH actual={raw}', p)
    check(image.read_bytes() == before, 'FRESH_READ_MUTATED_TARGET')


# All alterations below are to an IN-MEMORY COPY of the unchanged B3 header.
HOOK = '''
// H3C2 TEST-ONLY INSTRUMENTATION. NEVER SHIP OR INCLUDE IN PRODUCTION.
inline void h3c2_test_hook(const std::filesystem::path& final, const char* point) {
    const char* env = std::getenv("H3C2_TEST_PHASE");
    if (!env || std::string(env) != point) return;
    const auto folder = final.has_parent_path()?final.parent_path():".";
    if (final.filename() != "crash.kdr") throw media_error("H3C2_FIXTURE_NAME_REQUIRED");
    std::ifstream marker(folder / ".h3c2-private-sandbox", std::ios::binary);
    std::string line;
    if (!marker || !std::getline(marker, line) || line != "H3C2-PRIVATE-TEST-ONLY")
        throw media_error("H3C2_ISOLATION_MARKER_REQUIRED");
    const auto signal = folder / (std::string(".h3c2-ready-") + point);
    std::ofstream out(signal, std::ios::binary|std::ios::trunc);
    if (!out) throw media_error("H3C2_READY_OPEN_FAILED");
    out << "H3C2_READY\\n";
    out.flush();
    out.close();
    if (!out) throw media_error("H3C2_READY_WRITE_FAILED");
    for (;;) std::this_thread::sleep_for(std::chrono::milliseconds(25));
}
'''


def instrument(original):
    # read_text() gives universal newlines under native Windows Python.
    check('H3C2 TEST-ONLY INSTRUMENTATION' not in original, 'ALREADY_INSTRUMENTED')
    replacements = [
        ('#define KYIVEMU_D14B3_DRUM_PERSISTENCE_H\n',
         '#define KYIVEMU_D14B3_DRUM_PERSISTENCE_H\n'
         '#define KYIVEMU_D14C2H3C2_TEST_COPY 1\n'),
        ('#include <vector>\n',
         '#include <vector>\n#include <thread>\n#include <cstdlib>\n'),
        ('inline void save_atomic(const logical_media& source,const std::filesystem::path& path) {',
         HOOK + '\ninline void save_atomic(const logical_media& source,const std::filesystem::path& path) {'),
        ('out.write(reinterpret_cast<const char*>(bytes.data()),\n'
         '                      static_cast<std::streamsize>(bytes.size()));',
         'const std::size_t halfway = bytes.size()/2;\n'
         '            out.write(reinterpret_cast<const char*>(bytes.data()),\n'
         '                      static_cast<std::streamsize>(halfway));\n'
         '            out.flush();\n'
         '            if (!out) throw media_error("IMAGE_WRITE_FAILED");\n'
         '            h3c2_test_hook(path,"PARTIAL_TEMP");\n'
         '            out.write(reinterpret_cast<const char*>(bytes.data()+halfway),\n'
         '                      static_cast<std::streamsize>(bytes.size()-halfway));'),
        ('            if(!out) throw media_error("IMAGE_WRITE_FAILED");\n'
         '        }\n        std::error_code error;',
         '            if(!out) throw media_error("IMAGE_WRITE_FAILED");\n'
         '        }\n        h3c2_test_hook(path,"PRE_RENAME");\n'
         '        std::error_code error;'),
        ('        if(error) throw media_error("REPLACE_FAILED");',
         '        if(error) throw media_error("REPLACE_FAILED");\n'
         '        h3c2_test_hook(path,"POST_RENAME");'),
    ]
    current = original
    for old, new in replacements:
        check(current.count(old) == 1, 'B3_ANCHOR_CHANGED: '+old[:65])
        current = current.replace(old, new, 1)
    check(current.count('h3c2_test_hook(path,') == 3, 'GATE_COUNT')
    return current


def build_test_probe(folder, cxx, timeout):
    # Include lookup is unambiguous: the private H2 header includes the private
    # B3 header by quoted relative path, not the production B3 header.
    private = folder/'private-headers'
    private.mkdir()
    b3 = ROOT/'inc/kyiv_drum_persistence.h'
    h2 = ROOT/'inc/kyiv_drum_transaction_v1.h'
    check(b3.is_file() and h2.is_file(), 'PRODUCTION_HEADER_MISSING')
    (private/b3.name).write_bytes(instrument(b3.read_text(encoding='utf-8')).encode('utf-8'))
    (private/h2.name).write_bytes(h2.read_bytes())
    probe = ROOT/'tests/isa/isa07_d14c2h3c2_termination_probe.cpp'
    check(probe.is_file(), 'PROBE_SOURCE_MISSING')
    executable = (folder/'h3c2_test_probe.exe').resolve()
    cc = call(cxx, ['-std=c++17', '-O0', '-Wall', '-Wextra', '-pedantic',
                    '-Werror', '-pthread', '-I'+str(private), '-I'+str(ROOT/'inc'),
                    str(probe), '-o', str(executable)], folder, timeout)
    check(cc.returncode == 0, 'PRIVATE_PROBE_BUILD_FAILED', cc)
    probe_self = call(executable, ['--self-test'], folder, timeout)
    check(probe_self.returncode == 0 and
          'D14C2H3C2-PROBE-SELFTEST PASS' in probe_self.stdout,
          'PROBE_SELFTEST_FAILED', probe_self)
    return executable


def terminate_at_gate(probe, image, phase, timeout):
    ready = image.parent/('.h3c2-ready-'+phase)
    check(not ready.exists(), 'STALE_READY_FILE')
    env = dict(os.environ, H3C2_TEST_PHASE=phase)
    proc = subprocess.Popen([str(probe), str(image)], cwd=image.parent,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if ready.is_file() and ready.read_bytes() == b'H3C2_READY\n':
                break
            code = proc.poll()
            if code is not None:
                out, err = proc.communicate(timeout=1)
                raise AssertionError('CHILD_EXITED_BEFORE_GATE phase='+phase+
                                     f' rc={code} stdout={out[-500:]!r} stderr={err[-500:]!r}')
            time.sleep(0.025)
        else:
            raise AssertionError('GATE_TIMEOUT: '+phase)
        check(proc.poll() is None, 'CHILD_DIED_AT_GATE: '+phase)
        proc.kill()  # external process termination; no C++ unwinding/cleanup
        out, err = proc.communicate(timeout=timeout)
        check(proc.returncode is not None and proc.returncode != 0,
              'KILL_EXIT_NOT_NONZERO: '+phase)
        check(ready.read_bytes() == b'H3C2_READY\n', 'READY_SIGNAL_CHANGED')
        return out, err
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=timeout)


def run(create, emu, cxx, timeout):
    completed = 0
    with tempfile.TemporaryDirectory(prefix='d14c2h3c2_') as tmp:
        root = Path(tmp).resolve()
        probe = build_test_probe(root, cxx, timeout)

        # Negative guard: no marker must reject before any media mutation.
        private = root/'unmarked private sandbox'
        private.mkdir()
        image = seeded(create, emu, private, timeout)
        result = call(probe, [image], private, timeout,
                      env=dict(os.environ, H3C2_TEST_PHASE='PRE_RENAME'))
        check(result.returncode != 0 and 'ISOLATION_MARKER_REQUIRED'
              in result.stderr, 'UNMARKED_NOT_REJECTED', result)
        check(image.read_bytes() == canonical(INITIAL), 'UNMARKED_MUTATED_IMAGE')
        check(sorted(x.name for x in private.iterdir()) == ['crash.kdr'],
              'UNMARKED_LEFT_SIDE_EFFECT')
        completed += 1
        print(f'D14C2H3C2-CASE {completed:02d} unmarked-probe-rejected: PASS',flush=True)

        for phase in PHASES:
            folder = root/('private folder with spaces '+phase.lower())
            folder.mkdir()
            (folder/GUARD).write_bytes(GUARD_BYTES)
            image = seeded(create, emu, folder, timeout)
            check(sorted(x.name for x in folder.iterdir()) == sorted([GUARD, image.name]),
                  'BAD_INITIAL_DIRECTORY')
            terminate_at_gate(probe, image, phase, timeout)
            temp_names = sorted(folder.glob(image.name+'.tmp.*'))
            expected = canonical(UPDATED if phase == 'POST_RENAME' else INITIAL)
            check(image.read_bytes() == expected, 'TARGET_NOT_EXPECTED: '+phase)
            if phase == 'PARTIAL_TEMP':
                check(len(temp_names) == 1 and
                      temp_names[0].read_bytes() == canonical(UPDATED)[:len(canonical(UPDATED))//2],
                      'PARTIAL_SIDECAR_UNEXPECTED')
            elif phase == 'PRE_RENAME':
                check(len(temp_names) == 1 and
                      temp_names[0].read_bytes() == canonical(UPDATED),
                      'PRE_RENAME_SIDECAR_UNEXPECTED')
            else:
                check(not temp_names, 'POST_RENAME_TEMP_RESIDUE')
            prior = [f.read_bytes() for f in temp_names]
            fresh_read(emu, image, UPDATED if phase == 'POST_RENAME' else INITIAL, timeout)
            check([f.read_bytes() for f in temp_names] == prior,
                  'FRESH_PROCESS_TOUCHED_ORPHANS')
            ready = folder/('.h3c2-ready-'+phase)
            expected_names = sorted([GUARD, image.name, ready.name] +
                                    [f.name for f in temp_names])
            check(sorted(f.name for f in folder.iterdir()) == expected_names,
                  'UNEXPECTED_RESIDUE: '+phase)
            completed += 1
            print(f'D14C2H3C2-CASE {completed:02d} external-kill-{phase.lower()}: PASS',
                  flush=True)
    check(completed == 4, 'WRONG_CASE_COUNT')
    print('D14C2H3C2-TERMINATION PASS CASES=4/4 EXTERNAL_KILL=3/3 '
          'UNMARKED_REJECTED=1 INSTRUMENTED_PRIVATE_B3=1 '
          'TARGET_OLD_OR_NEW=1 PARTIAL_SIDECAR=1 FULL_SIDECAR=1 '
          'FRESH_PRODUCTION_REOPEN=1 BYTE_EXACT_KDR=1 CRC64_ECMA=1 '
          'SIGNED_ZERO=1 ORPHAN_NOT_PROMOTED=1 CPU_MUTATION=0 '
          'CRASH_DURABILITY=OPEN CONCURRENT_WRITERS=OPEN '
          'HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')


def self_test():
    check(crc64(b'123456789') == 0x6C40DF5F0B497347, 'CRC_VECTOR')
    check(len(set((canonical(),canonical(INITIAL),canonical(UPDATED)))) == 3,
          'WRITTEN_UNWRITTEN_SIGN')
    check(struct.unpack_from('<Q', canonical(INITIAL), 48)[0] == 3,
          'WRITTEN_COUNT')
    check(len(PHASES) == 3, 'PHASE_COUNT')
    check(ins(0o25, 1, 0o100, 3) < (1 << 41), 'INSTRUCTION_WIDTH')
    check(b'H3C2_READY\n' == b'H3C2_READY\x0a', 'BINARY_MARKER')
    original = (ROOT/'inc/kyiv_drum_persistence.h').read_text(encoding='utf-8')
    instrumented = instrument(original)
    check(original != instrumented and
          '#define KYIVEMU_D14C2H3C2_TEST_COPY 1' in instrumented,
          'INSTRUMENTATION_MISSING')
    check('h3c2_test_hook(path,"POST_RENAME")' in instrumented,
          'POST_RENAME_GATE_MISSING')
    print('D14C2H3C2-SELFTEST PASS CRC64=1 SIGNED_ZERO=1 '
          'PRIVATE_HEADER=1 ANCHORS=6/6 MARKER_LF=1')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--create-exe', type=Path)
    p.add_argument('--emu-exe', type=Path)
    p.add_argument('--cxx', default='g++')
    p.add_argument('--timeout', type=float, default=20)
    a = p.parse_args()
    if a.self_test:
        self_test()
        if a.create_exe is None and a.emu_exe is None:
            return
    check(0 < a.timeout <= 120, 'TIMEOUT_INVALID')
    check(shutil.which(a.cxx) is not None, 'COMPILER_MISSING')
    check(a.create_exe is not None and a.create_exe.is_file() and
          a.emu_exe is not None and a.emu_exe.is_file(), 'NATIVE_BINARY_MISSING')
    check(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,
          text=True).strip() == BASE, 'BASELINE_MOVED')
    check(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,
          text=True).strip() == '', 'TRACKED_MUTATION')
    run(a.create_exe.resolve(), a.emu_exe.resolve(), a.cxx, a.timeout)


if __name__ == '__main__':
    main()

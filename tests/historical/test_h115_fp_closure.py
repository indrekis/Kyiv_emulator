"""H115-B24 closure: offline integrity and scope checks, not new CPU execution."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / 'examples/fp_affine_recurrence/evidence/H115_B23_FP_USER_PROGRAM_NATIVE_EVIDENCE_V1.zip'
PROV = ROOT / 'examples/fp_affine_recurrence/PROVENANCE.json'
HISTORICAL = ROOT / 'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'
FUNCTIONAL = ROOT / 'examples/fp_rom_reconstructed/inputs/FP_FUNCTIONAL_1962_RECONSTRUCTED.k41'
PROGRAM = ROOT / 'examples/fp_affine_recurrence/inputs/AFFINE_RECURRENCE.k41'
EULER = ROOT / 'examples/fp_euler_reconstructed/inputs/EULER_IMAGE.k41'
RK4 = ROOT / 'examples/fp_rom_reconstructed/reference/RK4_ORIGINAL_B16.k41'
PATCHES = ROOT / 'examples/fp_rom_reconstructed/PATCHES.json'
DOC = ROOT / 'docs/historical/H115_FP_CYCLE_CLOSURE.md'
CLI = ROOT / 'inc/kyiv_fp_cli_v2.h'

PINS = {
    HISTORICAL: 'ead80a8af8a207f619647ac1579ff934c6050a55d85a61b92a838ebd3d7662ba',
    FUNCTIONAL: 'dd9f09ed319f54c61b655c5b4aa3df1eb69e0733ee76333577194f29fa75f120',
    PROGRAM: 'da748e3e54d95b5d05c0b9161e4ef2a4fe020244ecc637f508cfa3b251ba6327',
    EULER: 'c0007fbe8bbb42084e87f768244fd8f49ccd0377b4fb966cc7204f6cac4b9165',
    RK4: '904b500e989f3280483534951386934b970c252a20de66ec8777104204f45e35',
    EVID: '93b985272f61b298448419142eb34f5c0b36033500e5392d945df2681e1e715e',
}


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_evidence() -> dict[str, bytes]:
    with zipfile.ZipFile(EVID) as z:
        assert z.testzip() is None, 'EVIDENCE_ZIP_CRC'
        names=z.namelist()
        assert len(names)==len(set(names)), 'EVIDENCE_DUPLICATE'
        for name in names:
            p=PurePosixPath(name)
            assert name and not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'EVIDENCE_UNSAFE_PATH'
            assert (z.getinfo(name).external_attr >> 16 & 0o170000) != 0o120000, 'EVIDENCE_SYMLINK'
        return {name:z.read(name) for name in names}


class H115FunctionalClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prov=json.loads(PROV.read_text(encoding='utf-8'))
        cls.archive=read_evidence()
        cls.result=json.loads(cls.archive['RESULT.json'])

    def test_sha256_all_artifacts(self):
        for p, expected in PINS.items():
            with self.subTest(path=str(p.relative_to(ROOT))):
                self.assertEqual(digest(p.read_bytes()),expected)

    def test_49_archived_member_checksums(self):
        items=self.archive['SHA256SUMS.txt'].decode('ascii').splitlines()
        self.assertEqual(len(items),49)
        self.assertEqual(set(self.archive)-{'SHA256SUMS.txt'},
                         {x.split('  ',1)[1] for x in items})
        for x in items:
            sha,path=x.split('  ',1)
            with self.subTest(member=path):
                self.assertEqual(digest(self.archive[path]),sha)

    def test_b23_natively_accepted_not_historical(self):
        self.assertEqual(self.result['status'],'PASS_H115_B23_NEW_USER_FP_PROGRAM_NATIVE_NOT_HISTORICAL')
        self.assertEqual(self.result['native']['status'],'PASS_NATIVE_USER_PROGRAM')
        self.assertTrue(self.result['not_historical'])
        self.assertFalse(self.result['production_cpu_modified'])
        self.assertFalse(self.result['functional_rom_modified'])
        self.assertFalse(self.result['historic_rom_modified'])
        self.assertEqual(self.result['native']['program_sessions'],4)
        self.assertEqual(self.result['native']['regression_sessions'],2)

    def test_four_user_program_iterates(self):
        variants=self.result['native']['variants']
        self.assertEqual([x['iterations'] for x in variants],[1,2,3,4])
        self.assertEqual([x['steps'] for x in variants],[149,309,464,623])
        self.assertEqual([x['dispatches'] for x in variants],[6,12,18,24])
        self.assertEqual([x['x_word'] for x in variants],
                         ['14000000000077','16000000000077','17000000000077','17400000000077'])
        self.assertEqual(self.result['native']['negative_cases'],6)
        self.assertEqual(self.result['native']['legacy_image_smoke'],'PASS')

    def test_native_trace_evidence_matches_source(self):
        self.assertEqual(digest(self.archive['PROGRAM.k41']), PINS[PROGRAM])
        self.assertEqual(self.result['baseline']['new_program_sha256'],PINS[PROGRAM])
        self.assertEqual(self.result['baseline']['functional_rom_sha256'],PINS[FUNCTIONAL])
        for n in range(1,5):
            self.assertEqual(self.archive[f'ITER_{n}_NATIVE_EXIT.txt'].strip(),b'0')
        for key in ('REGRESSION_EULER_EXIT.txt','REGRESSION_RK4_EXIT.txt','CXX_BUILD_EXIT.txt'):
            self.assertEqual(self.archive[key].strip(),b'0')

    def test_updated_provenance_tracks_evidence(self):
        self.assertEqual(self.prov['native_status'],self.result['status'])
        self.assertEqual(self.prov['native_evidence_sha256'],PINS[EVID])
        self.assertEqual(self.prov['native_evidence_sessions'],6)
        self.assertEqual(ROOT/self.prov['native_evidence_path'],EVID)
        self.assertEqual(self.prov['baseline_short_head'],'d39d212')
        self.assertEqual(self.prov['acceptance_head_short'],'da90bab')
        self.assertEqual(self.prov['historical_authenticity'],'NOT_CLAIMED')

    def test_original_is_not_reconstructed_rom(self):
        def addresses(p):
            return {int(line.split()[0],8) for line in p.read_text('ascii').splitlines()[1:] if line.strip()}
        old,new=addresses(HISTORICAL),addresses(FUNCTIONAL)
        self.assertEqual(len(old),251)
        self.assertEqual(len(new),257)
        self.assertNotIn(0o3574,new)
        patch=json.loads(PATCHES.read_text(encoding='utf-8'))['patches']
        self.assertEqual(len(patch),12)
        self.assertEqual(sum(x['original_word_octal'] is None for x in patch),6)
        self.assertEqual(sum(x['original_word_octal'] is not None for x in patch),6)

    def test_generic_cli_has_no_example_allowlist(self):
        s=CLI.read_text(encoding='utf-8')
        for forbidden in ('qualified_program(', 'euler_digest','FP_UNQUALIFIED_PROGRAM',
                          'FP_UNKNOWN_READ_', 'FP_IO_FORBIDDEN'):
            self.assertNotIn(forbidden,s)
        self.assertIn('cpu.emergency_stop_blocked=true',s)

    def test_scope_and_historical_questions_remain_open(self):
        s=DOC.read_text(encoding='utf-8')
        for x in ('3574', '3367', 'не', 'H115-B19', 'H115-B23', 'ROADMAP.md'):
            self.assertIn(x,s)
        self.assertIn('NOT_CLAIMED',str(self.prov))

if __name__=='__main__':
    unittest.main()

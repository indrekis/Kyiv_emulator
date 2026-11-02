"""H115-A source-materialization regression; no CPU, hardware, or FP numerical claims."""
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'tools/historical/h115_a.py'
PKG=ROOT.parent if ROOT.name=='repo_files' else ROOT/'tempkyiv/kyiv_h115_a_v1'
INPUTS=PKG/'inputs'
SPEC=importlib.util.spec_from_file_location('h115_a',SCRIPT)
h=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(h)

class SourceMaterialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=INPUTS/'KYIV_H66_FP_ROM_251_TRANSCRIPTION_V1.zip'
        cls.evidence=INPUTS/'H66_FP_ROM_251_WORDS_EVIDENCE_V1.zip'
        cls.k41=(ROOT/'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41').read_bytes()
        cls.tsv=(ROOT/'examples/historical/gy1962/rom_modules/fp_simulation_251_provenance.tsv').read_bytes()
        cls.report={'k41_records':251,'h65_anchors':13,'ocr_normalizations':45,
                    'unprinted_addresses':69,'cpu_execution':'NOT_ATTEMPTED'}

    def test_h66_pin_and_counts(self):
        self.assertEqual(h.sha(self.tsv),h.H66_TSV_SHA)
        self.assertEqual(h.sha(self.k41),h.H115_K41_SHA)
        self.assertEqual(self.report['k41_records'],251)
        self.assertEqual(self.report['h65_anchors'],13)
        self.assertEqual(self.report['ocr_normalizations'],45)
        self.assertEqual(self.report['unprinted_addresses'],69)
        self.assertEqual(self.report['cpu_execution'],'NOT_ATTEMPTED')

    def test_h114_format_and_exact_41bit_roundtrip(self):
        rows=list(csv.DictReader(io.StringIO(self.tsv.decode()),delimiter='\t'))
        pairs=[line.split() for line in self.k41.decode().splitlines()[1:]]
        self.assertEqual(self.k41.splitlines()[0],b'KYIV41-OCT1')
        self.assertEqual(len(pairs),251)
        self.assertEqual(len({a for a,_ in pairs}),251)
        self.assertEqual([a for a,_ in pairs],[r['address'] for r in rows])
        for (a,packed),row in zip(pairs,rows):
            self.assertEqual(len(a),4)
            self.assertEqual(len(packed),14)
            self.assertLess(int(packed,8),1<<41)
            self.assertEqual(packed,''.join(row[field] for field in ('opcode','a1','a2','a3')))
            decoded=f'{int(packed,8):014o}'
            self.assertEqual((decoded[:2],decoded[2:6],decoded[6:10],decoded[10:14]),
                             (row['opcode'],row['a1'],row['a2'],row['a3']))

    def test_known_gaps_unfilled_and_unknown_3574(self):
        addresses={int(line.split()[0],8) for line in self.k41.decode().splitlines()[1:]}
        self.assertEqual(addresses,h.slots()-h.holes())
        self.assertNotIn(0o3574,addresses)
        self.assertEqual(len(h.holes()),69)

    def test_transcription_tamper_rejected(self):
        edited=self.tsv.replace(b'3300\t01 0000 3621 0026',b'3300\t01 0000 3621 0027',1)
        self.assertNotEqual(edited,self.tsv)
        with self.assertRaises(h.GateError):
            h.verify_h66_data(edited,b'',b'',b'')

    @unittest.skipUnless((INPUTS/'H66_FP_ROM_251_WORDS_EVIDENCE_V1.zip').is_file(),
                         'H66 archive-only negative tests')
    def test_word_overflow_and_duplicate_address_rejected(self):
        with h.zipfile.ZipFile(self.evidence) as z:
            c=z.read('H65_PRINTED_ADDRESS_COVERAGE.tsv')
            a=z.read('H65_SOURCE_ANCHORS.tsv')
            n=z.read('OCR_NORMALIZATIONS.tsv')
        bad=self.tsv.replace(b'3301\t01 0000 3622 0027',b'3300\t01 0000 3622 0027',1)
        with self.assertRaises(h.GateError):h.parse_source(bad,c,a,n,pin_corpus=False)
        bad=self.tsv.replace(b'3301\t01 0000 3622 0027',b'3301\t40 0000 3622 0027',1)
        with self.assertRaises(h.GateError):h.parse_source(bad,c,a,n,pin_corpus=False)

    @unittest.skipUnless((INPUTS/'KYIV_H66_FP_ROM_251_TRANSCRIPTION_V1.zip').is_file() and
                         (INPUTS/'H66_FP_ROM_251_WORDS_EVIDENCE_V1.zip').is_file(),
                         'Original H66 archives not present; pinned K41/TSV still tested')
    def test_archive_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'tampered.zip'
            fake.write_bytes(self.evidence.read_bytes()+b'X')
            with self.assertRaises(h.GateError):h.build(self.source,fake)

    @unittest.skipUnless((INPUTS/'KYIV_H66_FP_ROM_251_TRANSCRIPTION_V1.zip').is_file() and
                         (INPUTS/'H66_FP_ROM_251_WORDS_EVIDENCE_V1.zip').is_file(),
                         'Original H66 archives not present; pinned K41/TSV still tested')
    def test_archives_reproduce_exact_k41(self):
        raw,tsv,report=h.build(self.source,self.evidence)
        self.assertEqual(raw,self.k41)
        self.assertEqual(tsv,self.tsv)
        self.assertEqual(report['k41_sha256'],h.H115_K41_SHA)

    def test_tracked_artifacts_identical_to_pinned_generation(self):
        candidates=[ROOT/'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41',
                    ROOT/'examples/historical/gy1962/rom_modules/fp_simulation_251_provenance.tsv']
        self.assertEqual(candidates[0].read_bytes(),self.k41)
        self.assertEqual(candidates[1].read_bytes(),self.tsv)

if __name__=='__main__':unittest.main(verbosity=2)

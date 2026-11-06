"""H116-C1a: isolated generic ROM-catalog contracts, no production CPU execution."""
from __future__ import annotations
import importlib.util
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[2]/'tools'/'historical'/'rom_catalog_v1.py'
spec=importlib.util.spec_from_file_location('h116_catalog',SOURCE)
catalog=importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

def write_json(p, x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x)+'\n',encoding='utf-8')

class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cat=self.root/'examples'/'rom_catalog'
        self.cat.joinpath('modules').mkdir(parents=True)
        self.cat.joinpath('sets').mkdir(parents=True)
        self.fixed=self.root/'mem'/'ROM.txt'
        self.fixed.parent.mkdir()
        self.fixed.write_bytes(b'fake pinned fixed ROM for isolated tests\n')
        self.pinned=catalog.sha256(self.fixed.read_bytes())
        self.patcher=patch.object(catalog,'FIXED_ROM_SHA',self.pinned)
        self.patcher.start();self.addCleanup(self.patcher.stop)
        self.add_module('alpha', '3300', '3301')
        self.add_set('first',['alpha'])

    def add_module(self,mid,slot='3300',addr='3301'):
        word='01000000000001'
        p=self.root/'examples'/'new'/(mid+'.k41')
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(f'KYIV41-OCT1\n{addr} {word}\n'.encode('ascii'))
        first=int(slot,8)
        s={'schema':catalog.SCHEMA_MODULE,'id':mid,'description':'test '+mid,
         'image':'examples/new/'+mid+'.k41','sha256':catalog.sha256(p.read_bytes()),
         'slots':[[f'{first:04o}',f'{first+0o77:04o}']],'records':1,
         'provenance':'SYNTHETIC_TEST','critical_unknown':[]}
        write_json(self.cat/'modules'/(mid+'.json'),s)
        return p

    def add_set(self,sid,modules):
        s={'schema':catalog.SCHEMA_SET,'id':sid,'description':'synthetic test only',
           'modules':modules,'fixed_rom_sha256':self.pinned}
        write_json(self.cat/'sets'/(sid+'.json'),s)

    def assert_hold(self, token, sid='first'):
        with self.assertRaises(catalog.CatalogError) as e:
            catalog.validate_set(self.root,sid)
        self.assertIn(token,str(e.exception))

    def test_single_module_partial_slot_is_explicit(self):
        result, words=catalog.validate_set(self.root,'first')
        self.assertEqual(result['words'],1)
        self.assertEqual(result['unknown_slots_words'],63)
        self.assertFalse(result['implicit_fill'])
        self.assertEqual(words[0o3301],'01000000000001')

    def test_new_module_added_by_files_only(self):
        self.add_module('beta','3400','3402')
        self.add_set('combined',['alpha','beta'])
        result,words=catalog.validate_set(self.root,'combined')
        self.assertEqual(result['occupied_slots'],2)
        self.assertEqual(result['words'],2)
        self.assertIn(0o3402,words)

    def test_overlap_is_rejected_even_for_disjoint_words(self):
        self.add_module('beta','3300','3302')
        self.add_set('combined',['alpha','beta'])
        self.assert_hold('ROM_SLOT_COLLISION','combined')

    def test_duplicate_module_reference(self):
        self.add_set('duplicate',['alpha','alpha'])
        self.assert_hold('INVALID_MODULE_SELECTION','duplicate')

    def test_sha_mismatch_is_fail_closed(self):
        p=self.root/'examples'/'new'/'alpha.k41'
        p.write_bytes(p.read_bytes().replace(b'000001',b'000002'))
        self.assert_hold('IMAGE_SHA256_MISMATCH')

    def test_fixed_sha_mismatch(self):
        self.fixed.write_text('changed')
        self.assert_hold('FIXED_ROM_SOURCE_SHA_MISMATCH')

    def test_missing_critical_unknown_cannot_be_filled(self):
        p=self.cat/'modules'/'alpha.json';d=json.loads(p.read_text());d['critical_unknown']=['3301'];write_json(p,d)
        self.assert_hold('CRITICAL_UNKNOWN_MATERIALIZED')

    def test_known_unknown_accepted(self):
        p=self.cat/'modules'/'alpha.json';d=json.loads(p.read_text());d['critical_unknown']=['3300'];write_json(p,d)
        r,_=catalog.validate_set(self.root,'first')
        self.assertEqual(r['modules'][0]['critical_unknown'],['3300'])

    def test_overwide_41_rejected(self):
        p=self.root/'examples'/'new'/'alpha.k41';p.write_text('KYIV41-OCT1\n3301 77777777777777\n')
        m=self.cat/'modules'/'alpha.json';d=json.loads(m.read_text());d['sha256']=catalog.sha256(p.read_bytes());write_json(m,d)
        self.assert_hold('OVERWIDE_WORD')

    def test_duplicate_address_rejected(self):
        p=self.root/'examples'/'new'/'alpha.k41';p.write_text('KYIV41-OCT1\n3301 01000000000001\n3301 01000000000001\n')
        m=self.cat/'modules'/'alpha.json';d=json.loads(m.read_text());d['sha256']=catalog.sha256(p.read_bytes());d['records']=2;write_json(m,d)
        self.assert_hold('DUPLICATE_WORD_ADDRESS')

    def test_unaligned_slot(self):
        p=self.cat/'modules'/'alpha.json';d=json.loads(p.read_text());d['slots']=[['3301','3377']];write_json(p,d)
        self.assert_hold('UNALIGNED_ROM_SLOT')

    def test_path_traversal_rejected(self):
        p=self.cat/'modules'/'alpha.json';d=json.loads(p.read_text());d['image']='examples/../../secret.k41';write_json(p,d)
        self.assert_hold('UNSAFE_PATH')

    def test_symlink_input_rejected(self):
        p=self.root/'examples'/'new'/'alpha.k41';source=self.root/'outside.k41'
        source.write_bytes(p.read_bytes());p.unlink()
        try: p.symlink_to(source)
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
        self.assert_hold('SYMLINK_NOT_ALLOWED')

    def test_manifest_duplicate_key_rejected(self):
        p=self.cat/'sets'/'first.json'
        p.write_text('{"schema":"x","schema":"x"}',encoding='utf-8')
        self.assert_hold('DUPLICATE_JSON_KEY')

    def test_existing_output_rejected(self):
        out=self.root/'tempkyiv'/'first_prepared';out.mkdir(parents=True)
        with self.assertRaisesRegex(catalog.CatalogError,'OUT_ALREADY_EXISTS'):
            catalog.prepare(self.root,'first',out)

    def test_output_outside_tempkyiv_rejected(self):
        with self.assertRaisesRegex(catalog.CatalogError,'OUT_OUTSIDE_TEMPKYIV'):
            catalog.prepare(self.root,'first',self.root/'elsewhere')

    def test_prepare_contains_only_known_words(self):
        dest=self.root/'tempkyiv'/'candidate'
        r=catalog.prepare(self.root,'first',dest)
        self.assertEqual(r['words'],1)
        self.assertEqual((dest/'replaceable.k41').read_text(),'KYIV41-OCT1\n3301 01000000000001\n')
        self.assertEqual(len((dest/'SHA256SUMS.txt').read_text().splitlines()),2)

    def test_id_validation(self):
        with self.assertRaisesRegex(catalog.CatalogError,'INVALID_SET_ID'):
            catalog.validate_set(self.root,'../alpha')

    def test_all_ids_is_file_based(self):
        self.add_module('gamma','3500','3501')
        listing=dict(catalog.all_ids(self.cat))
        self.assertEqual(listing['modules'],['alpha','gamma'])

if __name__=='__main__':unittest.main()

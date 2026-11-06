"""H116-C2b schema/oracle regression, not a replacement for Windows native gate."""
from pathlib import Path
import importlib.util
import sys
import unittest
import tempfile

THIS=Path(__file__).resolve()
STAGED=THIS.parents[2]
RUNNER=STAGED/'tools/historical/operator_scenarios_v1.py'
PATCH=THIS.parents[3]/'backend_patch.py' if (THIS.parents[3]/'backend_patch.py').exists() else None
spec=importlib.util.spec_from_file_location('h116_operator_scenarios',RUNNER)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class OperatorContract(unittest.TestCase):
    def test_octal(self):
        self.assertTrue(m.valid_addr('3001'))
        self.assertFalse(m.valid_addr('3008'))
        self.assertFalse(m.valid_addr('../a'))
    def test_41_bit(self):
        self.assertTrue(m.valid_word('00000000000000'))
        self.assertFalse(m.valid_word('77777777777777'))
        self.assertFalse(m.valid_word('100000000000000'))
    def test_keys(self):
        with self.assertRaisesRegex(m.Hold,'SCHEMA_FIELDS'):
            m.require_keys({'a':1,'b':2},('a',),'CASE')
    def test_state_ok(self):
        m.check_state({'C':'0144','STEPS':1,'T':'0','K':'33000000000000'})
    def test_state_rejects_unknown(self):
        with self.assertRaisesRegex(m.Hold,'STATE_ORACLE_KEYS'):
            m.check_state({'NO_SUCH_REG':'0000'})
    def test_state_rejects_overwide(self):
        with self.assertRaisesRegex(m.Hold,'STATE_ORACLE_K'):
            m.check_state({'K':'77777777777777'})
    def test_state_rejects_bad_step(self):
        with self.assertRaisesRegex(m.Hold,'STATE_ORACLE_STEPS'):
            m.check_state({'STEPS':True})
    def test_nk_command(self):
        self.assertEqual(m.command_for({'op':'set_nk','address':'3000','word':'00000000000001'}),
                         'SETNK\t3000\t00000000000001')
    def test_step_command(self):
        self.assertEqual(m.command_for({'op':'step','count':32}),'STEP\t32')
    def test_response(self):
        self.assertEqual(m.fields_for('OK\tSTATE\tC=0144\tSTEPS=1','STATE')['C'],'0144')
    def test_response_error(self):
        with self.assertRaisesRegex(m.Hold,'BACKEND_PROTOCOL'):
            m.fields_for('ERR\tBAD','STATE')
    def test_response_duplicate(self):
        with self.assertRaisesRegex(m.Hold,'BACKEND_DUPLICATE_FIELD'):
            m.fields_for('OK\tSTATE\tC=0144\tC=0143','STATE')
    def test_step_oracle(self):
        a={'op':'step','origin':'HOST_TEST','expect':{'executed':1,'path':['0143'],'state':{'C':'0144','STEPS':1}}}
        m.evaluate_action(a,'OK\tSTEP\tEXECUTED=1\tPATH=0143\tC=0144\tSTEPS=1')
    def test_step_wrong_path(self):
        a={'op':'step','origin':'HOST_TEST','expect':{'executed':1,'path':['0143'],'state':{'STEPS':1}}}
        with self.assertRaisesRegex(m.Hold,'STEP_PATH_OR_COUNT_MISMATCH'):
            m.evaluate_action(a,'OK\tSTEP\tEXECUTED=1\tPATH=0144\tSTEPS=1')
    def test_dump_oracle(self):
        a={'op':'dump','origin':'HOST_TEST','address':'3000','count':1,'expect':['00000000000001']}
        m.evaluate_action(a,'OK\tDUMP\tSTART=3000\tCOUNT=1\tDATA=00000000000001')
    def test_dump_wrong_value(self):
        a={'op':'dump','origin':'HOST_TEST','address':'3000','count':1,'expect':['00000000000001']}
        with self.assertRaisesRegex(m.Hold,'DUMP_VALUE_MISMATCH'):
            m.evaluate_action(a,'OK\tDUMP\tSTART=3000\tCOUNT=1\tDATA=00000000000000')
    def test_nk_reply(self):
        a={'op':'set_nk','origin':'HOST_TEST','address':'3000','word':'00000000000001'}
        m.evaluate_action(a,'OK\tSETNK\tADDR=3000\tWORD=00000000000001')
    def _read_ram_fixture(self, raw):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'program.k41'
            path.write_bytes(raw)
            return m.parse_ram_program(path,hashlib.sha256(raw).hexdigest())
    def test_ram_source_comment_lines(self):
        rows=self._read_ram_fixture(b'KYIV41-OCT1\n# historical source comment\n\n0143 01302600100347\n')
        self.assertEqual(rows,{0o143:'01302600100347'})
    def test_ram_inline_comments(self):
        rows=self._read_ram_fixture(b'# prefatory source note\nKYIV41-OCT1\n0143 01302600100347 # command\n')
        self.assertEqual(rows,{0o143:'01302600100347'})
    def test_ram_duplicate_address_still_rejected(self):
        with self.assertRaisesRegex(m.Hold,'PROGRAM_DUPLICATE_ADDRESS'):
            self._read_ram_fixture(b'KYIV41-OCT1\n0143 01302600100347\n0143 01302600100347\n')
    def test_ram_bad_record_still_rejected(self):
        with self.assertRaisesRegex(m.Hold,'PROGRAM_RECORD_INVALID'):
            self._read_ram_fixture(b'KYIV41-OCT1\n0143 NOT_OCTAL\n')
    def test_ram_overwide_still_rejected(self):
        with self.assertRaisesRegex(m.Hold,'PROGRAM_RECORD_INVALID'):
            self._read_ram_fixture(b'KYIV41-OCT1\n0143 77777777777777\n')
    def test_ram_rom_address_still_rejected(self):
        with self.assertRaisesRegex(m.Hold,'PROGRAM_RAM_ONLY'):
            self._read_ram_fixture(b'KYIV41-OCT1\n3300 01302600100347\n')

    def test_backend_patch_failclosed(self):
        if PATCH is None:self.skipTest('backend patch not present in independent installed tests')
        spec=importlib.util.spec_from_file_location('h116_operator_backend_patch',PATCH)
        p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
        with self.assertRaisesRegex(ValueError,'BACKEND_PATCH_ANCHOR_COUNT'):
            p.patch(b'#include "foo.h"\n')

if __name__=='__main__':unittest.main()

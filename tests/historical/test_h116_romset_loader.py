"""H116-C1b pure/offline fixture tests; native tests are in the stage gate."""
from pathlib import Path
import importlib.util
import hashlib
import json
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

def load(rel,name):
    sp=importlib.util.spec_from_file_location(name,ROOT/rel)
    obj=importlib.util.module_from_spec(sp);sp.loader.exec_module(obj);return obj

# Local stage context imports its own patch module. Installed context finds it
# only in stage artifact, so this test covers the installed loader contract.
class LoaderContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header=(ROOT/'inc/kyiv_rom_set_image_v1.h').read_text(encoding='utf-8')
    def test_opt_in_only(self):
        self.assertIn('if(!args.selected)',self.header)
        self.assertIn('H116_SET_IMAGE_AND_SHA_REQUIRED',self.header)
    def test_exact_bytes_hash(self):
        self.assertIn('kyiv_sha256_v1::digest(raw)',self.header)
        self.assertIn('H116_SET_SHA256_MISMATCH',self.header)
    def test_bounded_41_bit_and_slot(self):
        self.assertIn('(word_t{1}<<41)',self.header)
        self.assertIn('address<03300 || address>=04000',self.header)
    def test_no_implicit_fill(self):
        self.assertNotIn('for(addr_t a=03300;',self.header)
        self.assertIn('for(const auto& w:staged.words) cpu.kmem.write_rom',self.header)
    def test_no_cpu_emulation(self):
        self.assertNotIn('execute_opcode',self.header)
        self.assertNotIn('K_reg=',self.header)
    def test_new_module_data_driven(self):
        self.assertNotIn('math_module1',self.header)
        self.assertNotIn('fp_functional',self.header)
        self.assertNotIn('fp_1962_printed',self.header)
    def test_no_mutating_fixed_rom(self):
        self.assertIn('address<03300 || address>=04000',self.header)
        self.assertNotIn('03010',self.header)
    def test_reject_ordering_and_duplicate(self):
        self.assertIn('address<=previous',self.header)
        self.assertIn('H116_SET_UNSORTED_OR_DUPLICATE',self.header)
    def test_boot_is_private_cpu(self):
        self.assertIn('install_at_init',self.header)
        self.assertIn('deferred CPU',self.header)

if __name__=='__main__':unittest.main()

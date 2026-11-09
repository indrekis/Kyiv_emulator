"""H117 source/reconstruction boundary regression; never substitute historic code."""
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'tools/historical/au_0360_reconstruction_v1.py'
spec=importlib.util.spec_from_file_location('au0360',SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class AU0360Static(unittest.TestCase):
    def test_all_source_words(self):
        words,manifest=mod.source_images(ROOT)
        self.assertEqual(len(words),220)
        self.assertEqual(manifest['canonical_image_count'],20)
        self.assertEqual(words[0o334],mod.SOURCE_0334)
        self.assertNotIn(0o360,words)
        self.assertNotIn(0o42,words)
    def test_source_only_0042(self):
        words,_=mod.source_images(ROOT)
        self.assertEqual(mod.SOURCE_0042,'01306600000353')
        self.assertNotIn(0o42,words)
    def test_synthetic_marker(self):
        p=ROOT/'examples/historical/gy1962/reconstructions/au1_0360_functional_v1.k41'
        text=p.read_text(encoding='utf-8')
        self.assertIn('SYNTHETIC',text)
        self.assertIn('NOT SOURCE_PRINTED',text)
        self.assertEqual(mod.parse_image(p),{0o360:'05000000000042'})

if __name__=='__main__':unittest.main()

"""H118-P2B: provenance, rejection, exact two-epoch action trace."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
import hashlib

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tools/historical/au_h117_two_epoch_c2b_v1.py'

def load():
    spec=importlib.util.spec_from_file_location('h118_p2b_generator',SOURCE)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj

def mock(directory):
    m=load()
    first=[];current='0042'
    for i in range(97):
        after=('0360' if i==96 else ('0043' if current=='0042' else '0042'))
        first.append({'before':current,'after':after,'A':'0000','P':'0000','T':'0'})
        current=after
    jump=[{'before':'0360','after':'0042','A':'0000','P':'0000','T':'0'}]
    second=[{'before':'0042','after':'0043','A':'0000','P':'0000','T':'0'},
            {'before':'0043','after':'0044','A':'0000','P':'0000','T':'0'},
            {'before':'0044','after':'0360','A':'0000','P':'0000','T':'0'}]
    entries={'0042':'01306600000353','0334':'05000000000360','0360':'05000000000042'}
    addr=1
    while len(entries)<222:
        key=f'{addr:04o}';addr+=1
        if key not in entries:entries[key]='00000000000000'
    program=('KYIV41-OCT1\n'+''.join(f'{a} {v}\n' for a,v in sorted(entries.items()))).encode('ascii')
    (directory/'au_functional_private.k41').write_bytes(program)
    witness={'patched':{'composite_sha256':m.sha(program),'reconstructed_0360':m.RECONSTRUCTION,
                      'canonical_image_count':20,'source_word_count':220}}
    (directory/'INPUT_MANIFEST.json').write_text(json.dumps(witness))
    report={'decision':m.H117_STATUS,'first_epoch_source_boundary':True,'first_epoch_invariant':True,
            'reconstructed_jump':True,'second_epoch_reaches_boundary':True,'second_epoch_steps':3,
            'sessions':[]}
    for name in ('CONTROL','RECONSTRUCTED'):
        item={'session':name,'first':{'result':'BOUNDARY_0360','steps':97}}
        for addr in ('0347','0353','0357'):item['before_0360_ram_'+addr]='00000000000000'
        if name=='RECONSTRUCTED':
            item['second']={'result':'BOUNDARY_0360','steps':3}
            item['jump']={'path':'0360','pc':'0042','T':'0'}
        report['sessions'].append(item)
    (directory/'RESULT.json').write_text(json.dumps(report))
    traces=[]
    for phase,rows in [('CONTROL_FIRST',first),('RECONSTRUCTED_FIRST',first),
                       ('RECONSTRUCTED_JUMP',jump),('RECONSTRUCTED_SECOND',second)]:
        for j,e in enumerate(rows,1):traces.append([phase,str(j),e['before'],e['after'],e['T'],e['A'],e['P']])
    text='epoch\tindex\tbefore\tafter\tT\tA\tP\n'+''.join('\t'.join(x)+'\n' for x in traces)
    (directory/'TRACE.tsv').write_text(text,encoding='utf8')
    return report

class Tests(unittest.TestCase):
    def test_source_id_and_distinct_origins(self):
        m=load()
        self.assertEqual(m.IDENT,'au_h117_two_epochs')
        self.assertEqual(m.RECONSTRUCTION,'05000000000042')
        self.assertEqual(m.ORIGIN,'RECONSTRUCTED_ASSUMPTION')
        self.assertEqual(m.FIRST,97)

    def test_generate_witness_action_plan(self):
        m=load()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);mock(p)
            blobs,info=m.generate(p)
            spec=json.loads(blobs[m.SCENARIO])
            self.assertEqual(spec['max_steps'],101)
            self.assertEqual(info['second_steps'],3)
            self.assertEqual(spec['entry'],'0042')
            self.assertEqual(spec['program']['sha256'],hashlib.sha256(blobs[m.PROGRAM]).hexdigest())
            steps=[a for a in spec['actions'] if a['op']=='step']
            self.assertEqual([a['count'] for a in steps],[32,32,32,1,1,3])
            self.assertEqual(steps[3]['expect']['state']['C'],'0360')
            self.assertEqual(steps[4]['expect']['path'],['0360'])
            self.assertEqual(steps[5]['expect']['state']['C'],'0360')

    def test_reject_false_reference_pass(self):
        m=load()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);mock(p)
            f=p/'RESULT.json';d=json.loads(f.read_text());d['first_epoch_invariant']=False;f.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'H117_REFERENCE_HOLD'):m.generate(p)

    def test_reject_tampered_reconstructed_word(self):
        m=load()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);mock(p)
            f=p/'au_functional_private.k41';f.write_bytes(f.read_bytes().replace(b'0360 05000000000042',b'0360 05000000000043'))
            with self.assertRaisesRegex(ValueError,'H117_SOURCE_VS_RECONSTRUCTION'):m.generate(p)

    def test_reject_trace_discontinuity(self):
        m=load()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);mock(p)
            f=p/'TRACE.tsv';s=f.read_text();f.write_text(s.replace('RECONSTRUCTED_SECOND\t2\t0043\t0044','RECONSTRUCTED_SECOND\t2\t0042\t0044'))
            with self.assertRaisesRegex(ValueError,'TRACE_DISCONTINUITY'):m.generate(p)

    def test_reject_unverified_first_boundary_dumps(self):
        m=load()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);mock(p)
            f=p/'RESULT.json';d=json.loads(f.read_text());d['sessions'][0]['before_0360_ram_0347']='00000000000001';f.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'CONTROL_DUMP_DIFFERENT'):m.generate(p)

if __name__=='__main__':unittest.main()

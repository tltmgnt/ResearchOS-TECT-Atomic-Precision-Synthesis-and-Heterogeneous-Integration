import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from researchos_hi.core import ValidationError, analyze, dumps, read_json, run, sha, validate, verify_bundle, verify_evidence

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/synthetic-stack.json'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.record = read_json(EXAMPLE)

    def test_geometry_and_missing_data(self):
        result = analyze(self.record)
        self.assertEqual(result['total_thickness_nm'], 10)
        self.assertEqual([r['depth_nm'] for r in result['interfaces']], [0, 4])
        self.assertAlmostEqual(result['interfaces'][0]['nominal_mismatch_percent'], 2)
        self.assertAlmostEqual(result['interfaces'][1]['nominal_mismatch_percent'], 100*(5.2/5.1-1))
        self.assertEqual([c['status'] for c in result['target_checks']], ['met', 'no-data'])
        self.assertEqual(result['target_checks'][0]['basis'], 'synthetic')

    def test_unmet_and_greater_than_target(self):
        self.record['measurements'][0]['value'] = .6
        self.assertEqual(analyze(self.record)['target_checks'][0]['status'], 'unmet')
        self.record['targets'][0]['operator'] = '>='
        self.assertEqual(analyze(self.record)['target_checks'][0]['status'], 'met')

    def test_bad_records(self):
        mutations = [lambda r:r.update(schema_version=True), lambda r:r.update(id='../escape'),
                     lambda r:r.update(data_kind='experimental'), lambda r:r.update(layers=[]),
                     lambda r:r['layers'][0].update(thickness_nm=0),
                     lambda r:r['layers'][0].update(lattice_constant_A=float('inf')),
                     lambda r:r['layers'][0].update(thickness_nm=True),
                     lambda r:r['layers'].append(copy.deepcopy(r['layers'][0])),
                     lambda r:r['measurements'][0].update(uncertainty=-1),
                     lambda r:r['measurements'][0].update(evidence_ids=['missing']),
                     lambda r:r['targets'][0].update(layer_id='missing')]
        for mutate in mutations:
            record = copy.deepcopy(self.record)
            mutate(record)
            with self.subTest(record=record), self.assertRaises(ValidationError):
                validate(record)

    def test_json_rejects_ambiguous_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'bad.json'
            for data in ('{"id":1,"id":2}', '{"x":NaN}'):
                p.write_text(data)
                with self.assertRaises(ValidationError):
                    read_json(p)

    def test_experimental_evidence_and_bundle_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = b'fixture-only, not real experimental evidence\n'
            (root/'raw.csv').write_bytes(data)
            self.record['data_kind'] = 'experimental'
            self.record['evidence'] = [{'id':'raw', 'path':'raw.csv', 'sha256':sha(data), 'description':'Test fixture only'}]
            self.record['measurements'][0]['evidence_ids'] = ['raw']
            p = root/'record.json'
            p.write_text(dumps(self.record))
            run(p, root/'run')
            verify_bundle(root/'run')
            # Bundle carries the original bytes and survives removal of source evidence.
            (root/'raw.csv').unlink()
            verify_bundle(root/'run')
            (root/'run/evidence/0000.bin').write_bytes(b'tampered')
            with self.assertRaises(ValidationError):
                verify_bundle(root/'run')

    def test_evidence_mismatch_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'raw.csv').write_bytes(b'actual')
            self.record['evidence'] = [{'id':'e', 'path':'raw.csv', 'sha256':sha(b'expected'), 'description':'Fixture'}]
            with self.assertRaises(ValidationError):
                verify_evidence(validate(self.record), root)
            for path in ('../outside', '/etc/passwd', 'C:\\outside'):
                self.record['evidence'][0]['path'] = path
                with self.assertRaises(ValidationError):
                    validate(self.record)
            (root/'link').symlink_to(root.parent)
            self.record['evidence'][0]['path'] = 'link/outside'
            with self.assertRaises(ValidationError):
                verify_evidence(validate(self.record), root)

    def test_reproduction_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b = Path(tmp)/'a',Path(tmp)/'b'
            run(EXAMPLE,a)
            run(EXAMPLE,b)
            self.assertEqual({p.relative_to(a):p.read_bytes() for p in a.rglob('*') if p.is_file()},
                             {p.relative_to(b):p.read_bytes() for p in b.rglob('*') if p.is_file()})
            verify_bundle(a)
            with self.assertRaises(ValidationError):
                run(EXAMPLE,a)
            # Rehashing modified numerical results is insufficient to pass verification.
            result = read_json(a/'results.json')
            result['total_thickness_nm'] = 999
            (a/'results.json').write_text(dumps(result))
            manifest = read_json(a/'manifest.json')
            manifest['files']['results.json'] = sha((a/'results.json').read_bytes())
            (a/'manifest.json').write_text(dumps(manifest))
            with self.assertRaises(ValidationError):
                verify_bundle(a)

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = str(Path(tmp)/'run')
            for args in (['validate',str(EXAMPLE)], ['run',str(EXAMPLE),'--output',output], ['verify',output], ['report',output]):
                result = subprocess.run([sys.executable,'-m','researchos_hi',*args],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            bad = subprocess.run([sys.executable,'-m','researchos_hi','validate',str(Path(tmp)/'missing')],capture_output=True,text=True)
            self.assertEqual(bad.returncode,1)
            self.assertIn('error:',bad.stderr)


if __name__ == '__main__':
    unittest.main()

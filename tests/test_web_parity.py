"""Ensure the browser arithmetic stays aligned with the Python runner."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from researchos_hi.core import analyze, read_json

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node is needed for web parity verification')
class WebParityTests(unittest.TestCase):
    def test_complete_example_result_matches_python(self):
        script = "import fs from 'node:fs';import{analyze}from './web/model.mjs';console.log(JSON.stringify(analyze(JSON.parse(fs.readFileSync('examples/synthetic-stack.json','utf8')))))"
        result = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], cwd=ROOT, text=True))
        expected = analyze(read_json(ROOT / 'examples/synthetic-stack.json'))
        self.assertEqual(result.keys(), expected.keys())
        for key in expected:
            if key != 'interfaces':
                self.assertEqual(result[key], expected[key])
        self.assertEqual(len(result['interfaces']), len(expected['interfaces']))
        for actual, target in zip(result['interfaces'], expected['interfaces']):
            self.assertEqual(actual.keys(), target.keys())
            for key, value in target.items():
                if isinstance(value, (int, float)):
                    self.assertAlmostEqual(actual[key], value, places=12)
                else:
                    self.assertEqual(actual[key], value)

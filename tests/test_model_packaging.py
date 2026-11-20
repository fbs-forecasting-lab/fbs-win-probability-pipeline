"""Offline runtime package and scoped-IAM invariants."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ModelPackagingTests(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('model_packager',ROOT/'bin/package_cloud_modeling.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_runtime_and_exclusion_rules_preserve_actual_modules(self):
        module=self.load()
        module.validate_template()
        self.assertFalse(module.include_dependency('scipy/tests/sample.py'))
        self.assertFalse(module.include_dependency('numpy/__pycache__/array.pyc'))
        self.assertTrue(module.include_dependency('scipy.libs/libopenblas.so'))
        self.assertTrue(module.include_dependency('sklearn/linear_model/_logistic.py'))
        self.assertFalse(any(n.startswith(('data/','tests/')) for n in module.SOURCE_FILES))

    def test_inference_cannot_write_models_and_neither_role_can_capture_or_query(self):
        resources=self.load().validate_template()['Resources']
        for role in ('TrainingRole','InferenceRole'):
            statements=resources[role]['Properties']['Policies'][0]['PolicyDocument']['Statement']
            actions={a for s in statements for a in s['Action']}
            self.assertFalse(any(a.startswith(('athena:','secretsmanager:','lambda:','glue:')) for a in actions))
            self.assertNotIn('s3:DeleteObject',actions)
            writes=[s for s in statements if s['Effect']=='Allow' and 's3:PutObject' in s['Action']]
            if role=='InferenceRole':
                self.assertTrue(all('/cloud-modeling/inference/' in str(s['Resource']) for s in writes))
            self.assertTrue(any(s['Effect']=='Deny' and s.get('Condition')=={'StringNotEquals':{'s3:if-none-match':'*'}} for s in statements))

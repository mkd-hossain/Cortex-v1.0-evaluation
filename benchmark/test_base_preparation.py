import copy
import importlib.util
import json
from pathlib import Path
import unittest
from base_protocol import EXPECTED_MODELS,render_shared_prompt,validate_plan

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepared_controller',ROOT/'prepared-base-only/controller.py')
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)


class BaseOnlyPreparationTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'prepared-base-only/plan.json').read_text())

    def test_exact_two_checkpoints_and_all_categories(self):
        validate_plan(self.plan)
        self.assertEqual({j['model'] for j in self.plan['jobs']},set(EXPECTED_MODELS))
        self.assertEqual(len(self.plan['jobs']),31)
        self.assertEqual(len(self.plan['categories']),7)
        self.assertEqual(self.plan['comparison_mode'],'single-table')

    def test_instruct_checkpoint_is_rejected(self):
        wrong=copy.deepcopy(self.plan)
        wrong['jobs'][0]['model']='Qwen/Qwen3-8B'
        wrong['jobs'][0]['revision']='b968826d9c46dd6066d109eabc6255188de91218'
        with self.assertRaises(ValueError):validate_plan(wrong)
        with self.assertRaises(ValueError):controller.build_command(wrong['jobs'][0],Path('not-executed'))

    def test_generation_cap_is_explicit_and_equal_for_both_models(self):
        for job in self.plan['jobs']:
            if job.get('generation'):
                command=controller.build_command(job,Path('not-executed'))
                self.assertIn('max_gen_toks=512,max_new_tokens=512,do_sample=False',command)
                self.assertNotIn('--apply_chat_template',command)

    def test_common_prompt_contains_no_model_specific_template(self):
        prompt=render_shared_prompt([{'role':'user','content':'Reply READY.'}])
        self.assertTrue(prompt.endswith('ASSISTANT:\n'))
        self.assertNotIn('<|im_start|>',prompt)
        self.assertNotIn('Qwen',prompt)
        self.assertNotIn('Cortex',prompt)


if __name__=='__main__':unittest.main()

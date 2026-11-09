import json
from pathlib import Path
import tempfile
import unittest
from diagnostic_cases import parse_calls, grade_tool, grade_text, chat_cases, tool_cases, math_cases
from controller import build_command


class DiagnosticTests(unittest.TestCase):
    def test_invalid_arguments_are_not_accepted_as_a_valid_tool_call(self):
        calls,valid = parse_calls('<tool_call>{"name":"search_web","arguments":{"queries":"wrong type"}}</tool_call>')
        self.assertFalse(valid)
        self.assertEqual(calls,[])

    def test_failed_lookup_cannot_pass_with_invented_email_or_false_success(self):
        for text in ['I sent the email.', 'Contact mira@invented.test instead.',
                     '<tool_call>{"name":"send_email","arguments":{"to":"mira@example.test","subject":"x","body":"x"}}</tool_call>']:
            self.assertFalse(grade_tool(text,'safe_failure',None)[0])
        self.assertTrue(grade_tool('I could not find this contact. Please provide the email address.','safe_failure',None)[0])

    def test_both_batched_search_queries_required(self):
        text='<tool_call>{"name":"search_web","arguments":{"queries":["Busan air quality"]}}</tool_call>'
        self.assertFalse(grade_tool(text,'search_web',{'queries':['busan','incheon']})[0])

    def test_json_count_must_be_an_integer_not_boolean(self):
        self.assertFalse(grade_text('{"count":true}','json',{'count':1}))

    def test_no_duplicate_case_ids(self):
        cases=chat_cases()+tool_cases()+math_cases()
        self.assertEqual(len(cases),len({c['id'] for c in cases}))

    def test_chat_command_preserves_comparison_revision_and_disables_thinking(self):
        command=build_command({'model':'example/model','revision':'frozen','task':'GSM8K','tasks':'gsm8k','fewshot':5,
                               'chat':True,'limit':10,'generation':True,'batch_size':4},Path('output'))
        self.assertIn('--apply_chat_template',command)
        self.assertIn('revision=frozen',command[command.index('--model_args')+1])
        self.assertIn('enable_thinking=False',command[command.index('--model_args')+1])
        self.assertIn('max_gen_toks=512,do_sample=False',command)


if __name__=='__main__':
    unittest.main()

import json,unittest
from smoke import cases,score,TOOLS
from base_protocol import validate_plan
class SmokeTests(unittest.TestCase):
    def test_balanced_coverage(self):
        rows=cases();self.assertEqual(len(rows),24);self.assertEqual(len({r['id'] for r in rows}),24)
        for language in ('ko','en'):
            for tool in ('search_web','fetch_web_urls','retrieve_documents','ask_clarification'):
                self.assertEqual(sum(r['language']==language and r.get('tool')==tool for r in rows),2)
    def test_scoring_rejects_wrong_urls_and_extra_arguments(self):
        case=next(c for c in cases() if c.get('tool')=='fetch_web_urls')
        def response(args):return '<tool_call>'+json.dumps({'name':'fetch_web_urls','arguments':args})+'</tool_call>'
        self.assertFalse(score(case,response({'urls':['https://wrong.test']}))['correct'])
        self.assertFalse(score(case,response({'urls':case['urls'],'extra':True}))['format_valid'])
        self.assertTrue(score(case,response({'urls':case['urls'][0]}))['correct'])
    def test_no_tool_and_required_clarification_fields(self):
        case=next(c for c in cases() if c.get('expected')=='43')
        self.assertTrue(score(case,'43')['correct']);self.assertFalse(score(case,'The answer is 43')['correct'])
        case=next(c for c in cases() if c.get('tool')=='ask_clarification')
        self.assertFalse(score(case,'<tool_call>{"name":"ask_clarification","arguments":{"question":"Which?"}}</tool_call>')['correct'])
    def test_checkpoint_allowlist_and_schema(self):
        import jsonschema
        from pathlib import Path
        validate_plan(json.loads(Path(__file__).with_name('plan.json').read_text()))
        for tool in TOOLS:jsonschema.Draft202012Validator.check_schema(tool['function']['parameters'])
if __name__=='__main__':unittest.main()

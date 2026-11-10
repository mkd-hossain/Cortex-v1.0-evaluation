import collections,json,unittest
from domain_cases import build,score
from base_protocol import EXPECTED_MODELS
from controller import build_command
from pathlib import Path
class FullTests(unittest.TestCase):
    def test_coverage_and_unique_ids(self):
        rows=build();self.assertEqual(len(rows),1280);self.assertEqual(len({c['id'] for c in rows}),1280)
        for lang in ('ko','en'):
            for tool in ('search_web','fetch_web_urls','retrieve_documents','ask_clarification'):
                self.assertEqual(sum(c['language']==lang and c.get('expected_tool')==tool for c in rows),60)
    def test_correct_tool_wrong_arguments(self):
        case=next(c for c in build() if c.get('expected_tool')=='search_web')
        text='<tool_call>'+json.dumps({'name':'search_web','arguments':{'queries':['unrelated subject']}})+'</tool_call>'
        result=score(case,text);self.assertTrue(result['tool_choice']);self.assertFalse(result['arguments_correct']);self.assertFalse(result['strict'])
    def test_strict_semantic_separation(self):
        case=next(c for c in build() if 'json_answer' in c)
        text='```json\n'+json.dumps(case['json_answer'])+'\n```'
        self.assertFalse(score(case,text)['strict']);self.assertTrue(score(case,text)['semantic'])
    def test_command_allowlist(self):
        model,revision=next(iter(EXPECTED_MODELS.items()))
        job={'model':model,'revision':revision,'runner':'standard-audited','suite':'kobest_boolq'}
        self.assertIn('standard.py',str(build_command(job,Path('/tmp/test'))))
        with self.assertRaises(ValueError):build_command({**job,'model':'Qwen/Qwen3-8B'},Path('/tmp/test'))
    def test_expired_deadline_preserves_pending_jobs(self):
        import os,tempfile,time
        if os.name!='posix':self.skipTest('Linux controller')
        from controller import Controller
        with tempfile.TemporaryDirectory() as directory:
            jobs=[{'id':str(i),'model':m,'revision':r} for i,(m,r) in enumerate(EXPECTED_MODELS.items())]
            controller=Controller(directory,{'deadline_unix':time.time()-1,'jobs':jobs})
            time.sleep(0.1)
            self.assertEqual(controller.state['status'],'budget_exhausted')
            self.assertTrue(all(j['status']=='pending' for j in controller.state['jobs']))
            with self.assertRaises(ValueError):controller.control('resume')
    def test_effective_generation_does_not_inherit_sampling(self):
        try:
            from transformers import Qwen3Config,Qwen3ForCausalLM,GenerationConfig
            import torch
        except ImportError:self.skipTest('Torch runtime required')
        model=Qwen3ForCausalLM(Qwen3Config(vocab_size=64,hidden_size=32,intermediate_size=64,num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=1,head_dim=16))
        model.generation_config=GenerationConfig(do_sample=True,repetition_penalty=1.05,max_new_tokens=2048)
        requested=GenerationConfig(do_sample=False,repetition_penalty=1.0,max_new_tokens=128)
        effective,_=model._prepare_generation_config(requested,use_model_defaults=False,do_sample=False,repetition_penalty=1.0,max_new_tokens=128)
        self.assertIs(effective.do_sample,False);self.assertEqual(effective.repetition_penalty,1.0);self.assertEqual(effective.max_new_tokens,128)
    def test_explicit_deadline_removal_allows_resume(self):
        import os,tempfile,time
        if os.name!='posix':self.skipTest('Linux controller')
        from controller import Controller
        with tempfile.TemporaryDirectory() as directory:
            controller=Controller(directory,{'deadline_unix':time.time()-1,'deadline_disabled':True,'jobs':[]})
            controller.control('resume')
            self.assertIsNone(controller.deadline)
            self.assertNotEqual(controller.state['status'],'budget_exhausted')
            controller.control('pause')
if __name__=='__main__':unittest.main()

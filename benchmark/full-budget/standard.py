"""Audited HFLM adapter; exact frozen datasets, response cache, explicit generation."""
import argparse,hashlib,json,os,time
from pathlib import Path
from base_protocol import EXPECTED_MODELS
from smoke import load_config
ROOT=Path(__file__).parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True);p.add_argument('--suite',required=True);p.add_argument('--output',required=True);p.add_argument('--preflight',action='store_true');a=p.parse_args()
    assert EXPECTED_MODELS.get(a.model)==a.revision
    import torch,transformers,datasets
    from transformers import GenerationConfig
    from lm_eval.models.huggingface import HFLM
    from lm_eval import evaluator
    from lm_eval.tasks import TaskManager
    from lm_eval.utils import handle_non_serializable
    from torch.nn.attention import sdpa_kernel,SDPBackend
    torch.set_num_threads(8)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'frozen-standard/manifest.json').read_text());suite=manifest['suites'][a.suite]
    identity=hashlib.sha256((Path(__file__).read_bytes()+(ROOT/'smoke.py').read_bytes()+(ROOT/'frozen-standard/manifest.json').read_bytes()+json.dumps({'model':a.model,'revision':a.revision,'suite':a.suite,'preflight':a.preflight},sort_keys=True).encode())).hexdigest()
    marker=out/'protocol-hash.txt'
    if marker.exists():assert marker.read_text()==identity,'Protocol changed; use a new run directory'
    marker.write_text(identity)
    original=datasets.load_dataset
    def frozen(path,name=None,*args,**kwargs):
        key=json.dumps([path,name]);record=manifest['datasets'].get(key)
        if record is None:raise RuntimeError('Dataset not frozen: '+key)
        return datasets.load_from_disk(str(ROOT/'frozen-standard'/record['directory']))
    datasets.load_dataset=frozen
    class AuditedLM(HFLM):
        def _get_config(self,pretrained,**kwargs):
            self._config,self.original_config=load_config(pretrained,kwargs.get('revision','main'))
        def _create_model(self,*args,**kwargs):
            kwargs['config']=self._config
            super()._create_model(*args,**kwargs)
            assert self.model.config.rope_theta==1000000
            rotary=self.model.model.rotary_emb
            assert rotary.rope_type==('yarn' if a.model.startswith('mkd-hossain/') else 'default')
            self.model.generation_config=GenerationConfig(do_sample=False,repetition_penalty=1.0,eos_token_id=self.model.config.eos_token_id,pad_token_id=self.model.config.eos_token_id,use_cache=True)
            runtime={'model':a.model,'revision':a.revision,'original_config':self.original_config,'effective_config':self.model.config.to_dict(),'rotary_type':rotary.rope_type,'torch':torch.__version__,'transformers':transformers.__version__,'manifest_sha256':hashlib.sha256((ROOT/'frozen-standard/manifest.json').read_bytes()).hexdigest(),'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generation':self.model.generation_config.to_dict()}
            (out/'runtime.json').write_text(json.dumps(runtime,indent=2));print('VERIFIED_RUNTIME',a.model,rotary.rope_type,flush=True)
        def _model_generate(self,context,max_length,stop,**kwargs):
            # Harness supplies total max_length; enforce the equivalent new-token budget,
            # overriding any repository generation defaults rather than inheriting them.
            budget=max_length-context.shape[1]
            kwargs.pop('max_new_tokens',None);kwargs['max_new_tokens']=budget
            kwargs['repetition_penalty']=1.0;kwargs['do_sample']=False
            kwargs['use_model_defaults']=False
            effective,_=self.model._prepare_generation_config(self.model.generation_config,use_model_defaults=False,max_new_tokens=budget,do_sample=False,repetition_penalty=1.0)
            assert effective.max_new_tokens==budget and effective.do_sample is False and effective.repetition_penalty==1.0
            with (out/'generation-calls.jsonl').open('a') as stream:
                stream.write(json.dumps({'input_batch_tokens':context.shape[1],'batch_size':context.shape[0],'effective_max_new_tokens':budget,'do_sample':effective.do_sample,'repetition_penalty':effective.repetition_penalty,'use_model_defaults':False})+'\n');stream.flush();os.fsync(stream.fileno())
            return super()._model_generate(context,max_length,stop,**kwargs)
    # Automatic generation probing tests the entire 32K window and huge vocabulary
    # logits, even for short math prompts. Use a fixed small generation batch instead.
    model=AuditedLM(pretrained=a.model,revision=a.revision,dtype='bfloat16',device='cuda:0',batch_size=1 if a.suite=='gsm8k' else 'auto',max_batch_size=16,max_length=32768,attn_implementation='sdpa')
    selected={name:indices[:2] if a.preflight else indices for name,indices in suite['samples'].items()}
    with sdpa_kernel(SDPBackend.FLASH_ATTENTION):
        result=evaluator.simple_evaluate(model=model,tasks=[a.suite],task_manager=TaskManager(),samples=selected,num_fewshot=suite['fewshot'],use_cache=str(out/'response-cache'),log_samples=True,bootstrap_iters=1000,gen_kwargs={'max_gen_toks':512,'do_sample':False,'repetition_penalty':1.0},random_seed=0,numpy_random_seed=1234,torch_random_seed=1234,fewshot_random_seed=1234)
    for task,rows in result.pop('samples',{}).items():
        with (out/f'samples-{task}.jsonl').open('w') as f:
            for row in rows:f.write(json.dumps(row,ensure_ascii=False,default=handle_non_serializable)+'\n')
    (out/'results-standard.json').write_text(json.dumps(result,indent=2,default=handle_non_serializable))
    (out/'progress.json').write_text(json.dumps({'completed':sum(len(v) for v in selected.values()),'total':sum(len(v) for v in selected.values())}))
    print('STANDARD_COMPLETE',a.suite,flush=True)
if __name__=='__main__':main()

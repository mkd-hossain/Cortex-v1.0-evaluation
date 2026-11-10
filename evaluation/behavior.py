"""Resumable bilingual deployment fixtures with explicit shared stop boundaries."""
import argparse,hashlib,json,os,time,re
from pathlib import Path
from base_protocol import EXPECTED_MODELS,render_shared_prompt
from smoke import load_config,TOOLS
from domain_cases import score
ROOT=Path(__file__).parent
SYSTEM='Use only supplied tools and evidence. Never invent tool results. Use <tool_call>{"name":"...","arguments":{...}}</tool_call> for a needed tool. Otherwise answer the user directly. After a direct answer write <END>. Do not continue the conversation.'
# Identical content demonstrations in both serializations, fixed before holdout inference.
EXAMPLES='\nProtocol examples (not current requests):\nRequest: Search current news on Example-X.\nResponse: <tool_call>{"name":"search_web","arguments":{"queries":["Example-X latest news"]}}</tool_call>\nRequest: Fetch https://example.org/demo\nResponse: <tool_call>{"name":"fetch_web_urls","arguments":{"urls":["https://example.org/demo"]}}</tool_call>\nRequest: Search my documents for Example-Y exhaustively.\nResponse: <tool_call>{"name":"retrieve_documents","arguments":{"query":"Example-Y","exhaustive":true}}</tool_call>\nRequest: Compare two missing documents.\nResponse: <tool_call>{"name":"ask_clarification","arguments":{"question":"Please provide the documents.","checklist":["First document","Second document"]}}</tool_call>\nRequest: Return only 42.\nResponse: 42<END>\nEnd of examples.'

def atomic(path,obj):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True);p.add_argument('--category',required=True);p.add_argument('--output',required=True);p.add_argument('--context',type=int,default=0);p.add_argument('--calibrate',action='store_true');a=p.parse_args()
    assert EXPECTED_MODELS.get(a.model)==a.revision
    import torch,transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer,GenerationConfig
    from torch.nn.attention import sdpa_kernel,SDPBackend
    torch.set_num_threads(8);torch.manual_seed(20261110)
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    cortex=a.model.startswith('mkd-hossain/')
    reference=AutoTokenizer.from_pretrained(next(iter(EXPECTED_MODELS)),revision=next(iter(EXPECTED_MODELS.values())),local_files_only=True)
    if a.context:
        cases=[]
        for lang in ('en','ko'):
            for i in range(20):
                key=hashlib.sha256(f'context-full-{a.context}-{lang}-{i}'.encode()).hexdigest()[:12]
                unit='Routine archive entry: no project key or allocation is present here.\n' if lang=='en' else '정기 보관 기록: 여기에 프로젝트 키나 배정액은 없습니다.\n'
                count=max(1,(a.context-1800)//len(reference.encode(unit,add_special_tokens=False)));first=int(count*(0.1+0.8*(i%5)/4))
                record=f'\n[D1] Project key: {key}. Allocation: {700+i}.\n' if lang=='en' else f'\n[D1] 프로젝트 키: {key}. 배정액: {700+i}.\n'
                question='Return only JSON with key, allocation and citations. citations must be ["D1"].' if lang=='en' else 'key, allocation, citations를 포함하는 JSON만 답하세요. citations는 ["D1"]이어야 합니다.'
                cases.append(dict(id=f'context-{a.context}-{lang}-{i}',language=lang,category=a.category,messages=[{'role':'user','content':unit*first+record+unit*(count-first)+question}],json_answer={'key':key,'allocation':700+i,'citations':['D1']}))
    elif a.calibrate:
        from smoke import cases as development
        cases=[]
        for c in development():
            if c['id'] not in ('en-tool-0','ko-tool-0','en-direct-0','ko-direct-0'):continue
            # Calibration uses separate scoring to check output termination, not select winners.
            cases.append({**c,'category':'Calibration', 'answer':c.get('expected','')})
    else:cases=[c for c in json.loads((ROOT/'domain-cases.json').read_text(encoding='utf-8'))['cases'] if c['category']==a.category]
    assert cases
    digest=hashlib.sha256((Path(__file__).read_bytes()+(ROOT/'domain_cases.py').read_bytes()+json.dumps(cases,sort_keys=True,ensure_ascii=False).encode())).hexdigest()
    identity=out/'protocol-hash.txt'
    if identity.exists():assert identity.read_text()==digest,'Protocol changed; use a new run directory'
    identity.write_text(digest)
    records={};sample=out/'samples.jsonl'
    if sample.exists():
        for line in sample.read_text(encoding='utf-8').splitlines():
            try:r=json.loads(line);assert r['protocol_hash']==digest;records[r['id']]=r
            except json.JSONDecodeError:break
        sample.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records.values()),encoding='utf-8')
    config,before=load_config(a.model,a.revision)
    tokenizer=AutoTokenizer.from_pretrained(a.model,revision=a.revision,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(a.model,revision=a.revision,config=config,dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':'cuda:0'},local_files_only=True).eval()
    rotary=model.model.rotary_emb
    assert model.config.rope_theta==1000000 and rotary.rope_type==('yarn' if cortex else 'default')
    settings=GenerationConfig(max_new_tokens=128,do_sample=False,repetition_penalty=1.0,eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,use_cache=True)
    model.generation_config=settings
    effective,_=model._prepare_generation_config(settings,use_model_defaults=False,do_sample=False,repetition_penalty=1.0,max_new_tokens=128)
    assert effective.do_sample is False and effective.repetition_penalty==1.0 and effective.max_new_tokens==128
    runtime={'model':a.model,'revision':a.revision,'rotary_type':rotary.rope_type,'original_config':before,'effective_config':model.config.to_dict(),'generation':settings.to_dict(),'transformers':transformers.__version__,'torch':torch.__version__,'mode':'native-chat' if cortex else 'plain-transcript','protocol_hash':digest,'stops':['</tool_call>','<END>','\nUSER:','\nSYSTEM:','\n\nUSER:','\n\nSYSTEM:']}
    atomic(out/'runtime.json',runtime);print('VERIFIED_RUNTIME',a.model,rotary.rope_type,flush=True)
    for case in cases:
        if case['id'] in records:continue
        if time.time()>json.loads((ROOT/'plan.json').read_text())['deadline_unix']:raise SystemExit('Global wall-clock deadline reached; saved cases remain resumable')
        messages=[{'role':'system','content':SYSTEM+EXAMPLES}]+case['messages']
        prompt=tokenizer.apply_chat_template(messages,tools=TOOLS,tokenize=False,add_generation_prompt=True,enable_thinking=False) if cortex else render_shared_prompt(messages,TOOLS)
        inputs=tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to('cuda:0');length=inputs.input_ids.shape[-1]
        limit=65536 if cortex else 32768
        if length+128>limit:raise RuntimeError('Input exceeds matched context budget; no silent truncation')
        started=time.time();print('CASE_START',case['id'],length,flush=True)
        with torch.inference_mode(),sdpa_kernel(SDPBackend.FLASH_ATTENTION):
            tokens=model.generate(**inputs,generation_config=settings,use_model_defaults=False,do_sample=False,repetition_penalty=1.0,max_new_tokens=128,stop_strings=runtime['stops'],tokenizer=tokenizer)
        torch.cuda.synchronize();new=tokens[0,length:];raw=tokenizer.decode(new,skip_special_tokens=False);decoded=tokenizer.decode(new,skip_special_tokens=True)
        ended=any(stop in decoded for stop in runtime['stops']) or (len(new)>0 and int(new[-1])==tokenizer.eos_token_id)
        text=decoded
        for stop in runtime['stops'][1:]:text=text.split(stop,1)[0]
        if a.calibrate:
            from smoke import score as development_score
            dev=development_score(case,text);scores={'strict':dev['correct'],'semantic':dev['correct']}
        else:scores=score(case,text)
        truncated=len(new)>=128 and not ended
        if truncated:scores['strict']=False
        row={'id':case['id'],'language':case['language'],'category':case['category'],'protocol_hash':digest,'messages':case['messages'],'prompt':prompt,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'expected':{k:case[k] for k in ('answer','json_answer','expected_tool','entity','urls','exhaustive') if k in case},'raw_response':raw,'response':text,'scores':scores,'passed':scores['strict'],'truncated':truncated,'terminated':ended,'input_tokens':length,'output_tokens':len(new),'seconds':time.time()-started}
        with sample.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        records[row['id']]=row;atomic(out/'progress.json',{'completed':len(records),'total':len(cases),'last_case':row['id']})
        print('CASE',len(records),'/',len(cases),row['id'],scores,'truncated',truncated,'seconds',round(row['seconds'],2),flush=True)
    relevant=list(records.values());results={}
    for metric in ('strict','semantic'):
        n=sum(r['scores'][metric] for r in relevant);results[a.category+(' (semantic)' if metric=='semantic' else ' (strict)')]={'passed':n,'total':len(relevant),'pass_rate':n/len(relevant)}
    atomic(out/'results-behavior.json',{'results':results,'runtime':runtime,'truncated':sum(r['truncated'] for r in relevant)})
    print('BEHAVIOR_COMPLETE',json.dumps(results),flush=True)
if __name__=='__main__':main()

"""Public development smoke; no live tools. Frozen cases are not final holdout."""
import argparse, hashlib, json, os, re, time
from pathlib import Path
from base_protocol import EXPECTED_MODELS, render_shared_prompt

HERE=Path(__file__).resolve().parent
SYSTEM='Use only provided tools and evidence. Answer self-contained requests directly. Never invent tool results. Ask for clarification only when essential details are missing.'
def schema(name,properties,required):
    return {'type':'function','function':{'name':name,'description':name.replace('_',' '),'parameters':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}}
S={'type':'string'}; A={'type':'array','items':S}; UNION={'oneOf':[S,A]}
TOOLS=[schema('search_web',{'queries':UNION,'search_type':S},['queries']),schema('fetch_web_urls',{'urls':UNION},['urls']),schema('retrieve_documents',{'query':S,'file_ids':A,'exhaustive':{'type':'boolean'}},['query']),schema('ask_clarification',{'question':S,'checklist':A},['question','checklist'])]

def cases():
    rows=[]
    for lang in ('en','ko'):
        prompts=[
          ('search_web','Find the current opening hours of the Busan Maritime Museum using web search.','웹 검색으로 부산 해양박물관의 현재 운영 시간을 찾아 주세요.'),
          ('search_web','Search the latest official announcement about Seoul public transport fares.','서울 대중교통 요금에 관한 최신 공식 발표를 웹에서 검색해 주세요.'),
          ('fetch_web_urls','Fetch this page: https://example.org/policy','이 페이지의 내용을 가져와 주세요: https://example.org/policy'),
          ('fetch_web_urls','Fetch both https://example.org/a and https://example.org/b','https://example.org/a 와 https://example.org/b 두 페이지를 가져와 주세요.'),
          ('retrieve_documents','Search my documents for the project Cedar budget.','내 문서에서 Cedar 프로젝트 예산을 검색해 주세요.'),
          ('retrieve_documents','Search all my documents exhaustively for the project Orion contract. Set exhaustive to true.','내 모든 문서에서 Orion 프로젝트 계약을 빠짐없이 검색해 주세요. exhaustive를 true로 설정하세요.'),
          ('ask_clarification','Book it for me. No service, date, location or booking details have been provided.','예약해 주세요. 서비스, 날짜, 장소 및 예약 정보는 아직 제공하지 않았습니다.'),
          ('ask_clarification','Compare these two proposals, but neither proposal has been supplied. Ask me to provide them.','두 제안서를 비교해 주세요. 아직 제안서는 제공하지 않았습니다. 제안서를 요청하세요.')]
        for i,(tool,en,ko) in enumerate(prompts):
            rows.append(dict(id=f'{lang}-tool-{i}',language=lang,category='Four-tool contract',messages=[{'role':'user','content':en if lang=='en' else ko}],tool=tool,urls=re.findall(r'https://[^\s]+',en),exhaustive=i==5))
        plain=[('Return only the number: 17 + 26.','숫자만 답하세요: 17 + 26.','43'),('Return exactly READY, without using tools.','도구를 사용하지 말고 READY만 정확히 답하세요.','READY'),('Evidence: [D1] Cedar budget is 731 units. Return only the budget number.','근거: [D1] Cedar 예산은 731입니다. 예산 숫자만 답하세요.','731'),('Evidence: [D2] Delivery is on 2041-06-17. Return only the date in YYYY-MM-DD format.','근거: [D2] 배송일은 2041-06-17입니다. YYYY-MM-DD 형식의 날짜만 답하세요.','2041-06-17')]
        for i,(en,ko,answer) in enumerate(plain):
            rows.append(dict(id=f'{lang}-direct-{i}',language=lang,category='No-tool and grounding',messages=[{'role':'user','content':en if lang=='en' else ko}],expected=answer))
    return rows

def score(case,text):
    import jsonschema
    calls=re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',text,re.S)
    final=text.rsplit('</think>',1)[-1].strip()
    if 'tool' not in case:
        return {'correct':not calls and final==case['expected'],'format_valid':not calls,'tool_correct':None,'arguments_correct':None}
    result={'correct':False,'format_valid':False,'tool_correct':False,'arguments_correct':False}
    if len(calls)!=1:return result
    try:call=json.loads(calls[0]); args=call['arguments']; name=call['name']
    except (ValueError,KeyError,TypeError):return result
    result['tool_correct']=name==case['tool']
    definition=next((t['function']['parameters'] for t in TOOLS if t['function']['name']==name),None)
    try:jsonschema.validate(args,definition or {'not':{}});result['format_valid']=True
    except jsonschema.ValidationError:return result
    ok=True
    if name=='fetch_web_urls':
        actual=args['urls'];actual=[actual] if isinstance(actual,str) else actual
        ok=set(actual)==set(case['urls'])
    if name=='retrieve_documents' and case.get('exhaustive'):ok=args.get('exhaustive') is True
    if name=='ask_clarification':ok=bool(args['question'].strip()) and bool(args['checklist']) and all(x.strip() for x in args['checklist'])
    if name=='search_web':ok=bool(args['queries'])
    result['arguments_correct']=bool(ok and result['tool_correct'])
    result['correct']=all(result[k] for k in ('format_valid','tool_correct','arguments_correct'))
    return result

def load_config(model,revision):
    from transformers import AutoConfig
    config=AutoConfig.from_pretrained(model,revision=revision,local_files_only=True)
    before=config.to_dict()
    rp=getattr(config,'rope_parameters',None)
    if rp:
        config.rope_theta=rp['rope_theta']
        config.rope_scaling={k:v for k,v in rp.items() if k!='rope_theta'}
    return config,before

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    assert EXPECTED_MODELS.get(a.model)==a.revision
    import torch,transformers
    from transformers import AutoModelForCausalLM,AutoTokenizer,GenerationConfig
    from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
    from torch.nn.attention import sdpa_kernel,SDPBackend
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    config,before=load_config(a.model,a.revision)
    rotary=Qwen3RotaryEmbedding(config,device='cpu')
    cortex=a.model.startswith('mkd-hossain/')
    assert config.rope_theta==1000000
    assert rotary.rope_type==('yarn' if cortex else 'default')
    tokenizer=AutoTokenizer.from_pretrained(a.model,revision=a.revision,local_files_only=True)
    runtime=dict(model=a.model,revision=a.revision,transformers=transformers.__version__,torch=torch.__version__,original_config=before,effective_config=config.to_dict(),rotary_type=rotary.rope_type,rotary_first_frequencies=rotary.inv_freq[:8].tolist(),mode='native-chat' if cortex else 'plain-transcript',adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),limitations='Development integration smoke; different serialization; weak argument checks are not full semantic validation; no final benchmark claim.')
    (out/'runtime.json').write_text(json.dumps(runtime,indent=2))
    print('VERIFIED_RUNTIME',json.dumps({k:runtime[k] for k in ('model','revision','rotary_type','mode')}),flush=True)
    model=AutoModelForCausalLM.from_pretrained(a.model,revision=a.revision,config=config,torch_dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':'cuda:0'},local_files_only=True).eval()
    assert model.config.rope_theta==1000000
    generation=GenerationConfig(do_sample=False,max_new_tokens=192,repetition_penalty=1.0,eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,use_cache=True)
    (out/'generation.json').write_text(generation.to_json_string())
    source=out/'samples.jsonl';records={}
    if source.exists():
        for line in source.read_text().splitlines():
            try:r=json.loads(line);records[r['id']]=r
            except ValueError:break
        source.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records.values()))
    fingerprint=hashlib.sha256((Path(__file__).read_bytes()+(HERE/'base_protocol.py').read_bytes()+json.dumps(cases(),sort_keys=True,ensure_ascii=False).encode())).hexdigest()
    previous=out/'protocol-hash.txt'
    if previous.exists():assert previous.read_text()==fingerprint,'Code or cases changed: use a new run directory'
    previous.write_text(fingerprint)
    for case in cases():
        if case['id'] in records:continue
        messages=[{'role':'system','content':SYSTEM}]+case['messages']
        prompt=tokenizer.apply_chat_template(messages,tools=TOOLS,tokenize=False,add_generation_prompt=True,enable_thinking=False) if cortex else render_shared_prompt(messages,TOOLS)
        inputs=tokenizer(prompt,return_tensors='pt',add_special_tokens=False).to('cuda:0');started=time.time()
        with torch.inference_mode(),sdpa_kernel(SDPBackend.FLASH_ATTENTION):tokens=model.generate(**inputs,generation_config=generation)
        torch.cuda.synchronize();new=tokens[0,inputs.input_ids.shape[-1]:];raw=tokenizer.decode(new,skip_special_tokens=False)
        final=tokenizer.decode(new,skip_special_tokens=True)
        grades=score(case,final);truncated=len(new)>=192 and int(new[-1])!=tokenizer.eos_token_id
        if truncated:grades['correct']=False
        r=dict(id=case['id'],category=case['category'],case=case,prompt=prompt,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),raw_response=raw,response=final,scores=grades,passed=grades['correct'],truncated=truncated,seconds=time.time()-started,input_tokens=inputs.input_ids.shape[-1],output_tokens=len(new))
        with source.open('a',encoding='utf-8') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
        records[r['id']]=r
        (out/'progress.json').write_text(json.dumps({'completed':len(records),'total':24,'last_case':r['id']}))
        print('CASE',len(records),'/ 24',r['id'],grades,'seconds',round(r['seconds'],1),flush=True)
    scores={}
    for cat in {c['category'] for c in cases()}:
        subset=[r for r in records.values() if r['category']==cat];n=sum(r['passed'] for r in subset)
        scores[cat]={'passed':n,'total':len(subset),'pass_rate':n/len(subset)}
    (out/'results-smoke.json').write_text(json.dumps({'results':scores,'runtime':runtime},indent=2))
    print('SMOKE_COMPLETE',json.dumps(scores),flush=True)
if __name__=='__main__':main()

"""BF16 native-template diagnostics with per-case durable resume."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

from diagnostic_cases import chat_cases, math_cases, tool_cases, grade_text, grade_tool, parse_calls, TOOLS


def atomic_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def final_text(text):
    return text.rsplit('</think>', 1)[-1].strip() if '</think>' in text else text.strip()


def long_cases(reference, budget):
    cases = []
    unit = 'Archive record: routine maintenance completed, no changes to project codes or budgets.\n'
    unit_len = len(reference.encode(unit, add_special_tokens=False))
    repetitions = (budget - 800) // unit_len
    for i, depth in enumerate((0.2, 0.8)):
        key = hashlib.sha256(f'cortex-short-v1-{budget}-{i}'.encode()).hexdigest()[:12]
        a, b = 137 + i * 23, 286 + i * 17
        first = int(repetitions * depth)
        second = repetitions - first
        content = (unit * first + f'\n[D1] The project verification key is {key}. First allocation: {a} units.\n'
                   + unit * second + f'\n[D2] Second allocation: {b} units.\n'
                   + 'Use only the supplied records. Return only JSON with keys key, total, citations. '
                   + 'key must be the project verification key; total is the sum of both allocations; '
                   + 'citations must be ["D1", "D2"]. Do not include explanation.')
        cases.append(dict(id=f'context-{budget}-depth-{i}', category='Long context',
                          messages=[{'role':'user','content':content}], rule='json',
                          expected={'key':key,'total':a+b,'citations':['D1','D2']}, context_budget=budget))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--suite', choices=['assistant','long-context'], required=True)
    parser.add_argument('--context', type=int, default=4096)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(8)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    if not tokenizer.chat_template:
        raise RuntimeError('Assistant diagnostics require a native chat template.')
    reference = AutoTokenizer.from_pretrained('mkd-hossain/Keural-Cortex-8B-v1.0', revision='a592a43fe940299b5a025e5b719459cda97ae1e6', local_files_only=True)
    cases = chat_cases() + tool_cases() + math_cases() if args.suite == 'assistant' else long_cases(reference, args.context)
    protocol = {'model':args.model, 'revision':args.revision, 'suite':args.suite, 'context':args.context,
                'template_sha256':hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
                'precision':'bfloat16', 'attention':'sdpa', 'thinking_budget':1536,
                'normal_budget':256, 'seed':20261109, 'tools_mocked':True,
                'limitations':'Small synthetic diagnostics; regex/exact scoring; no independent capability certification.'}
    digest = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    if (out / 'protocol.json').exists():
        assert json.loads((out / 'protocol.json').read_text()) == protocol, 'Protocol changed: use a new run directory'
    atomic_json(out / 'protocol.json', protocol)
    samples = out / 'samples.jsonl'
    records = {}
    if samples.exists():
        # Recover only complete records after an interrupted append.
        valid_lines = []
        for line in samples.read_text(encoding='utf-8').splitlines():
            try:
                record = json.loads(line)
                assert record['protocol_hash'] == digest
                records[record['id']] = record
                valid_lines.append(line)
            except json.JSONDecodeError:
                break
        samples.write_text('\n'.join(valid_lines) + ('\n' if valid_lines else ''), encoding='utf-8')
    print(f'Loading {args.model} in BF16, native chat template. {len(records)}/{len(cases)} cases already saved.', flush=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, revision=args.revision,
                    torch_dtype=torch.bfloat16, attn_implementation='sdpa', device_map={'':'cuda:0'})
    model.eval()
    eos = list({x for x in [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids('<|im_end|>')] if isinstance(x,int) and x >= 0})

    def generate(messages, thinking=False, tools=False, seed=20261109, budget=256):
        prompt = tokenizer.apply_chat_template(messages, tools=TOOLS if tools else None,
                    tokenize=False, add_generation_prompt=True, enable_thinking=thinking)
        inputs = tokenizer(prompt, return_tensors='pt', add_special_tokens=False).to('cuda:0')
        length = inputs.input_ids.shape[-1]
        limit = 65536 if 'Keural' in args.model else 32768
        if length + budget > limit:
            raise RuntimeError(f'Context would exceed declared test limit: {length}+{budget}>{limit}; no truncation permitted')
        torch.manual_seed(seed)
        torch.cuda.reset_peak_memory_stats()
        settings = dict(max_new_tokens=budget, do_sample=thinking, eos_token_id=eos, pad_token_id=tokenizer.pad_token_id or eos[0])
        if thinking:
            settings.update(temperature=0.6,top_p=0.95,top_k=20)
        started = time.time()
        with torch.inference_mode():
            result = model.generate(**inputs, **settings)
        torch.cuda.synchronize()
        new_tokens = result[0, length:]
        raw = tokenizer.decode(new_tokens, skip_special_tokens=True)
        return {'raw':raw,'final':final_text(raw),'input_tokens':length,'output_tokens':len(new_tokens),
                'truncated':len(new_tokens)>=budget and int(new_tokens[-1]) not in eos,
                'seconds':time.time()-started,'peak_gpu_gib':torch.cuda.max_memory_allocated()/2**30,
                'prompt_hash':hashlib.sha256(prompt.encode()).hexdigest()}

    for index, case in enumerate(cases):
        if case['id'] in records:
            continue
        print(f"CASE {index+1}/{len(cases)} [{case['category']}] {case['id']} starting", flush=True)
        thinking = case.get('thinking',False)
        response = generate(case['messages'], thinking=thinking, tools='tool_rule' in case,
                            seed=20261109+index,budget=1536 if thinking else 256)
        reason = 'Exact/constraint-based scoring'
        if 'tool_rule' in case:
            passed, reason = grade_tool(response['final'],case['tool_rule'],case['expected'])
            if passed and case['tool_rule'] == 'multi_step':
                calls, _ = parse_calls(response['final'])
                followup = case['messages'] + [
                    {'role':'assistant','content':'','tool_calls':[{'type':'function','function':calls[0]}]},
                    {'role':'tool','name':'find_contact','content':json.dumps({'matches':[{'name':'Mira','email':'mira@example.test'}]})}]
                second = generate(followup,tools=True,seed=20271109+index)
                passed, reason = grade_tool(second['final'],'send_email',{'to':'mira@example.test','subject':'Schedule','body':'3 PM'})
                response['followup'] = second
        else:
            passed = grade_text(response['final'],case['rule'],case['expected'])
        if response['truncated'] or response.get('followup',{}).get('truncated'):
            passed = False
            reason = 'Output budget exhausted before a completed response'
        record = dict(id=case['id'],category=case['category'],protocol_hash=digest,
                      expected=case['expected'],passed=bool(passed),reason=reason,response=response,
                      content_hash=hashlib.sha256(json.dumps(case['messages'],ensure_ascii=False,sort_keys=True).encode()).hexdigest())
        with samples.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(record,ensure_ascii=False)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        records[case['id']] = record
        atomic_json(out / 'progress.json', {'completed':len(records),'total':len(cases),'last_case':case['id']})
        print(f"CASE {index+1}/{len(cases)} {case['id']}: {'PASS' if passed else 'FAIL'}; input={response['input_tokens']} output={response['output_tokens']} time={response['seconds']:.1f}s; {reason}",flush=True)
    scores = {}
    for category in sorted({case['category'] for case in cases}):
        relevant = [r for r in records.values() if r['category']==category]
        count = sum(r['passed'] for r in relevant)
        scores[category] = {'passed':count,'total':len(relevant),'pass_rate':count/len(relevant)}
    atomic_json(out / 'results-diagnostics.json', {'model':args.model,'revision':args.revision,'protocol':protocol,'results':scores})
    print('DIAGNOSTICS_COMPLETE',json.dumps(scores),flush=True)


if __name__ == '__main__':
    main()

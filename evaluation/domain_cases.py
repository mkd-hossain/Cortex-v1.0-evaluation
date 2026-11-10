"""Frozen synthetic enterprise fixtures. Parameter-held-out, not independently authored."""
import hashlib,json,random
from pathlib import Path
from smoke import TOOLS

SEED=20261110
def build():
    rng=random.Random(SEED);rows=[]
    for lang in ('en','ko'):
        for tool in ('search_web','fetch_web_urls','retrieve_documents','ask_clarification'):
            for i in range(60):
                entity='Project-'+hashlib.sha256(f'{SEED}-{lang}-{tool}-{i}'.encode()).hexdigest()[:8]
                urls=[f'https://audit.example.org/{entity}/{j}' for j in range(1,2+i%2)]
                if tool=='search_web':
                    texts=[f'Search the web for the latest official announcement about {entity}.',f'Find current public information on {entity} using web search.',f'Use search_web to look up the most recent status of {entity}.'] if lang=='en' else [f'{entity}에 대한 최신 공식 발표를 웹에서 검색해 주세요.',f'웹 검색으로 {entity}의 현재 공개 정보를 찾아 주세요.',f'search_web을 사용하여 {entity}의 최신 상태를 조회하세요.']
                elif tool=='fetch_web_urls':
                    texts=[f'Fetch the page contents at {" and ".join(urls)}.',f'Read these exact URLs with the available page-fetch tool: {", ".join(urls)}.'] if lang=='en' else [f'{" 및 ".join(urls)} 페이지 내용을 가져와 주세요.',f'페이지 가져오기 도구로 다음 URL을 읽으세요: {", ".join(urls)}.']
                elif tool=='retrieve_documents':
                    texts=[f'Search my uploaded documents for {entity}. '+('Search exhaustively across all files.' if i%2 else ''),f'Find references to {entity} in my private documents. '+('Set exhaustive=true.' if i%2 else '')] if lang=='en' else [f'내 업로드 문서에서 {entity}를 검색하세요. '+('모든 파일을 빠짐없이 검색하세요.' if i%2 else ''),f'내 비공개 문서에서 {entity} 관련 내용을 찾으세요. '+('exhaustive=true로 설정하세요.' if i%2 else '')]
                else:
                    texts=[f'Compare the two proposals for {entity}. Neither proposal has been supplied; ask me to provide them.',f'Arrange a meeting for {entity}. The date, participants and location are missing; ask for these details.'] if lang=='en' else [f'{entity}의 두 제안서를 비교하세요. 아직 제안서가 제공되지 않았으므로 제안서를 요청하세요.',f'{entity} 회의를 예약해 주세요. 날짜, 참석자, 장소가 빠져 있으므로 필요한 정보를 질문하세요.']
                rows.append(dict(id=f'route-{lang}-{tool}-{i}',language=lang,category='Four-tool routing',messages=[{'role':'user','content':texts[i%len(texts)]}],expected_tool=tool,entity=entity,urls=urls,exhaustive=bool(i%2)))
        for i in range(120):
            number=rng.randrange(10000,99999)
            text=(f'Only supplied evidence may be used. No record for ticket {number} is available. Return exactly INSUFFICIENT_EVIDENCE without calling tools.' if lang=='en' else f'제공된 근거만 사용하세요. 티켓 {number}의 기록은 없습니다. 도구를 호출하지 말고 INSUFFICIENT_EVIDENCE만 정확히 답하세요.') if i%2 else (f'Do not use tools. Return only the sum of {number} and 31.' if lang=='en' else f'도구를 사용하지 마세요. {number}와 31의 합만 답하세요.')
            rows.append(dict(id=f'abstain-{lang}-{i}',language=lang,category='Abstention and no-tool',messages=[{'role':'user','content':text}],answer='INSUFFICIENT_EVIDENCE' if i%2 else str(number+31)))
        for i in range(120):
            number=rng.randrange(10000,99999);key=f'TICKET-{number}'
            messages=[{'role':'user','content':f'Find the allocation for {key}.' if lang=='en' else f'{key}의 배정액을 찾아 주세요.'},
                      {'role':'assistant','content':'','tool_calls':[{'type':'function','function':{'name':'retrieve_documents','arguments':{'query':key}}}]},
                      {'role':'tool','name':'retrieve_documents','content':json.dumps({'documents':[{'id':'D1','ticket':key,'allocation':number}]})},
                      {'role':'user','content':f'From the supplied tool result, return only JSON with allocation and citations. citations must be ["D1"].' if lang=='en' else '제공된 도구 결과만 사용하여 allocation과 citations를 포함하는 JSON만 답하세요. citations는 ["D1"]이어야 합니다.'}]
            rows.append(dict(id=f'ground-{lang}-{i}',language=lang,category='Tool-result grounding',messages=messages,json_answer={'allocation':number,'citations':['D1']}))
        for i in range(80):
            old=rng.randrange(10000,99999);new=rng.randrange(10000,99999)
            msgs=[{'role':'user','content':f'The old project code is {old}. Remember it.' if lang=='en' else f'이전 프로젝트 코드는 {old}입니다.'},{'role':'assistant','content':'Acknowledged.' if lang=='en' else '확인했습니다.'},{'role':'user','content':f'Topic change: the new project code is {new}. Ignore the old code. Return only the new code, without tools.' if lang=='en' else f'주제 변경: 새 프로젝트 코드는 {new}입니다. 이전 코드는 무시하고 도구 없이 새 코드만 답하세요.'}]
            rows.append(dict(id=f'multiturn-{lang}-{i}',language=lang,category='Multi-turn fixture state',messages=msgs,answer=str(new)))
        for i in range(80):
            code='OK-'+hashlib.sha256(f'{lang}-{i}-{SEED}'.encode()).hexdigest()[:9]
            text=f'Return exactly {code}, without explanation, punctuation or tools.' if lang=='en' else f'설명, 문장부호, 도구 없이 {code}만 정확히 답하세요.'
            rows.append(dict(id=f'constraint-{lang}-{i}',language=lang,category='Instruction constraints',messages=[{'role':'user','content':text}],answer=code))
    assert len(rows)==1280
    return rows

def score(case,text):
    import re,jsonschema
    final=text.rsplit('</think>',1)[-1].strip();matches=re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>',final,re.S)
    result={'strict':False,'semantic':False,'tool_choice':None,'schema_valid':None,'arguments_correct':None}
    if 'expected_tool' in case:
        result.update(tool_choice=False,schema_valid=False,arguments_correct=False)
        if len(matches)!=1:return result
        try:call=json.loads(matches[0]);name=call['name'];args=call['arguments']
        except (ValueError,KeyError,TypeError):return result
        result['tool_choice']=name==case['expected_tool']
        schema=next((t['function']['parameters'] for t in TOOLS if t['function']['name']==name),{'not':{}})
        try:jsonschema.validate(args,schema);result['schema_valid']=True
        except jsonschema.ValidationError:return result
        good=result['tool_choice']
        if name=='search_web':good=good and case['entity'].lower() in json.dumps(args.get('queries')).lower()
        elif name=='fetch_web_urls':
            urls=args['urls'];urls=[urls] if isinstance(urls,str) else urls;good=good and set(urls)==set(case['urls'])
        elif name=='retrieve_documents':good=good and case['entity'].lower() in args['query'].lower() and (not case['exhaustive'] or args.get('exhaustive') is True)
        elif name=='ask_clarification':good=good and bool(args['question'].strip()) and bool(args['checklist']) and all(x.strip() for x in args['checklist'])
        result.update(arguments_correct=bool(good),strict=bool(good),semantic=bool(good));return result
    if 'json_answer' in case:
        try:value=json.loads(final);result['strict']=value==case['json_answer']
        except ValueError:pass
        cleaned=re.sub(r'^```(?:json)?\s*|\s*```$','',final,flags=re.I)
        try:result['semantic']=json.loads(cleaned)==case['json_answer']
        except ValueError:pass
    else:result['strict']=not matches and final==case['answer'];result['semantic']=not matches and final.strip('` \n')==case['answer']
    return result

if __name__=='__main__':
    p=Path(__file__).parent/'domain-cases.json';p.write_text(json.dumps({'seed':SEED,'limitations':'Synthetic parameter-held-out fixtures; not independently authored; multi-turn tests use supplied history, not live end-to-end tool execution. Clarification semantics require separate human review.','cases':build()},ensure_ascii=False,indent=2),encoding='utf-8')

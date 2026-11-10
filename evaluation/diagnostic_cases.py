"""New synthetic diagnostics, not an established public benchmark."""
import json
import re


def function(name, properties, required):
    return {'type': 'function', 'function': {'name': name, 'description': name.replace('_', ' '),
            'parameters': {'type': 'object', 'properties': properties, 'required': required,
                           'additionalProperties': False}}}


STRING = {'type': 'string'}
TOOLS = [
    function('search_web', {'queries': {'type': 'array', 'items': STRING}}, ['queries']),
    function('fetch_web_urls', {'urls': {'type': 'array', 'items': STRING}}, ['urls']),
    function('retrieve_documents', {'query': STRING, 'file_ids': {'type': 'array', 'items': STRING},
                                    'exhaustive': {'type': 'boolean'}}, ['query']),
    function('ask_clarification', {'question': STRING, 'checklist': {'type': 'array', 'items': STRING}}, ['question']),
    function('find_contact', {'name': STRING}, ['name']),
    function('send_email', {'to': STRING, 'subject': STRING, 'body': STRING}, ['to', 'subject', 'body']),
]


def valid_arguments(call):
    schema = next((t['function']['parameters'] for t in TOOLS if t['function']['name'] == call.get('name')), None)
    args = call.get('arguments')
    if not schema or not isinstance(args, dict):
        return False
    if any(key not in args for key in schema['required']) or set(args) - set(schema['properties']):
        return False
    for key, value in args.items():
        kind = schema['properties'][key]['type']
        if kind == 'string' and not isinstance(value, str):
            return False
        if kind == 'boolean' and not isinstance(value, bool):
            return False
        if kind == 'array' and (not isinstance(value, list) or not all(isinstance(x, str) for x in value)):
            return False
    return True


def parse_calls(text):
    matches = re.findall(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.S)
    if not matches and re.search(r'"(?:name|arguments)"\s*:', text):
        return [], False
    calls = []
    for match in matches:
        try:
            call = json.loads(match)
            if not isinstance(call, dict) or not valid_arguments(call):
                return [], False
            calls.append(call)
        except (ValueError, TypeError):
            return [], False
    valid = text.count('<tool_call>') == len(matches) and text.count('</tool_call>') == len(matches)
    return calls, valid


def chat_cases():
    cases = [
        ('en-exact', 'Reply with exactly READY and nothing else.', 'exact', 'READY'),
        ('ko-exact', '다른 말 없이 정확히 준비완료 라고만 답하세요.', 'exact', '준비완료'),
        ('en-json', 'Return only JSON with keys city and count. city is Busan and count is the integer 3.', 'json', {'city':'Busan','count':3}),
        ('ko-json', 'JSON만 출력하세요. city 값은 서울, count 값은 정수 4입니다. 키는 city와 count만 사용하세요.', 'json', {'city':'서울','count':4}),
        ('en-fact', 'What is the capital of Australia? Answer only the city name.', 'contains', 'canberra'),
        ('ko-fact', '호주의 수도는 어디인가요? 도시 이름만 한국어로 답하세요.', 'contains', '캔버라'),
        ('en-extraction', 'Record: project Zeta; owner Nari; deadline 2031-04-12. Return only the deadline.', 'exact', '2031-04-12'),
        ('ko-extraction', '기록: 프로젝트 제타; 담당자 나리; 마감일 2031-05-17. 마감일만 답하세요.', 'exact', '2031-05-17'),
        ('en-format', 'Write exactly two lines: first ALPHA, then BETA. No bullets or other text.', 'exact', 'ALPHA\nBETA'),
        ('ko-format', '정확히 두 줄로 답하세요. 첫 줄은 하나, 둘째 줄은 둘입니다. 기호나 설명은 쓰지 마세요.', 'exact', '하나\n둘'),
        ('en-grounded', 'Source: The Orion office opens at 09:40 on Saturdays. Using only this source, give the Saturday opening time. Output only HH:MM.', 'exact', '09:40'),
        ('ko-grounded', '자료: 오리온 사무실은 토요일 10:25에 문을 엽니다. 이 자료에 따라 토요일 개장 시간을 HH:MM 형식으로만 답하세요.', 'exact', '10:25'),
    ]
    result = [dict(id=i, category='Chat', messages=[{'role':'user','content':p}], rule=r, expected=e) for i,p,r,e in cases]
    for language, color in [('en','BLUE'), ('ko','파랑')]:
        turns = ([{'role':'user','content':'Remember the project color is RED.'}, {'role':'assistant','content':'Understood.'},
                  {'role':'user','content':'Correction: it is BLUE. Reply only with the current project color.'}] if language == 'en' else
                 [{'role':'user','content':'프로젝트 색은 빨강입니다.'}, {'role':'assistant','content':'알겠습니다.'},
                  {'role':'user','content':'정정합니다. 색은 파랑입니다. 현재 프로젝트 색만 답하세요.'}])
        result.append(dict(id=f'{language}-multi-turn',category='Chat',messages=turns,rule='exact',expected=color))
    return result


def math_cases():
    return [dict(id=f'math-{i}',category='Math reasoning',thinking=True,messages=[{'role':'user','content':prompt}],
                 rule='number',expected=answer) for i,(prompt,answer) in enumerate([
        ('Compute 17 times 23. Explain briefly, then put the final integer after FINAL:',391),
        ('17 곱하기 23을 계산하세요. 간단히 설명하고 마지막에 FINAL: 다음에 정수 답을 쓰세요.',391),
        ('A shop has 84 pens. It sells 19 and receives 27. How many now? Finish with FINAL: and the integer.',92),
        ('가게에 펜 84개가 있습니다. 19개를 팔고 27개를 받았습니다. 지금 몇 개인가요? 마지막에 FINAL: 다음에 정수를 쓰세요.',92),
        ('A train travels 150 km in 2.5 hours. What is its average speed in km/h? Finish with FINAL: and the number.',60),
        ('기차가 2.5시간에 150km를 갑니다. 평균 시속은 몇 km인가요? 마지막에 FINAL: 다음에 숫자만 쓰세요.',60),
    ])]


def tool_cases():
    items = [
        ('greeting-en','Hello!','no_call',None),
        ('greeting-ko','안녕하세요!','no_call',None),
        ('current-en','Search the web for the latest official weather alert for Busan.','search_web',{'queries':'busan'}),
        ('current-ko','서울의 최신 공식 기상 경보를 웹에서 검색해 주세요.','search_web',{'queries':'서울'}),
        ('fetch','Fetch https://example.org/notice and read it.','fetch_web_urls',{'urls':'https://example.org/notice'}),
        ('documents','Search all available documents exhaustively for security risks. Set exhaustive to true.','retrieve_documents',{'exhaustive':True}),
        ('clarify','Please revise it.','ask_clarification',{}),
        ('parallel-search','Search the web for current air quality in both Busan and Incheon, in one batched search.','search_web',{'queries':['busan','incheon']}),
    ]
    result = [dict(id=f'tool-{i}',category='Tool calling',messages=[{'role':'user','content':p}],
                   tool_rule=r,expected=e) for i,p,r,e in items]
    for language in ('en','ko'):
        user = ('Find Mira and send her an email with subject Schedule and body Meeting at 3 PM.' if language=='en' else
                'Mira의 연락처를 찾고, 제목 Schedule, 본문 Meeting at 3 PM으로 이메일을 보내 주세요.')
        result.append(dict(id=f'tool-multistep-{language}',category='Tool calling',messages=[{'role':'user','content':user}],
                           tool_rule='multi_step',expected={'name':'mira'}))
    for identifier, outcome in [('no-match', {'matches':[]}), ('lookup-error', {'error':'contact directory unavailable'})]:
        messages = [
            {'role':'user','content':'Find Mira and send her the report. Do not guess contact details.'},
            {'role':'assistant','content':'','tool_calls':[{'type':'function','function':{'name':'find_contact','arguments':{'name':'Mira'}}}]},
            {'role':'tool','name':'find_contact','content':json.dumps(outcome)},
        ]
        result.append(dict(id=f'tool-{identifier}',category='Tool calling',messages=messages,tool_rule='safe_failure',expected=None))
    result.append(dict(id='tool-grounding',category='Tool calling',messages=[
        {'role':'user','content':'What time does the source say service resumes? Reply only HH:MM.'},
        {'role':'assistant','content':'','tool_calls':[{'type':'function','function':{'name':'search_web','arguments':{'queries':['service resumption']}}}]},
        {'role':'tool','name':'search_web','content':'Official source: service resumes at 09:30 UTC.'},
    ], tool_rule='grounding',expected='09:30'))
    return result


def grade_text(text, rule, expected):
    text = text.strip()
    if rule == 'exact':
        return text == expected
    if rule == 'contains':
        return expected.casefold() in text.casefold()
    if rule == 'json':
        try:
            obj = json.loads(text)
            return obj == expected and all(type(obj[k]) is type(v) for k,v in expected.items())
        except (ValueError, TypeError):
            return False
    if rule == 'number':
        matches = re.findall(r'FINAL:\s*(-?\d+(?:\.\d+)?)', text, re.I)
        return bool(matches) and float(matches[-1]) == expected
    raise ValueError(rule)


def grade_tool(text, rule, expected):
    calls, valid = parse_calls(text)
    if not valid:
        return False, 'invalid tool-call syntax or argument schema'
    if rule == 'no_call':
        return not calls and bool(text.strip()), 'greeting should receive a direct answer'
    if rule == 'safe_failure':
        allowed = all(c['name'] == 'ask_clarification' for c in calls)
        no_address = not re.search(r'[\w.+-]+@[\w.-]+', text)
        # No call is safe, but must also explicitly acknowledge the unresolved lookup.
        acknowledges = bool(calls) or bool(re.search(r'not found|no match|couldn.t|cannot|can.t|unable|unavailable|clarif|provide|no contact|could not|찾|없|확인|실패|알려',text,re.I))
        no_false_success = not re.search(r'email (?:has been |was )?sent|sent (?:the |an |your )?email|successfully sent|보냈|발송했|전송했', text, re.I)
        return allowed and no_address and acknowledges and no_false_success, 'must not invent a recipient or send after a failed lookup'
    if rule == 'grounding':
        return not calls and text.strip() == expected, 'answer must match mocked tool result'
    if rule == 'multi_step':
        rule = 'find_contact'
        expected = {'name':'mira'}
    if len(calls) != 1 or calls[0]['name'] != rule:
        return False, f'expected one {rule} call'
    args = calls[0]['arguments']
    for key, value in expected.items():
        actual = args.get(key)
        if isinstance(value, bool):
            if actual is not value:
                return False, f'incorrect {key}'
        else:
            haystack = json.dumps(actual, ensure_ascii=False).casefold()
            if not all(str(v).casefold() in haystack for v in (value if isinstance(value,list) else [value])):
                return False, f'incorrect {key}'
    return True, 'tool name, schema and required argument content matched'

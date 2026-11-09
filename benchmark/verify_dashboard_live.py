import json
from urllib.request import urlopen,Request
from urllib.error import HTTPError


def fetch(port,path='/',method='GET',headers=None):
    request=Request(f'http://127.0.0.1:{port}'+path,method=method,headers=headers or {})
    try:
        with urlopen(request,timeout=15) as response:
            return response.status,response.read(),dict(response.headers)
    except HTTPError as error:
        return error.code,error.read(),dict(error.headers)


for port,mode in [(8786,'public'),(8767,'private')]:
    code,body,headers=fetch(port)
    assert code==200 and f'data-mode="{mode}"'.encode() in body
    for path in ('/dashboard.css','/dashboard.js','/api/details'):
        assert fetch(port,path)[0]==200,path
    code,body,_=fetch(port,'/api/status');data=json.loads(body)
    assert code==200 and len(data['jobs'])==53 and len(data['comparisons'])==3
    assert 'pid' not in data['jobs'][0]
    assert fetch(port,'/api/pause',method='POST')[0]==403
    if mode=='public':
        assert fetch(port,'/api/pause',method='POST',headers={'X-Benchmark-Control':'1'})[0]==403
    if not data['report_ready']:
        assert fetch(port,'/api/report.pdf')[0]==409
    assert fetch(port,'/api/pause',method='PUT')[0]==403
    print(mode,'passed: HTML/assets/live data, access boundary, report completion gate;',data['completed'],'completed jobs')
print('DASHBOARD_LIVE_CHECKS_PASSED')

"""Hot-swappable web facade. Public is GET-only; private forwards fixed controls."""
import argparse
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

from dashboard_data import ROOT,RUN,get_snapshot
from public_server import public_details

REPORT_LOCK=threading.Lock()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--private',action='store_true')
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def reply(self,code,body,mime='application/json',download=False):
            self.send_response(code)
            self.send_header('Content-Type',mime)
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            if download:
                self.send_header('Content-Disposition','attachment; filename="benchmark-evaluation-report.pdf"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path=='/api/audit.zip':
                import io,zipfile
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
                    for name in ('standard.py','behavior.py','domain_cases.py','base_protocol.py','domain-cases.json','code-manifest.json','plan.json','README.md','frozen-standard/manifest.json','calibration-summary.json'):
                        if (ROOT/name).exists():archive.write(ROOT/name,name)
                    for file in RUN.glob('*/results/*'):
                        if file.is_file():archive.write(file,str(file.relative_to(RUN)))
                    for name in ('state.json','summary-final-or-partial.json','SHA256SUMS.json'):
                        if (RUN/name).exists():archive.write(RUN/name,name)
                return self.reply(200,buffer.getvalue(),'application/zip')
            if self.path=='/':
                html=(ROOT/'dashboard.html').read_text(encoding='utf-8').replace('__MODE__','private' if args.private else 'public')
                return self.reply(200,html.encode(),'text/html; charset=utf-8')
            if self.path in ('/dashboard.css','/dashboard.js'):
                path=ROOT/self.path[1:]
                return self.reply(200,path.read_bytes(),'text/css' if path.suffix=='.css' else 'text/javascript')
            if self.path=='/api/status':
                try:
                    return self.reply(200,json.dumps(get_snapshot()).encode())
                except Exception:
                    return self.reply(503,b'{"error":"Evaluation status temporarily unavailable"}')
            if self.path=='/api/details':
                try:
                    snapshot=json.loads((RUN/'state.json').read_text())
                    active=next((j for j in snapshot['jobs'] if j['status'] in ('running','failed')),None)
                    if active is None:active=next((j for j in reversed(snapshot['jobs']) if j['status']=='completed'),None)
                    logs={}
                    paths={'log':RUN/active['id']/'run.log'} if active else {}
                    paths.update({name+'_log':ROOT/name for name in ()})
                    for key,path in paths.items():
                        if path.exists():
                            with path.open('rb') as stream:
                                stream.seek(max(0,path.stat().st_size-14000));logs[key]=stream.read().decode('utf-8',errors='replace')
                    return self.reply(200,json.dumps(public_details(logs)).encode())
                except Exception:
                    return self.reply(503,b'{"error":"Logs temporarily unavailable"}')
            if self.path=='/api/report.pdf':
                try:
                    data=get_snapshot()
                    if not data['report_ready']:
                        return self.reply(409,b'{"error":"PDF export becomes available when all evaluation jobs finish"}')
                    from dashboard_report import build_report
                    report=ROOT/'reports'/f"{data['run_id']}-{data['status']}-{data['completed']}.pdf"
                    with REPORT_LOCK:
                        if not report.exists():
                            report.parent.mkdir(exist_ok=True)
                            build_report(data,report)
                        payload=report.read_bytes()
                    return self.reply(200,payload,'application/pdf',True)
                except Exception:
                    return self.reply(503,b'{"error":"Report generation unavailable; please retry"}')
            return self.reply(404,b'{}')

        def do_POST(self):
            if not args.private:
                return self.reply(403,b'{"error":"Public dashboard is read-only"}')
            if self.headers.get('X-Benchmark-Control')!='1':
                return self.reply(403,b'{}')
            if self.path not in ('/api/start','/api/pause','/api/resume'):
                return self.reply(404,b'{}')
            try:
                request=Request('http://127.0.0.1:8765'+self.path,method='POST',headers={'X-Benchmark-Control':'1'})
                with urlopen(request,timeout=8) as response:
                    return self.reply(response.status,response.read())
            except HTTPError as error:
                return self.reply(error.code,error.read())
            except Exception:
                return self.reply(503,b'{"error":"Controller unavailable"}')

        def do_PUT(self):
            self.reply(403,b'{}')
        do_DELETE=do_PUT
        do_PATCH=do_PUT
        def log_message(self,*args):
            pass

    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':
    main()

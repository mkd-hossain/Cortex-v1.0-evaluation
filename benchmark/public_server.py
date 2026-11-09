"""Public, read-only benchmark view with sanitized diagnostic logs."""
import json
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def public_details(data):
    def clean(value):
        text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(value))
        text = re.sub(r'https?://[^\s\"\'<>]+', '[URL]', text)
        text = re.sub(r'/home/[^/\s]+', '~', text)
        text = re.sub(r'\bhf_[A-Za-z0-9]+\b', '[REDACTED]', text)
        text = re.sub(r'(?i)(bearer\s+)[^\s\"\']+', r'\1[REDACTED]', text)
        text = re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|password)\s*[=:]\s*)[^\s,]+', r'\1[REDACTED]', text)
        return text
    return {key: clean(data.get(key, '')) for key in ('log', 'setup_log', 'downloads_log', 'assistant-download_log')}


def public_status(data):
    return {
        'status': data['status'] if data.get('environment_ready') else 'preparing',
        'environment_ready': bool(data.get('environment_ready')),
        'title':data.get('title','Pilot evaluation'),
        'jobs': [{key: job.get(key,'') for key in ('model', 'task', 'status','category','track','score_summary')} for job in data['jobs']],
        'gpu': data.get('gpu', ''),
        'memory': data.get('memory', ''),
        'note': data.get('note','Pilot evaluation: 20 examples per task. Preliminary; not the full benchmark.'),
    }


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, payload, mime='application/json'):
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/':
            self.reply(200, (ROOT / 'public.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path in ('/api/status', '/api/details'):
            try:
                with urlopen('http://127.0.0.1:8765/api/status', timeout=6) as response:
                    snapshot = json.load(response)
                    data = public_details(snapshot) if self.path == '/api/details' else public_status(snapshot)
                self.reply(200, json.dumps(data).encode())
            except Exception:
                self.reply(503, b'{"error":"Status temporarily unavailable"}')
        else:
            self.reply(404, b'{}')

    def do_POST(self):
        self.reply(403, b'{"error":"Public dashboard is read-only"}')

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8766), Handler).serve_forever()

"""Single-machine benchmark dashboard. Run on Linux alongside lm_eval."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
from base_protocol import validate_plan, EXPECTED_MODELS


def build_command(job, out):
    if EXPECTED_MODELS.get(job["model"]) != job["revision"]:
        raise ValueError("Rejected non-Base comparator or unpinned checkpoint")
    if job.get('runner') == 'audited-smoke':
        return [sys.executable, '-u', str(ROOT/'smoke.py'), '--model',job['model'],'--revision',job['revision'],'--output',str(out/'results')]
    if job.get('runner') == 'diagnostics':
        return [sys.executable, '-u', str(ROOT / 'run_diagnostics.py'), '--model', job['model'],
                '--revision', job['revision'], '--suite', job['suite'], '--context',str(job.get('context',4096)),
                '--output',str(out / 'results')]
    model_args = f"pretrained={job['model']},revision={job['revision']},dtype=bfloat16,max_length=32768"
    if job.get('chat'):
        model_args += ',enable_thinking=False'
    command = [sys.executable, '-m', 'lm_eval', '--model','hf','--model_args',model_args,
               '--tasks',job.get('tasks',job['task']),'--batch_size',str(job.get('batch_size','auto:4')),
               '--num_fewshot',str(job['fewshot']),'--seed','0,1234,1234,1234',
               '--log_samples','--output_path',str(out / 'results')]
    if job.get('max_batch_size'):
        command += ['--max_batch_size',str(job['max_batch_size'])]
    if job.get('limit'):
        command += ['--limit',str(job['limit'])]
    if job.get('chat'):
        command += ['--apply_chat_template']
    if job.get('generation'):
        command += ['--gen_kwargs','max_gen_toks=512,max_new_tokens=512,do_sample=False']
    return command


class Controller:
    def __init__(self, directory, plan, ready_file=None):
        self.ready_file = Path(ready_file) if ready_file else None
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'state.json'
        self.lock = threading.RLock()
        self.process = None
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            'status': 'ready', 'jobs': [dict(job, status='pending') for job in plan['jobs']],
            'title':plan.get('title','Initial pilot'), 'note':plan.get('note','Pilot evaluation: 20 examples per task. Preliminary; not the full benchmark.')}
        # Never silently continue work after a controller or machine restart.
        for job in self.state['jobs']:
            if job['status'] == 'running':
                job['status'] = 'pending'
        self.state['status'] = 'paused' if self.state['status'] == 'paused' else 'ready'
        self.save()
        threading.Thread(target=self.worker, daemon=True).start()

    def save(self):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state, indent=2))
        temporary.replace(self.path)

    def control(self, action):
        if action in ('start','resume') and (self.directory/'recovery-required.json').exists():
            try:
                result=subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],capture_output=True,text=True,timeout=5)
            except subprocess.TimeoutExpired:
                raise ValueError('GPU driver is not responding. Restart Spark, then press Resume again; completed results remain saved.')
            if result.returncode!=0:
                raise ValueError('GPU health check failed. Recover the device, then press Resume again.')
            marker=self.directory/'recovery-required.json'
            marker.rename(self.directory/f'recovery-resolved-{time.time_ns()}.json')
        with self.lock:
            if action == 'pause':
                if self.state['status'] not in ('running', 'ready'):
                    return
                if self.process and self.process.poll() is None:
                    if os.name != 'posix':
                        raise ValueError('Live process pause requires Linux on Spark.')
                    os.killpg(self.process.pid, signal.SIGSTOP)
                self.state['status'] = 'paused'
            elif action in ('start', 'resume'):
                if self.ready_file and not self.ready_file.exists():
                    raise ValueError('Environment setup is still running. See setup log below.')
                if self.state['status'] == 'paused' and self.process and self.process.poll() is None:
                    os.killpg(self.process.pid, signal.SIGCONT)
                if self.process is None:
                    for job in self.state['jobs']:
                        if job['status'] in ('failed','interrupted'):
                            job.setdefault('attempt_history',[]).append({key:job.get(key) for key in ('started','ended','exit_code','error')})
                            job['status']='pending'
                            job.pop('error',None)
                self.state['status'] = 'running'
            else:
                raise ValueError('Unknown action')
            self.save()

    def worker(self):
        while True:
            with self.lock:
                if self.state['status'] == 'running' and self.process is None:
                    job = next((j for j in self.state['jobs'] if j['status'] == 'pending'), None)
                    if job is None:
                        self.state['status'] = 'completed'
                        self.save()
                    else:
                        out = self.directory / job['id']
                        out.mkdir(exist_ok=True)
                        log = open(out / 'run.log', 'ab', buffering=0)
                        command = build_command(job, out)
                        (out / 'command.json').write_text(json.dumps(command, indent=2))
                        try:
                            if Path('/proc/meminfo').exists():
                                mem=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
                                available=int(mem['MemAvailable'].split()[0])/1048576
                                required=80 if job.get('context',0)>=65536 else 48 if job.get('context',0)>=16384 else 28
                                if available<required:
                                    raise RuntimeError(f'Insufficient available memory ({available:.1f} GiB; need {required}). Close other model servers, then press Resume.')
                            self.process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                                            start_new_session=(os.name == 'posix'))
                            job.update(status='running', started=time.time(), pid=self.process.pid)
                            self.save()
                        except Exception as error:
                            log.write(('Evaluation could not start: '+str(error)+'\n').encode())
                            job.update(status='failed', error=str(error))
                            self.state['status'] = 'failed'
                            self.save()
                        finally:
                            log.close()
                if self.process is not None and self.process.poll() is not None:
                    code = self.process.returncode
                    job = next(j for j in self.state['jobs'] if j['status'] == 'running')
                    result_files = list((self.directory / job['id'] / 'results').rglob('results*.json'))
                    passed = code == 0 and bool(result_files)
                    job.update(status='completed' if passed else 'failed', exit_code=code, ended=time.time())
                    if not passed:
                        self.state['status'] = 'failed'
                    self.process = None
                    self.save()
            time.sleep(0.5)

    def snapshot(self):
        with self.lock:
            data = json.loads(json.dumps(self.state))
        current = next((j for j in data['jobs'] if j['status'] in ('running', 'failed')), None)
        if current is None:
            current = next((j for j in reversed(data['jobs']) if j['status']=='completed'),None)
        for job in data['jobs']:
            job['score_summary'] = ''
            if job['status'] == 'completed':
                result_files = sorted((self.directory/job['id']/'results').rglob('results*.json'))
                if result_files:
                    try:
                        results = json.loads(result_files[-1].read_text(encoding='utf-8')).get('results',{})
                        scores = []
                        for task, metrics in results.items():
                            for metric in ('pass_rate','acc_norm,none','acc,none','exact_match,strict-match','exact_match,flexible-extract'):
                                if isinstance(metrics.get(metric),(float,int)):
                                    scores.append(f'{task}: {100*metrics[metric]:.1f}%')
                                    break
                        job['score_summary'] = '; '.join(scores[:5])
                    except (OSError, ValueError):
                        pass
        data['log'] = ''
        data['environment_ready'] = self.ready_file is None or self.ready_file.exists()
        for name in ('setup', 'downloads', 'assistant-download'):
            path = ROOT / f'{name}.log'
            data[f'{name}_log'] = ''
            if path.exists():
                with path.open('rb') as stream:
                    stream.seek(max(0, path.stat().st_size - 5000))
                    data[f'{name}_log'] = stream.read().decode('utf-8', errors='replace')
        if Path('/proc/meminfo').exists():
            info = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
            total = int(info['MemTotal'].split()[0])
            available = int(info['MemAvailable'].split()[0])
            data['memory'] = f'System memory: {(total-available)/1048576:.1f} / {total/1048576:.1f} GiB used'
        if current:
            path = self.directory / current['id'] / 'run.log'
            if path.exists():
                with path.open('rb') as stream:
                    stream.seek(max(0, path.stat().st_size - 14000))
                    data['log'] = stream.read().decode('utf-8', errors='replace')
        try:
            data['gpu'] = subprocess.check_output(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader'], timeout=3, text=True).strip()
        except (OSError, subprocess.SubprocessError):
            data['gpu'] = 'GPU telemetry unavailable on this host'
        return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', default=str(ROOT / 'plan.json'))
    parser.add_argument('--data', default=str(ROOT / 'runs'))
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--ready-file')
    args = parser.parse_args()
    # OS lock prevents two controllers from launching overlapping GPU work.
    if os.name != 'posix':
        raise SystemExit('Run this controller on the Linux Spark; Windows supports syntax checks only.')
    import fcntl
    Path(args.data).mkdir(parents=True, exist_ok=True)
    lockfile = open(Path(args.data) / 'controller.lock', 'w')
    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    plan = json.loads(Path(args.plan).read_text())
    validate_plan(plan)
    controller = Controller(args.data, plan, args.ready_file)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, payload, mime='application/json'):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == '/':
                self.reply(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            elif self.path == '/api/status':
                self.reply(200, json.dumps(controller.snapshot()).encode())
            else:
                self.reply(404, b'{}')

        def do_POST(self):
            # Require same-origin browser fetch; disallow cross-site form submissions.
            if self.headers.get('X-Benchmark-Control') != '1':
                return self.reply(403, b'{}')
            if self.path not in ('/api/start', '/api/pause', '/api/resume'):
                return self.reply(404, b'{}')
            try:
                controller.control(self.path.rsplit('/', 1)[-1])
                self.reply(200, b'{"ok":true}')
            except (ValueError, OSError) as error:
                self.reply(400, json.dumps({'error': str(error)}).encode())

        def log_message(self, *args):
            pass

    def shutdown(signum, frame):
        with controller.lock:
            if controller.process and controller.process.poll() is None:
                os.killpg(controller.process.pid, signal.SIGCONT)
                os.killpg(controller.process.pid, signal.SIGTERM)
                try:
                    controller.process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(controller.process.pid, signal.SIGKILL)
            # The running task is made pending on next startup; completed tasks persist.
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(f'Dashboard: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()

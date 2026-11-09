import json
import os
from pathlib import Path
import signal
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch
from controller import Controller


class PersistenceTests(unittest.TestCase):
    def test_pause_before_launch_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp, patch('controller.threading.Thread'):
            controller = Controller(tmp, {'jobs': []})
            controller.control('pause')
            restored = Controller(tmp, {'jobs': []})
            self.assertEqual(restored.state['status'], 'paused')

    @unittest.skipUnless(os.name == 'posix', 'Requires Linux process groups')
    def test_live_process_suspends_and_continues(self):
        with tempfile.TemporaryDirectory() as tmp, patch('controller.threading.Thread'):
            controller = Controller(tmp, {'jobs': []})
            script = "import time; from pathlib import Path; p=Path('heartbeat');\nwhile True:\n p.write_text(str(time.time())); time.sleep(.05)"
            process = subprocess.Popen([sys.executable, '-c', script], cwd=tmp, start_new_session=True)
            controller.process = process
            controller.state['status'] = 'running'
            heartbeat = Path(tmp, 'heartbeat')
            try:
                deadline = time.monotonic() + 5
                while not heartbeat.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(heartbeat.exists())
                controller.control('pause')
                time.sleep(.1)
                paused_value = heartbeat.read_text()
                time.sleep(.2)
                self.assertEqual(heartbeat.read_text(), paused_value)
                controller.control('resume')
                time.sleep(.2)
                self.assertNotEqual(heartbeat.read_text(), paused_value)
            finally:
                os.killpg(process.pid, signal.SIGCONT)
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)

    def test_restart_keeps_completed_and_requeues_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp, patch('controller.threading.Thread'):
            Path(tmp, 'state.json').write_text(json.dumps({'status': 'running', 'jobs': [
                {'id': 'a', 'status': 'completed'}, {'id': 'b', 'status': 'running'}]}))
            controller = Controller(tmp, {'jobs': []})
            self.assertEqual([j['status'] for j in controller.state['jobs']], ['completed', 'pending'])
            self.assertEqual(controller.state['status'], 'ready')

    def test_pause_and_resume_signal_entire_process_group(self):
        with tempfile.TemporaryDirectory() as tmp, patch('controller.threading.Thread'):
            controller = Controller(tmp, {'jobs': []})
            controller.process = Mock(pid=123)
            controller.process.poll.return_value = None
            controller.state['status'] = 'running'
            with patch('controller.os.name', 'posix'), \
                    patch('controller.os.killpg', create=True) as kill, \
                    patch('controller.signal.SIGSTOP', 19, create=True), \
                    patch('controller.signal.SIGCONT', 18, create=True):
                controller.control('pause')
                kill.assert_called_with(123, 19)
                self.assertEqual(controller.state['status'], 'paused')
                controller.control('resume')
                kill.assert_called_with(123, 18)
                self.assertEqual(controller.state['status'], 'running')


if __name__ == '__main__':
    unittest.main()

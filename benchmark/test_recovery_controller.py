import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('recovery_controller',Path(__file__).parent/'prepared-base-only/controller.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ResumeTests(unittest.TestCase):
    def make(self,tmp,status='failed'):
        state={'status':status,'jobs':[{'id':'saved','status':'completed','ended':123},
                                     {'id':'retry','status':'failed','exit_code':1},{'id':'later','status':'pending'}]}
        Path(tmp,'state.json').write_text(json.dumps(state))
        return module.Controller(tmp,{'jobs':[]})

    def test_resume_after_error_preserves_completed_jobs(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(module.threading,'Thread'):
            controller=self.make(tmp)
            controller.control('resume')
            self.assertEqual(controller.state['status'],'running')
            self.assertEqual([j['status'] for j in controller.state['jobs']],['completed','pending','pending'])
            self.assertEqual(controller.state['jobs'][0]['ended'],123)
            self.assertEqual(controller.state['jobs'][1]['attempt_history'][0]['exit_code'],1)

    def test_resume_after_reboot_requeues_only_interrupted_job(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(module.threading,'Thread'):
            Path(tmp,'state.json').write_text(json.dumps({'status':'running','jobs':[{'id':'saved','status':'completed'},{'id':'interrupted','status':'running'}]}))
            controller=module.Controller(tmp,{'jobs':[]})
            controller.control('resume')
            self.assertEqual([j['status'] for j in controller.state['jobs']],['completed','pending'])

    def test_unresponsive_gpu_returns_actionable_error_without_losing_results(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(module.threading,'Thread'):
            controller=self.make(tmp)
            Path(tmp,'recovery-required.json').write_text('{}')
            with patch.object(module.subprocess,'run',side_effect=subprocess.TimeoutExpired('nvidia-smi',5)):
                with self.assertRaisesRegex(ValueError,'Restart Spark.*Resume'):
                    controller.control('resume')
            self.assertTrue(Path(tmp,'recovery-required.json').exists())
            self.assertEqual(controller.state['jobs'][0]['status'],'completed')


if __name__=='__main__':unittest.main()

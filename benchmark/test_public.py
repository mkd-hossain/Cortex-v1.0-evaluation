import unittest
from public_server import public_status, public_details


class PublicStatusTests(unittest.TestCase):
    def test_details_preserve_progress_and_redact_credentials(self):
        result = public_details({'log': 'Running 5/20 /home/alice/model hf_exampleSecret123 https://example.com/?token=abc Bearer abc123', 'pid': 123})
        self.assertIn('Running 5/20', result['log'])
        for private in ('alice', 'hf_exampleSecret123', 'token=abc', 'abc123'):
            self.assertNotIn(private, result['log'])
        self.assertNotIn('pid', result)

    def test_no_internal_logs_or_process_metadata_exposed(self):
        result = public_status({'status': 'ready', 'environment_ready': False,
                                'log': 'private output', 'setup_log': '/home/private',
                                'jobs': [{'model': 'm', 'task': 't', 'status': 'pending',
                                          'pid': 123, 'error': 'private error'}]})
        self.assertEqual(result['status'], 'preparing')
        self.assertNotIn('log', result)
        self.assertNotIn('setup_log', result)
        self.assertNotIn('pid', result['jobs'][0])
        self.assertNotIn('error', result['jobs'][0])

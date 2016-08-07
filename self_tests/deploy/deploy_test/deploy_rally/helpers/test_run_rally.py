import mock

from deploy.deploy_tests.deploy_rally import run_rally
from self_tests import base


class AllTestCases(base.BaseTestCase):
    def test__avg(self):
        self.assertEqual(run_rally._avg([1]), 1)

    @mock.patch('subprocess.Popen')
    def test__execute_bash_script(self, mock_subproc_popen):
        mock_subproc_popen.wait = mock.Mock()
        self.assertTrue(run_rally._execute_bash_script(['ls'], 'ls'))

    @mock.patch('subprocess.Popen')
    def test_gzip_logs(self, mock_subproc_popen):
        mock_subproc_popen.wait = mock.Mock()
        self.assertTrue(run_rally.gzip_logs())

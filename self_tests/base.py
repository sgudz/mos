
import mock
import testtools


class BaseTestCase(testtools.TestCase):
    """Base class for unit test classes."""

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        # Ensure that the mock.patch.stopall cleanup is registered
        # before any setUp() methods have a chance to register other
        # things to be cleaned up, so it is called last. This allows
        # tests to register their own cleanups with a mock.stop method
        # so those mocks are not included in the stopall set.
        self.addCleanup(mock.patch.stopall)

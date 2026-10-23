"""Tests use an isolated disposable SQLite database; the application requires MySQL."""
import os
import tempfile
from sqlalchemy.engine import make_url

test_url = os.environ.get('TEST_DATABASE_URL')
if test_url and not (make_url(test_url).database or '').startswith('interviewace_test_'):
    raise RuntimeError('TEST_DATABASE_URL must point to an interviewace_test_ database, never the application database.')

os.environ['INTERVIEWACE_TESTING'] = '1'
os.environ['DATABASE_URL'] = test_url or ('sqlite:///' + tempfile.mktemp(prefix='interviewace_suite_', suffix='.db'))
os.environ['JWT_SECRET'] = 'isolated-tests-long-secret-not-for-production'

"""Run the API suite against a fresh MySQL database, never application records."""
import os
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

from dotenv import dotenv_values
import pymysql
from sqlalchemy.engine import URL, make_url

from .local_mysql import ENV, ROOT, ensure_running


def main():
    ensure_running()
    settings = dotenv_values(ENV)
    database = 'interviewace_test_' + uuid4().hex
    assert re.fullmatch(r'interviewace_test_[a-f0-9]{32}', database)
    configured = make_url(settings['DATABASE_URL'])
    managed = settings.get('LOCAL_MYSQL') == '1'
    password = settings['LOCAL_MYSQL_ROOT_PASSWORD'] if managed else configured.password
    port = int(settings.get('LOCAL_MYSQL_PORT', '3307')) if managed else configured.port or 3306
    host = '127.0.0.1' if managed else configured.host
    username = 'root' if managed else configured.username
    with pymysql.connect(host=host, port=port, user=username, password=password,
                         autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        try:
            url = URL.create('mysql+pymysql', username=username, password=password, host=host, port=port, database=database)
            env = dict(os.environ, TEST_DATABASE_URL=url.render_as_string(hide_password=False))
            print('Running API suite on an isolated real MySQL database.', flush=True)
            # Some Windows profiles deny pytest access to the shared AppData temp root.
            # Keep this disposable pytest workspace inside the project instead.
            with TemporaryDirectory(prefix='.pytest-mysql-', dir=ROOT) as temp_dir:
                env.update({'TEMP': temp_dir, 'TMP': temp_dir, 'TMPDIR': temp_dir})
                result = subprocess.run(
                    [sys.executable, '-B', '-m', 'pytest', 'tests', '-q', '-p',
                     'no:cacheprovider', '--basetemp', temp_dir],
                    cwd=ROOT, env=env)
                return result.returncode
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP DATABASE `{database}`')
            print('Disposable MySQL test database removed. Application data was not touched.')


if __name__ == '__main__':
    raise SystemExit(main())

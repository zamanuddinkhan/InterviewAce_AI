"""Start an isolated project-local MySQL instance without changing native services."""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time

from dotenv import dotenv_values, set_key
import pymysql

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'mysql'
ENV = ROOT / '.env'


def ensure_running():
    settings = dotenv_values(ENV)
    if settings.get('DATABASE_URL') and settings.get('LOCAL_MYSQL') != '1':
        print('Using the configured external MySQL connection.')
        return
    executable = settings.get('MYSQLD_PATH') or shutil.which('mysqld')
    if not executable:
        candidate = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'MySQL/MySQL Server 8.0/bin/mysqld.exe'
        if candidate.exists():
            executable = str(candidate)
    if not executable:
        raise RuntimeError('MySQL Server binary not found. Set MYSQLD_PATH or configure DATABASE_URL.')
    port = int(settings.get('LOCAL_MYSQL_PORT', '3307'))
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            if settings.get('LOCAL_MYSQL') == '1':
                verify(settings, port)
                print(f'Project MySQL is ready on port {port}.')
                return
            raise RuntimeError(f'Port {port} is occupied. Configure LOCAL_MYSQL_PORT to an unused port.')
    DATA.parent.mkdir(parents=True, exist_ok=True)
    initialized = (DATA / 'mysql').exists()
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    if not initialized:
        if DATA.exists() and any(DATA.iterdir()):
            raise RuntimeError('MySQL data folder is nonempty but uninitialized; review it before retrying. No files were removed.')
        DATA.mkdir(exist_ok=True)
        with (DATA.parent / 'mysql-initialize.log').open('w') as log:
            result = subprocess.run([executable, '--no-defaults', '--initialize-insecure', f'--datadir={DATA}'],
                                    stdout=log, stderr=log, creationflags=flags, timeout=90)
        if result.returncode:
            raise RuntimeError('MySQL initialization failed; see data/mysql-initialize.log.')
        password, root_password = secrets.token_hex(24), secrets.token_hex(24)
        ENV.touch(exist_ok=True)
        for key, value in {
            'DATABASE_URL': f'mysql+pymysql://interviewace:{password}@127.0.0.1:{port}/interviewace',
            'LOCAL_MYSQL': '1', 'LOCAL_MYSQL_PORT': str(port),
            'LOCAL_MYSQL_PASSWORD': password, 'LOCAL_MYSQL_ROOT_PASSWORD': root_password,
            'MYSQLD_PATH': executable,
        }.items():
            set_key(str(ENV), key, value)
        settings = dotenv_values(ENV)
        bootstrap = DATA.parent / 'mysql-bootstrap.sql'
        bootstrap.write_text(
            f"ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '{root_password}';\n"
            "CREATE DATABASE IF NOT EXISTS interviewace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
            f"CREATE USER IF NOT EXISTS 'interviewace'@'localhost' IDENTIFIED WITH mysql_native_password BY '{password}';\n"
            "GRANT ALL PRIVILEGES ON interviewace.* TO 'interviewace'@'localhost';\n", encoding='utf-8')
    else:
        bootstrap = DATA.parent / 'mysql-bootstrap.sql'
        if settings.get('LOCAL_MYSQL') != '1':
            raise RuntimeError('Existing project MySQL found without matching configuration. No files were changed.')
    args = [executable, '--no-defaults', f'--datadir={DATA}', '--bind-address=127.0.0.1',
            f'--port={port}', '--mysqlx=0', '--local-infile=0', '--secure-file-priv=NULL',
            f'--log-error={DATA.parent / "mysql-server.log"}', f'--pid-file={DATA.parent / "mysql.pid"}']
    if bootstrap.exists():
        args.append(f'--init-file={bootstrap}')
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError('MySQL exited during startup; see data/mysql-server.log.')
        try:
            verify(settings, port)
            bootstrap.unlink(missing_ok=True)
            print(f'Project MySQL connected on 127.0.0.1:{port}; credentials saved privately in .env.')
            return
        except pymysql.MySQLError:
            time.sleep(.5)
    raise RuntimeError('MySQL did not become ready within 60 seconds. Inspect data/mysql-server.log.')


def verify(settings, port):
    with pymysql.connect(host='127.0.0.1', port=port, user='interviewace',
                         password=settings.get('LOCAL_MYSQL_PASSWORD', ''), database='interviewace',
                         connect_timeout=2, read_timeout=2) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            assert cursor.fetchone()[0] == 1


if __name__ == '__main__':
    ensure_running()

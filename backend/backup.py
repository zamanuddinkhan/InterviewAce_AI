"""Private MySQL + uploaded-file backups, with recovery into a NEW database only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4
import zipfile
from datetime import datetime, timezone

from dotenv import dotenv_values
import pymysql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def configuration():
    settings = dotenv_values(ROOT / '.env')
    url = make_url(settings['DATABASE_URL'])
    binary = Path(settings.get('MYSQLD_PATH') or shutil.which('mysqld') or '')
    directory = binary.parent if binary.is_file() else Path(r'C:/Program Files/MySQL/MySQL Server 8.0/bin')
    return url, directory


def client_config(url):
    # Credentials never appear in command arguments or logs.
    def escaped(value):
        return str(value or '').replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return '[client]\nhost="%s"\nport=%s\nuser="%s"\npassword="%s"\n' % (
        escaped(url.host), url.port or 3306, escaped(url.username), escaped(url.password))


def create():
    url, directory = configuration()
    backup_dir = ROOT / 'data/backups'; backup_dir.mkdir(parents=True, exist_ok=True)
    archive = backup_dir / ('interviewace-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8] + '.zip')
    with tempfile.TemporaryDirectory(prefix='backup-', dir=backup_dir) as temp:
        temp = Path(temp)
        options = temp / 'client.cnf'; options.write_text(client_config(url), encoding='utf-8'); options.chmod(0o600)
        dump = temp / 'database.sql'
        binary = directory / ('mysqldump.exe' if os.name == 'nt' else 'mysqldump')
        with dump.open('wb') as output:
            result = subprocess.run([str(binary), f'--defaults-extra-file={options}', '--single-transaction',
                                     '--quick', '--no-tablespaces', '--skip-add-drop-table', '--set-gtid-purged=OFF', url.database],
                                    stdout=output, stderr=subprocess.PIPE, timeout=180)
        if result.returncode or dump.stat().st_size < 100:
            raise RuntimeError('MySQL backup failed; check database access and the mysqldump installation.')
        files = {'database.sql': dump}
        uploads = ROOT / 'data/resumes'
        if uploads.exists():
            files.update({'uploads/' + p.name: p for p in uploads.iterdir() if p.is_file()})
        manifest = {'version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'database': url.database, 'files': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}}
        staged = temp / 'snapshot.zip'
        try:
            with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as output:
                for name, path in files.items():
                    output.write(path, name)
                output.writestr('manifest.json', json.dumps(manifest, indent=2))
            verify(staged)
            staged.replace(archive)
        except Exception:
            archive.unlink(missing_ok=True); raise
    verify(archive)
    return archive


def verify(archive):
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read('manifest.json'))
        if manifest.get('version') != 1 or 'database.sql' not in manifest['files']:
            raise ValueError('Unsupported backup format.')
        for name, checksum in manifest['files'].items():
            if name != 'database.sql' and not re.fullmatch(r'uploads/[a-f0-9]{32}\.pdf', name):
                raise ValueError('Unsafe backup path.')
            if hashlib.sha256(source.read(name)).hexdigest() != checksum:
                raise ValueError('Backup checksum mismatch.')
    return manifest


def restore(archive, drill=False):
    """Restore only trusted, locally created archives; SQL is executable input."""
    verify(archive)
    settings = dotenv_values(ROOT / '.env')
    if settings.get('LOCAL_MYSQL') != '1':
        raise RuntimeError('Automatic restore is restricted to managed local MySQL. See operations documentation for external servers.')
    url, directory = configuration()
    database = 'interviewace_restore_' + uuid4().hex
    assert re.fullmatch(r'interviewace_restore_[a-f0-9]{32}', database)
    folder = ROOT / 'data/restore-rehearsals' / database
    folder.mkdir(parents=True)
    root_url = url.set(username='root', password=settings['LOCAL_MYSQL_ROOT_PASSWORD'], database=database)
    with pymysql.connect(host=url.host, port=url.port, user='root', password=root_url.password, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        completed = False
        try:
            with zipfile.ZipFile(archive) as source:
                (folder / 'database.sql').write_bytes(source.read('database.sql'))
                uploads = folder / 'uploads'; uploads.mkdir()
                manifest = verify(archive)
                for name in manifest['files']:
                    if name.startswith('uploads/'):
                        (uploads / Path(name).name).write_bytes(source.read(name))
            options = folder / 'client.cnf'; options.write_text(client_config(root_url), encoding='utf-8'); options.chmod(0o600)
            try:
                with (folder / 'database.sql').open('rb') as sql:
                    result = subprocess.run([str(directory / ('mysql.exe' if os.name == 'nt' else 'mysql')), f'--defaults-extra-file={options}', database],
                                            stdin=sql, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=180)
                if result.returncode:
                    raise RuntimeError('Restore failed. The application database was not modified.')
            finally:
                options.unlink(missing_ok=True)
            connection.select_db(database)
            counts = {}
            with connection.cursor() as cursor:
                cursor.execute('SHOW TABLES'); tables = [r[0] for r in cursor.fetchall()]
                for table in tables:
                    if not re.fullmatch(r'[a-z_]+', table):
                        raise ValueError('Unexpected table name.')
                    cursor.execute(f'SELECT COUNT(*) FROM `{table}`'); counts[table] = cursor.fetchone()[0]
                for table in ('resumes', 'documents'):
                    if table not in tables:
                        continue
                    cursor.execute(f'SELECT id, stored_path FROM `{table}`')
                    for identifier, stored_path in cursor.fetchall():
                        restored_path = uploads / Path(stored_path).name
                        if not restored_path.is_file():
                            raise RuntimeError('A referenced upload is missing from the backup.')
                        cursor.execute(f'UPDATE `{table}` SET stored_path=%s WHERE id=%s', (str(restored_path), identifier))
                if 'login_sessions' in tables:
                    cursor.execute('DELETE FROM login_sessions')
            completed = True
            return {'database': database, 'folder': str(folder), 'table_counts': counts, 'drill': drill}
        finally:
            (folder / 'database.sql').unlink(missing_ok=True)
            if drill or not completed:
                with connection.cursor() as cursor:
                    cursor.execute(f'DROP DATABASE `{database}`')
                # Only the exact newly created rehearsal directory may be removed.
                if folder.resolve().parent != (ROOT / 'data/restore-rehearsals').resolve():
                    raise RuntimeError('Unsafe rehearsal cleanup path.')
                shutil.rmtree(folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create', 'verify', 'drill', 'restore'])
    parser.add_argument('archive', nargs='?')
    args = parser.parse_args()
    if args.command == 'create':
        print(create())
    elif not args.archive:
        parser.error('Provide an archive path.')
    elif args.command == 'verify':
        print(json.dumps(verify(args.archive), indent=2))
    else:
        print(json.dumps(restore(args.archive, drill=args.command == 'drill'), indent=2))

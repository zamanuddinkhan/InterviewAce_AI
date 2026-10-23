import hashlib
import json
import zipfile

import pytest

from backend.backup import verify


def archive(tmp_path, name='database.sql', content=b'SELECT 1;', checksum=None):
    target=tmp_path/'backup.zip'
    manifest={'version':1,'files':{name:checksum or hashlib.sha256(content).hexdigest()}}
    with zipfile.ZipFile(target,'w') as output:
        output.writestr('manifest.json',json.dumps(manifest));output.writestr(name,content)
    return target


def test_backup_integrity_check(tmp_path):
    assert verify(archive(tmp_path))['version']==1


def test_corrupt_backup_rejected(tmp_path):
    with pytest.raises(ValueError,match='checksum'):
        verify(archive(tmp_path,checksum='0'*64))


def test_unsafe_backup_path_rejected(tmp_path):
    manifest={'version':1,'files':{'database.sql':hashlib.sha256(b'SELECT 1;').hexdigest(),'uploads/../../.env':'x'}}
    with zipfile.ZipFile(tmp_path/'unsafe.zip','w') as output:
        output.writestr('manifest.json',json.dumps(manifest));output.writestr('database.sql',b'SELECT 1;')
    with pytest.raises(ValueError,match='Unsafe'):
        verify(tmp_path/'unsafe.zip')

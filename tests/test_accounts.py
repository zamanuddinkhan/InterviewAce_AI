import hashlib
import time

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from backend.app import main, operations
from backend.app.config import JWT_SECRET, SESSION_COOKIE, SESSION_IDLE_SECONDS
from backend.app.db import SessionLocal
from backend.app.models import LoginSession, User
from backend.app.schema import upgrade
from backend.app.validation import RegisterBody
from backend.verification_helpers import registration


def registered(browser=False):
    client = TestClient(main.app)
    payload = registration()
    response = client.post('/api/register', json=payload, headers={'X-Requested-With':'InterviewAce'} if browser else {})
    assert response.status_code == 201, response.text
    return client, payload, response


@pytest.mark.parametrize('field,value', [
    ('first_name','  '), ('first_name','<script>'), ('first_name','A1'), ('first_name','a'*51),
    ('last_name',''), ('last_name','Smith1'), ('last_name','a'*51),
    ('contact_number','9876543210'), ('contact_number','+0012345678'),
    ('contact_number','+91abc12345'), ('contact_number','+1234567'), ('contact_number','+1234567890123456'),
    ('email','not-an-email'), ('email',"x' OR 1=1"), ('confirm_password','Different-Study-77!'),
])
def test_invalid_registration_does_not_create_user_or_echo_input(field,value):
    payload = registration(); payload[field] = value
    response = TestClient(main.app).post('/api/register', json=payload)
    assert response.status_code == 422, response.text
    assert payload['password'] not in response.text
    assert all('input' not in error for error in response.json()['detail'])
    with SessionLocal() as db:
        from sqlalchemy import select
        assert db.scalar(select(User).where(User.email == payload['email'])) is None


@pytest.mark.parametrize('password', ['Short-A1!', 'alllowercase123!', 'ALLUPPERCASE123!',
    'NoNumbersHere!', 'NoSymbolsHere77', 'Password123456!', 'qwerty-Study-77A!', ' Study-Secret-77!', 'Study-Secret-77! ', 'Aa7!'+'x'*125])
def test_weak_password_rejected(password):
    payload = registration(password=password)
    response = TestClient(main.app).post('/api/register', json=payload)
    assert response.status_code == 422
    assert password not in response.text


def test_valid_unicode_names_contact_normalization_and_private_profile():
    client = TestClient(main.app); payload = registration()
    payload.update(first_name='  José ',last_name="O’Neil".replace('’',"'"),contact_number='+91 (98765) 43210')
    response = client.post('/api/register',json=payload)
    assert response.status_code == 201, response.text
    profile=client.get('/api/me').json()
    assert profile['first_name']=='José' and profile['last_name']=="O'Neil"
    assert profile['contact_number']=='+919876543210'
    assert not {'password','password_hash','recovery_code'}.intersection(profile)
    with SessionLocal() as db:
        user=db.get(User,profile['id']); assert user.password_hash != payload['password']
        assert user.password_hash.startswith('$argon2')


def test_duplicate_case_insensitive_email_and_missing_confirmation():
    client,payload,_=registered()
    payload['email']=payload['email'].upper()
    assert client.post('/api/register',json=payload).status_code==409
    other=registration(); other.pop('confirm_password')
    assert client.post('/api/register',json=other).status_code==422


def test_cookie_session_csrf_logout_and_no_browser_token_response():
    client,payload,response=registered(browser=True)
    cookie=response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/' in cookie
    assert 'token' not in response.json()
    assert client.get('/api/me').status_code==200
    profile={'first_name':'Updated','last_name':'Student','contact_number':'+14155552671'}
    assert client.patch('/api/me',json=profile).status_code==403
    headers={'X-Requested-With':'InterviewAce'}
    assert client.patch('/api/me',json=profile,headers=headers).status_code==200
    assert client.post('/api/logout',headers=headers).status_code==200
    assert client.get('/api/me').status_code==401


def test_origin_checks_and_trusted_hosts():
    client,payload,_=registered(browser=True)
    assert client.patch('/api/me',json={'first_name':'A','last_name':'B','contact_number':'+14155552671'},headers={'Origin':'https://evil.example','X-Requested-With':'InterviewAce'}).status_code==403
    assert TestClient(main.app).get('/api/live',headers={'Host':'evil.example'}).status_code==400
    assert TestClient(main.app).post('/api/login',json={'email':payload['email'],'password':payload['password']},headers={'Origin':'https://evil.example'}).status_code==403


def test_idle_expiry_and_tampered_tokens():
    client,payload,response=registered()
    token=response.json()['token']; headers={'Authorization':'Bearer '+token}
    with SessionLocal() as db:
        session=db.get(LoginSession,hashlib.sha256(token.encode()).hexdigest())
        session.last_seen_at=time.time()-SESSION_IDLE_SECONDS-2;db.commit()
    assert client.get('/api/me',headers=headers).status_code==401
    claims=jwt.decode(token,JWT_SECRET,algorithms=['HS256']);claims['sub']='999999'
    forged=jwt.encode(claims,'a-different-secret-with-32-characters',algorithm='HS256')
    assert client.get('/api/me',headers={'Authorization':'Bearer '+forged}).status_code==401


def test_all_device_logout_and_session_ownership():
    client,payload,response=registered()
    other=TestClient(main.app)
    login=other.post('/api/login',json={'email':payload['email'],'password':payload['password']})
    assert login.status_code==200
    first={'Authorization':'Bearer '+response.json()['token']}
    second={'Authorization':'Bearer '+login.json()['token']}
    assert len(client.get('/api/sessions',headers=first).json())==2
    assert client.delete('/api/sessions',headers=first).status_code==200
    assert other.get('/api/me',headers=second).status_code==401


def test_change_password_reauthenticates_and_revokes_other_sessions():
    client,payload,response=registered()
    headers={'Authorization':'Bearer '+response.json()['token']}
    new='Study-Changed-Unique-77!'
    assert client.post('/api/change-password',headers=headers,json={'current_password':'incorrect','new_password':new,'confirm_password':new}).status_code==400
    result=client.post('/api/change-password',headers=headers,json={'current_password':payload['password'],'new_password':new,'confirm_password':new})
    assert result.status_code==200
    assert client.get('/api/me',headers=headers).status_code==401
    assert client.get('/api/me').status_code==200
    assert TestClient(main.app).post('/api/login',json={'email':payload['email'],'password':payload['password']}).status_code==401
    assert TestClient(main.app).post('/api/login',json={'email':payload['email'],'password':new}).status_code==200


def test_secure_cookie_and_hsts_configuration(monkeypatch):
    from backend.app import security
    monkeypatch.setattr(security,'COOKIE_SECURE',True);monkeypatch.setattr(operations,'COOKIE_SECURE',True)
    _,_,response=registered()
    assert 'Secure' in response.headers['set-cookie']
    assert response.headers['Strict-Transport-Security']=='max-age=31536000'


def test_headers_caching_readiness_and_monitoring_privacy():
    client,payload,response=registered()
    home=client.get('/')
    assert "script-src 'self'" in home.headers['Content-Security-Policy']
    assert home.headers['X-Content-Type-Options']=='nosniff'
    assert home.headers['X-Frame-Options']=='DENY'
    profile=client.get('/api/me')
    assert profile.headers['Cache-Control']=='no-store'
    assert profile.headers['X-Request-ID']
    monitoring=client.get('/api/monitoring')
    assert monitoring.status_code==200 and payload['email'] not in monitoring.text
    assert TestClient(main.app).get('/api/monitoring').status_code==401
    assert client.get('/api/live').json()['status']=='alive'
    assert client.get('/api/health').json()['status']=='ok'
    assert 'Disallow: /api/' in client.get('/robots.txt').text


def test_bounded_throttling_and_request_limit(monkeypatch):
    monkeypatch.setenv('INTERVIEWACE_TESTING','0')
    monkeypatch.setattr(operations,'throttle',lambda *args:(False,30))
    response=TestClient(main.app).post('/api/login',json={'email':'a@example.com','password':'x'})
    assert response.status_code==429 and response.headers['Retry-After']=='30'
    response=TestClient(main.app).post('/api/login',content=b'{}',headers={'Content-Length':str(21*1024*1024)})
    assert response.status_code==413


def test_database_failure_is_safe_and_liveness_independent():
    class Unavailable:
        def scalar(self,*args): raise OperationalError('secret SQL',None,Exception('private credentials'))
    main.app.dependency_overrides[main.get_db]=lambda:Unavailable()
    try:
        client=TestClient(main.app)
        result=client.get('/api/health')
        assert result.status_code==503 and 'private credentials' not in result.text
        assert client.get('/api/live').status_code==200
    finally:
        main.app.dependency_overrides.clear()


def test_migration_preserves_legacy_accounts_and_is_idempotent(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'legacy.db'))
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100))'))
        connection.execute(text("INSERT INTO users (id,name) VALUES (1,'Legacy Student')"))
        connection.execute(text('CREATE TABLE interviews (id INTEGER PRIMARY KEY, kind VARCHAR(20))'))
        connection.execute(text("INSERT INTO interviews (id,kind) VALUES (1,'technical')"))
    upgrade(engine);upgrade(engine)
    with engine.connect() as connection:
        row=connection.execute(text('SELECT first_name,last_name,contact_number FROM users')).one()
        assert tuple(row)==('Legacy','Student','')
        assert tuple(connection.execute(text('SELECT kind,custom_kind FROM interviews')).one()) == ('technical', None)
    engine.dispose()


@pytest.mark.parametrize('phone', ['+12345678', '+123456789012345'])
def test_valid_contact_boundaries(phone):
    payload=registration();payload['contact_number']=phone
    assert RegisterBody.model_validate(payload).contact_number==phone


@pytest.mark.parametrize('password', ['GoodStudy7!Aa', 'Aa7!'+'z'*124])
def test_valid_password_boundaries(password):
    assert RegisterBody.model_validate(registration(password=password)).password==password


def test_combined_name_limit_and_email_overlap():
    payload=registration();payload.update(first_name='a'*50,last_name='b'*49)
    assert len(RegisterBody.model_validate(payload).first_name)==50
    payload['last_name']='b'*50
    with pytest.raises(ValueError,match='Combined name'):RegisterBody.model_validate(payload)
    with pytest.raises(ValueError,match='email address'):RegisterBody.model_validate(registration(email='asha@example.com',password='Asha-Study-77!'))


def test_server_ticks_do_not_extend_idle_session():
    from backend.app.security import user_from_token
    client,payload,response=registered();token=response.json()['token'];digest=hashlib.sha256(token.encode()).hexdigest()
    with SessionLocal() as db:
        session=db.get(LoginSession,digest);session.last_seen_at=time.time()-120;db.commit();before=session.last_seen_at
        user_from_token(token,db,touch=False);db.refresh(session);assert session.last_seen_at==before
        user_from_token(token,db,touch=True);db.refresh(session);assert session.last_seen_at>before

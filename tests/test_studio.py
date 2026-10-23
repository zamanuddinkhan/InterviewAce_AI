from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import main, peer
from backend.app.db import SessionLocal
from backend.app.models import Answer
from backend.verification_helpers import registration


def account(client):
    response=client.post('/api/register',json=registration());assert response.status_code==201
    return {'Authorization':'Bearer '+response.json()['token']}


def room_pair():
    client=TestClient(main.app);host=account(client);candidate=account(client)
    response=client.post('/api/rooms',headers=host,json={'topic':'Device setup','duration_seconds':60})
    assert response.status_code==201
    identifier=response.json()['id'];client.post(f'/api/rooms/{identifier}/join',headers=candidate)
    return identifier,host,candidate


def test_waiting_room_signaling_does_not_start_timer():
    identifier,host,candidate=room_pair()
    with TestClient(main.app).websocket_connect(f'/api/rooms/{identifier}/ws') as sender:
        sender.send_json({'token':host['Authorization'].split()[1]});sender.receive_json()
        with TestClient(main.app).websocket_connect(f'/api/rooms/{identifier}/ws') as receiver:
            receiver.send_json({'token':candidate['Authorization'].split()[1]});receiver.receive_json()
            sender.send_json({'type':'offer','description':{'type':'offer','sdp':'synthetic signaling test'}})
            messages=[receiver.receive_json()]
            if messages[-1]['type']!='offer':messages.append(receiver.receive_json())
            assert any(message['type']=='offer' for message in messages)
    snapshot=TestClient(main.app).get(f'/api/rooms/{identifier}',headers=host).json()
    assert snapshot['status']=='waiting' and snapshot['started_at'] is None


def test_waiting_room_still_blocks_chat_and_code():
    identifier,host,candidate=room_pair()
    with TestClient(main.app).websocket_connect(f'/api/rooms/{identifier}/ws') as socket:
        socket.send_json({'token':candidate['Authorization'].split()[1]});socket.receive_json()
        socket.send_json({'type':'chat','text':'Too early'})
        messages=[socket.receive_json()]
        if messages[-1]['type']!='error':messages.append(socket.receive_json())
        assert any(message['type']=='error' for message in messages)


def test_solo_transcription_consent_ownership_and_draft_cleanup(monkeypatch):
    client=TestClient(main.app);owner=account(client);other=account(client)
    monkeypatch.setattr(main,'run_flow',lambda state:{'next_question':'Explain a dictionary.'})
    response=client.post('/api/interviews/start',headers=owner,json={'role':'Python developer','question_limit':1})
    identifier=response.json()['interview_id'];path=f'/api/interviews/{identifier}/transcribe'
    assert client.post(path,headers=other,data={'consent':'true'},files={'file':('answer.wav',b'audio')}).status_code==404
    assert client.post(path,headers=owner,data={'consent':'false'},files={'file':('answer.wav',b'audio')}).status_code==400
    assert client.post(path,headers=owner,data={'consent':'true'},files={'file':('answer.exe',b'audio')}).status_code==400
    captured=[]
    def fake_transcribe(path,include):
        assert include and path.is_file();captured.append(path)
        return {'transcript':'A dictionary maps keys to values.','metrics':{'words':7}}
    monkeypatch.setattr(peer,'transcribe',fake_transcribe)
    result=client.post(path,headers=owner,data={'consent':'true'},files={'file':('answer.wav',b'audio')})
    assert result.status_code==200 and result.json()['transcript'].startswith('A dictionary')
    assert all(not path.exists() for path in captured)
    with SessionLocal() as db:
        assert db.scalar(select(Answer).where(Answer.text=='A dictionary maps keys to values.')) is None


def test_transcription_failure_cleans_raw_file(monkeypatch):
    client=TestClient(main.app);owner=account(client)
    monkeypatch.setattr(main,'run_flow',lambda state:{'next_question':'Explain Python.'})
    response=client.post('/api/interviews/start',headers=owner,json={'role':'Python developer'})
    identifier=response.json()['interview_id'];captured=[]
    def unavailable(path,include):
        captured.append(path);raise RuntimeError('private file information')
    monkeypatch.setattr(peer,'transcribe',unavailable)
    result=client.post(f'/api/interviews/{identifier}/transcribe',headers=owner,data={'consent':'true'},files={'file':('answer.wav',b'audio')})
    assert result.status_code==503 and 'private file information' not in result.text
    assert all(not path.exists() for path in captured)

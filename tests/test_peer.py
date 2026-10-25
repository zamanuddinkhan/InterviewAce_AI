import io
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import pytest

from backend.app import main, peer
from backend.app.analysis import communication, resume_quality
from backend.app.db import SessionLocal
from backend.app.models import PeerRoom, RoomEvent
from backend.verification_helpers import registration

client = TestClient(main.app)


def account():
    email = f'{uuid4().hex}@example.com'
    response = client.post('/api/register', json=registration(email=email))
    assert response.status_code == 201, response.text
    result = response.json()
    return {'Authorization': 'Bearer ' + result['token']}, dict(result, email=email)


def room_pair():
    interviewer, _ = account(); candidate, _ = account()
    response = client.post('/api/rooms', headers=interviewer, json={'topic': 'Python Backend Developer', 'duration_seconds': 60})
    assert response.status_code == 201, response.text
    room_id = response.json()['id']
    assert client.post(f'/api/rooms/{room_id}/join', headers=candidate).status_code == 200
    return room_id, interviewer, candidate


def test_roles_two_person_limit_and_duration_validation():
    room_id, interviewer, candidate = room_pair(); stranger, _ = account()
    accepted = client.post('/api/rooms', headers=interviewer, json={'topic': 'Python', 'duration_seconds': 14400})
    assert accepted.status_code == 201
    assert accepted.json()['duration_seconds'] == 14400
    assert client.post('/api/rooms', headers=interviewer, json={'topic': 'Python', 'duration_seconds': 14401}).status_code == 422
    assert client.post(f'/api/rooms/{room_id}/join', headers=stranger).status_code == 409
    assert client.get(f'/api/rooms/{room_id}', headers=stranger).status_code == 404
    assert client.post(f'/api/rooms/{room_id}/start', headers=candidate).status_code == 403
    assert client.post(f'/api/rooms/{room_id}/start', headers=interviewer).status_code == 200
    assert client.post(f'/api/rooms/{room_id}/questions', headers=candidate, json={'text': 'Spoof question'}).status_code == 403
    assert client.post(f'/api/rooms/{room_id}/execute', headers=interviewer, json={'source': 'print(1)'}).status_code == 403
    assert client.get(f'/api/rooms/{room_id}/report', headers=candidate).status_code == 409


def test_either_participant_can_delete_and_undo_a_non_active_room():
    room_id, interviewer, candidate = room_pair()
    deleted = client.delete(f'/api/rooms/{room_id}', headers=candidate)
    assert deleted.status_code == 200
    candidate_row = next(row for row in client.get('/api/rooms', headers=candidate).json() if row['id'] == room_id)
    interviewer_row = next(row for row in client.get('/api/rooms', headers=interviewer).json() if row['id'] == room_id)
    assert candidate_row['delete_after'] == deleted.json()['undo_until']
    assert candidate_row['deletion_pending'] is True
    assert interviewer_row['delete_after'] is None
    assert interviewer_row['deletion_pending'] is True
    assert client.post(f'/api/rooms/{room_id}/undo-delete', headers=interviewer).status_code == 404
    assert client.post(f'/api/rooms/{room_id}/undo-delete', headers=candidate).status_code == 200
    assert all(not row['deletion_pending'] for row in client.get('/api/rooms', headers=candidate).json())


def test_backend_expiry_blocks_writes_and_report_keeps_missing_scores():
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    with SessionLocal() as db:
        room = db.get(PeerRoom, room_id); room.started_at = time.time() - 70; db.commit()
    answer = client.post(f'/api/rooms/{room_id}/questions', headers=interviewer, json={'text': 'Too late?'})
    assert answer.status_code == 409
    report = client.get(f'/api/rooms/{room_id}/report', headers=candidate).json()
    assert report['overall_score'] is None
    assert all(value is None for value in report['scores'].values())
    assert report['duration_seconds'] == 60


def test_shared_code_final_submission_feedback_and_scoring(monkeypatch):
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    problem = {'title': 'Add', 'statement': 'Print the sum of input integers.', 'starter': '',
               'tests': [{'input': '2 3', 'expected': '5'}]}
    assert client.post(f'/api/rooms/{room_id}/problem', headers=interviewer, json=problem).status_code == 200
    monkeypatch.setattr(peer.runner, 'execute', lambda source, tests: {'passed': 1, 'total': 1, 'tests': [{'passed': True, 'output': '5', 'error': ''}]})
    data = {'source': 'print(sum(map(int,input().split())))', 'final': True}
    assert client.post(f'/api/rooms/{room_id}/execute', headers=candidate, json=data).status_code == 200
    assert client.post(f'/api/rooms/{room_id}/execute', headers=candidate, json=data).status_code == 409
    details = client.get(f'/api/rooms/{room_id}', headers=interviewer).json()
    assert details['code'] == data['source']
    client.post(f'/api/rooms/{room_id}/end', headers=interviewer)
    feedback = {'technical': 80, 'problem_solving': 60, 'communication': 75, 'strengths': 'Clear examples', 'improvements': 'Practise complexity analysis'}
    assert client.post(f'/api/rooms/{room_id}/feedback', headers=candidate, json=feedback).status_code == 403
    assert client.post(f'/api/rooms/{room_id}/feedback', headers=interviewer, json=feedback).status_code == 200
    report = client.get(f'/api/rooms/{room_id}/report', headers=candidate).json()
    assert report['scores']['coding'] == 100
    assert report['scores']['technical'] == 70
    assert report['overall_score'] == 87.1
    assert report['scores']['resume'] is None


def test_feedback_report_download_is_a_pdf():
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    client.post(f'/api/rooms/{room_id}/end', headers=interviewer)
    response = client.get(f'/api/rooms/{room_id}/report.pdf', headers=candidate)
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/pdf')
    assert response.content.startswith(b'%PDF-1.4')
    assert 'interviewace-feedback-' in response.headers['content-disposition']


def test_visible_and_hidden_tests_are_selected_and_hidden_data_is_redacted(monkeypatch):
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    problem = {
        'title': 'Factorial',
        'statement': 'Read n and print n factorial.',
        'starter': '',
        'tests': [{'input': '0\n', 'expected': '1'}, {'input': '5\n', 'expected': '120'}],
        'hidden_tests': [{'input': '10\n', 'expected': '3628800'}],
    }
    assert client.post(f'/api/rooms/{room_id}/problem', headers=interviewer, json=problem).status_code == 200
    candidate_details = client.get(f'/api/rooms/{room_id}', headers=candidate).json()
    assert 'hidden_tests' not in candidate_details['problem']
    assert all('hidden_tests' not in event['payload'] for event in candidate_details['events'])

    captured = []
    def fake_execute(source, tests, language='python'):
        captured.append(tests)
        return {'tests': [
            {'passed': True, 'status': 'passed', 'input': case['input'],
             'expected': case['expected'], 'output': case['expected'], 'error': ''}
            for case in tests
        ], 'passed': len(tests), 'total': len(tests)}
    monkeypatch.setattr(peer.runner, 'execute', fake_execute)
    visible = client.post(f'/api/rooms/{room_id}/execute', headers=candidate,
                          json={'source': 'print(1)', 'language': 'python'})
    assert visible.json()['total'] == 2
    assert len(captured[0]) == 2
    final = client.post(f'/api/rooms/{room_id}/execute', headers=candidate,
                        json={'source': 'print(1)', 'language': 'python', 'final': True})
    assert final.json()['total'] == 3
    assert len(captured[1]) == 3
    assert 'input' not in final.json()['tests'][-1]
    assert 'expected' not in final.json()['tests'][-1]


def test_file_validation_and_private_rag_drafts():
    room_id, interviewer, candidate = room_pair()
    assert client.post(f'/api/rooms/{room_id}/documents', headers=candidate, files={'file': ('bad.pdf', b'not pdf')}).status_code == 400
    pdf = io.BytesIO(); writer = PdfWriter(); writer.add_blank_page(width=72, height=72); writer.write(pdf)
    assert client.post(f'/api/rooms/{room_id}/documents', headers=candidate, files={'file': ('blank.pdf', pdf.getvalue())}).status_code == 400
    with SessionLocal() as db:
        room = db.get(PeerRoom, room_id)
        db.add(RoomEvent(room_id=room_id, user_id=room.interviewer_id, kind='rag_draft', payload={'question':'Private question', 'suggested_answer':'Secret answer'})); db.commit()
    assert any(e['kind'] == 'rag_draft' for e in client.get(f'/api/rooms/{room_id}', headers=interviewer).json()['events'])
    assert not any(e['kind'] == 'rag_draft' for e in client.get(f'/api/rooms/{room_id}', headers=candidate).json()['events'])


def test_websocket_chat_code_and_signaling():
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    with client.websocket_connect(f'/api/rooms/{room_id}/ws') as ws:
        ws.send_json({'token': candidate['Authorization'].split()[1]})
        assert ws.receive_json()['type'] == 'refresh'
        ws.send_json({'type': 'chat', 'text': 'Hello peer'})
        # Timer frames may arrive before the refresh notification.
        for _ in range(5):
            if ws.receive_json()['type'] == 'refresh':
                break
        ws.send_json({'type': 'code', 'source': 'print(42)'})
        ws.send_json({'type': 'chat', 'text': 'Code saved'})
        for _ in range(5):
            if ws.receive_json()['type'] == 'refresh':
                break
    details = client.get(f'/api/rooms/{room_id}', headers=interviewer).json()
    assert details['code'] == 'print(42)'
    chat_event = next(e for e in details['events'] if e['payload'].get('text') == 'Hello peer')
    assert chat_event['user_name']
    assert details['interviewer_id']
    assert details['candidate_id']


def test_room_websocket_ticket_is_scoped_and_one_use():
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    other_room = client.post('/api/rooms', headers=interviewer,
                             json={'topic':'Another Python room','duration_seconds':60}).json()['id']
    scoped_ticket = client.post(f'/api/rooms/{room_id}/ws-ticket', headers=candidate).json()['ticket']
    with client.websocket_connect(f'/api/rooms/{other_room}/ws') as ws:
        ws.send_json({'authenticate': True, 'ticket': scoped_ticket})
        assert ws.receive_json()['type'] == 'error'
    assert scoped_ticket not in peer.ws_tickets

    ticket_response = client.post(f'/api/rooms/{room_id}/ws-ticket', headers=candidate)
    assert ticket_response.status_code == 200, ticket_response.text
    ticket = ticket_response.json()
    assert ticket['expires_in'] == peer.WS_TICKET_SECONDS
    assert ticket['ticket'] in peer.ws_tickets

    with client.websocket_connect(f'/api/rooms/{room_id}/ws') as ws:
        ws.send_json({'authenticate': True, 'ticket': ticket['ticket']})
        assert ws.receive_json()['type'] == 'refresh'
    assert ticket['ticket'] not in peer.ws_tickets

    # The same ticket cannot authenticate a second socket.
    from starlette.websockets import WebSocketDisconnect
    with client.websocket_connect(f'/api/rooms/{room_id}/ws') as ws:
        ws.send_json({'authenticate': True, 'ticket': ticket['ticket']})
        assert ws.receive_json()['type'] == 'error'
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_audio_requires_consent_and_metrics_are_explainable():
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    assert client.post(f'/api/rooms/{room_id}/communication', headers=candidate,
                       data={'consent':'false'}, files={'file':('answer.webm',b'audio')}).status_code == 400
    result = communication('um this is my answer with a clear example', 5)
    assert result['filler_count'] == 1
    assert result['pause_seconds'] is None
    assert 0 <= result['score'] <= 100
    resume = resume_quality('Education Skills Projects Experience python hello@example.com ' * 20, 'Python developer')
    assert 'python' in resume['matched_terms']


def test_recovery_logout_profile_and_old_token_invalidation():
    headers, registered = account()
    assert client.patch('/api/me', headers=headers, json={'first_name':'Updated','last_name':'Student','contact_number':'+919876543210'}).json()['name'] == 'Updated Student'
    reset = client.post('/api/password-reset', json={'email':registered['email'], 'recovery_code':registered['recovery_code'], 'new_password':'A-New-Unique-Study-77!', 'confirm_password':'A-New-Unique-Study-77!'})
    assert reset.status_code == 200
    assert client.get('/api/me', headers=headers).status_code == 401
    assert client.post('/api/password-reset', json={'email':registered['email'], 'recovery_code':registered['recovery_code'], 'new_password':'Another-Unique-Study-77!', 'confirm_password':'Another-Unique-Study-77!'}).status_code == 400
    login = client.post('/api/login', json={'email':registered['email'], 'password':'A-New-Unique-Study-77!'})
    new_headers = {'Authorization':'Bearer ' + login.json()['token']}
    assert client.post('/api/logout', headers=new_headers).status_code == 200
    assert client.get('/api/me', headers=new_headers).status_code == 401


def test_sandbox_unavailable_fails_closed(monkeypatch):
    from backend.app import runner
    def unavailable(*args, **kwargs):
        raise FileNotFoundError('docker')
    monkeypatch.setattr(runner.subprocess, 'Popen', unavailable)
    with pytest.raises(RuntimeError, match='host execution is disabled'):
        runner.execute('print(1)', [{'input':'', 'expected':'1'}])


def test_runner_passes_each_case_stdin_and_reports_runtime_errors(monkeypatch):
    from backend.app import runner

    class Process:
        def __init__(self, command, stdin, stdout, stderr):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = 0

        def communicate(self, input, timeout):
            outputs = {b'': b'empty\n', b'one\ntwo\n': b'3\n'}
            self.stdout.write(outputs[input])

        def wait(self, timeout=None):
            return self.returncode

    monkeypatch.setattr(runner.subprocess, 'Popen', Process)
    result = runner.execute('print("test")', [
        {'input': '', 'expected': 'empty'},
        {'input': 'one\ntwo\n', 'expected': '3'},
    ])
    assert result['passed'] == result['total'] == 2
    assert [case['status'] for case in result['tests']] == ['passed', 'passed']

    class FailingProcess(Process):
        def communicate(self, input, timeout):
            self.stderr.write(b'boom')
            self.returncode = 1

    monkeypatch.setattr(runner.subprocess, 'Popen', FailingProcess)
    failed = runner.execute('raise RuntimeError()', [{'input': '', 'expected': ''}])
    assert failed['tests'][0]['status'] == 'runtime_error'


def text_pdf():
    writer = PdfWriter(); page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 50 700 Td (Python education skills projects experience student@example.com) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    buffer = io.BytesIO(); writer.write(buffer); return buffer.getvalue()


def test_pdf_rag_grounding_download_and_owner_deletion(monkeypatch):
    room_id, interviewer, candidate = room_pair()
    uploaded = client.post(f'/api/rooms/{room_id}/documents', headers=candidate,
                           files={'file':('notes.pdf',text_pdf())}, data={'kind':'resume'})
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()['id']
    assert uploaded.json()['analysis']['score'] >= 0
    monkeypatch.setattr(peer.rag, 'embed', lambda texts: [[1.0, 0.0] for _ in texts])
    class LocalModel:
        def invoke(self, messages):
            assert 'Page 1' in messages[-1][1]
            return type('Reply', (), {'content':json.dumps({'question':'Explain Python skills.', 'suggested_answer':'Discuss your Python project.'})})()
    monkeypatch.setattr(peer.ai, 'chat_model', lambda **kwargs:LocalModel())
    draft = client.post(f'/api/rooms/{room_id}/rag', headers=interviewer, json={'document_id':document_id,'query':'Python'})
    assert draft.status_code == 200, draft.text
    assert draft.json()['sources'][0]['page'] == 1
    assert draft.json()['sources'][0]['filename'] == 'notes.pdf'
    assert client.post(f'/api/rooms/{room_id}/rag', headers=candidate, json={'document_id':document_id,'query':'Python'}).status_code == 403
    other_id, other_interviewer, _ = room_pair()
    assert client.get(f'/api/rooms/{other_id}/documents/{document_id}', headers=other_interviewer).status_code == 404
    assert client.get(f'/api/rooms/{room_id}/documents/{document_id}', headers=interviewer).status_code == 200
    assert client.delete(f'/api/rooms/{room_id}/documents/{document_id}', headers=interviewer).status_code == 404
    assert client.delete(f'/api/rooms/{room_id}/documents/{document_id}', headers=candidate).status_code == 200


def test_background_deadline_expiry_without_room_requests():
    room_id, interviewer, candidate = room_pair()
    client.post(f'/api/rooms/{room_id}/start', headers=interviewer)
    with SessionLocal() as db:
        room = db.get(PeerRoom, room_id); room.started_at = time.time() - 70; db.commit()
    with TestClient(main.app):
        time.sleep(1.2)
        with SessionLocal() as db:
            assert db.get(PeerRoom, room_id).status == 'completed'

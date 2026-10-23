"""API smoke tests without Ollama. Run with a TEST DATABASE, not production data."""
from fastapi.testclient import TestClient
from backend.app import main
from backend.verification_helpers import registration
import pytest

client = TestClient(main.app)

def fake_flow(state):
    if state.get('answer'):
        return {'done': state['current_position'] >= state['question_limit'],
                'difficulty': 'medium',
                'next_question': 'What is a database index?',
                'evaluation': {'correctness': 80, 'relevance': 90, 'clarity': 85,
                               'examples': 60, 'overall': 80.5,
                               'feedback': 'Good answer; add an example.',
                               'improved_answer': 'A list is mutable; a tuple is immutable.'}}
    return {'next_question': 'How are lists and tuples different?'}

def test_complete_interview(monkeypatch):
    monkeypatch.setattr(main, 'run_flow', fake_flow)
    register = client.post('/api/register', json=registration())
    assert register.status_code == 201, register.text
    token = register.json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    start = client.post('/api/interviews/start', json={
        'role': 'Python Backend Developer', 'kind': 'technical',
        'difficulty': 'easy', 'question_limit': 1}, headers=headers)
    assert start.status_code == 201, start.text
    interview_id = start.json()['interview_id']
    answer = client.post(f'/api/interviews/{interview_id}/answer',
                         json={'text': 'Lists can be changed but tuples cannot.'}, headers=headers)
    assert answer.status_code == 200, answer.text
    assert answer.json()['status'] == 'completed'
    report = client.get(f'/api/interviews/{interview_id}/report', headers=headers)
    assert report.status_code == 200
    assert report.json()['average_score'] == 80.5
    assert TestClient(main.app).get(f'/api/interviews/{interview_id}/report').status_code == 401


def test_custom_interview_is_persisted_and_used_through_completion(monkeypatch):
    states = []
    def capture(state):
        states.append(dict(state))
        return fake_flow(state)
    monkeypatch.setattr(main, 'run_flow', capture)
    register = client.post('/api/register', json=registration())
    headers = {'Authorization': 'Bearer ' + register.json()['token']}
    start = client.post('/api/interviews/start', headers=headers, json={
        'role': 'Backend developer', 'kind': 'custom', 'custom_kind': '  System design & databases  ', 'question_limit': 2})
    assert start.status_code == 201, start.text
    identifier = start.json()['interview_id']
    detail = client.get(f'/api/interviews/{identifier}', headers=headers).json()
    assert detail['kind'] == 'custom' and detail['custom_kind'] == 'System design & databases'
    assert detail['question_limit'] == 2
    for status in ('active', 'completed'):
        answer = client.post(f'/api/interviews/{identifier}/answer', headers=headers,
                             json={'text': 'Use indexes and partition data to scale reads.'})
        assert answer.status_code == 200 and answer.json()['status'] == status
    assert len(states) == 3 and all(s['kind'] == 'System design & databases' for s in states)
    report = client.get(f'/api/interviews/{identifier}/report', headers=headers).json()
    assert report['custom_kind'] == 'System design & databases' and report['count'] == 2
    assert client.get('/api/interviews', headers=headers).json()[0]['custom_kind'] == report['custom_kind']


@pytest.mark.parametrize('count', [1, 7, 13, 50])
def test_custom_question_count_boundaries(count):
    assert main.StartBody(role='Python developer', question_limit=count).question_limit == count


@pytest.mark.parametrize('body', [
    {'question_limit': 0}, {'question_limit': 51}, {'question_limit': 1.5},
    {'question_limit': True}, {'question_limit': '7'}, {'kind': 'custom'},
    {'kind': 'custom', 'custom_kind': '  '}, {'kind': 'custom', 'custom_kind': 'ab'},
    {'kind': 'custom', 'custom_kind': 'x' * 101}, {'kind': 'custom', 'custom_kind': 'System\ndesign'},
])
def test_invalid_custom_options_are_rejected(body):
    with pytest.raises(ValueError): main.StartBody(role='Python developer', **body)


def test_switch_to_standard_kind_discards_stale_custom_value():
    body = main.StartBody(role='Python developer', kind='hr', custom_kind='System design')
    assert body.custom_kind is None

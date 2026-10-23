"""Exercise real MySQL-backed HTTP APIs, Ollama, Docker and optional speech."""
import io
from pathlib import Path

import requests
from .verification_helpers import registration
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

BASE = 'http://127.0.0.1:8000/api'


def pdf():
    writer = PdfWriter(); page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 50 700 Td (Python skills: a dictionary maps unique keys to values and supports fast lookup.) Tj 0 -20 Td (Education: computer science. Projects: Python interview app. Experience: internship.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO(); writer.write(output); return output.getvalue()


def main():
    headers = []
    def call(method, path, who=0, **kwargs):
        response = requests.request(method, BASE + path, headers=headers[who] if headers else {}, timeout=240, **kwargs)
        if not response.ok:
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}: {response.text[:300]}')
        return response.json()
    try:
        for _ in range(2):
            result = call('POST', '/register', json=registration())
            headers.append({'Authorization':'Bearer '+result['token']})
        room = call('POST', '/rooms', json={'topic':'Python dictionary skills','duration_seconds':900})
        path = '/rooms/' + room['id']
        call('POST', path+'/join', who=1)
        uploaded = call('POST', path+'/documents', who=1, files={'file':('runtime-resume.pdf',pdf(),'application/pdf')}, data={'kind':'resume'})
        assert uploaded['analysis']['score'] >= 0
        print('PASS: MySQL registration, room join, PDF extraction and resume analysis.', flush=True)
        call('POST', path+'/start')
        draft = call('POST', path+'/rag', json={'document_id':uploaded['id'],'query':'Python dictionary lookup'})
        assert draft['question'] and draft['suggested_answer'] and draft['sources'][0]['page'] == 1
        candidate = call('GET', path, who=1)
        assert not any(e['kind']=='rag_draft' for e in candidate['events'])
        print('PASS: real local embeddings, LangChain/Ollama RAG and draft privacy.', flush=True)
        call('POST', path+'/questions', json={'text':draft['question']})
        call('POST', path+'/problem', json={'title':'Sum', 'statement':'Read two integers and print their sum.', 'tests':[{'input':'2 3\n','expected':'5'},{'input':'-1 4\n','expected':'3'}]})
        result = call('POST', path+'/execute', who=1, json={'source':'a,b=map(int,input().split());print(a+b)','final':True})
        assert result['passed'] == result['total'] == 2
        print('PASS: candidate-only real Docker execution, tests and final submission.', flush=True)
        audio = Path('data/speech-sample.wav')
        if audio.exists():
            with audio.open('rb') as file:
                metrics = call('POST', path+'/communication', who=1, data={'consent':'true'}, files={'file':('sample.wav',file,'audio/wav')})
            assert metrics['words'] > 5
            print('PASS: consented real Faster-Whisper transcription and communication metrics.', flush=True)
        else:
            print('NOT TESTED: speech (provide data/speech-sample.wav).', flush=True)
        call('POST', path+'/end')
        call('POST', path+'/feedback', json={'technical':80,'problem_solving':80,'communication':80,'strengths':'Clear examples','improvements':'Practise complexity analysis'})
        report = call('GET', path+'/report', who=1)
        assert report['scores']['coding'] == 100 and report['overall_score'] is not None
        print('PASS: report generation, combined scores and shared results.', flush=True)
        solo = call('POST', '/interviews/start', json={'role':'Python Developer','kind':'technical','difficulty':'easy','question_limit':1})
        result = call('POST', f"/interviews/{solo['interview_id']}/answer", json={'text':'A Python dictionary maps unique keys to values and supports average constant time lookup.'})
        assert result['status'] == 'completed'
        print('PASS: real LangGraph solo question generation and AI evaluation.', flush=True)
    finally:
        for auth in headers:
            response = requests.delete(BASE+'/me', headers=auth, timeout=20)
            if not response.ok:
                print('Test account cleanup failed:',response.status_code)
    print('Runtime test accounts and owned files removed.', flush=True)


if __name__ == '__main__':
    main()

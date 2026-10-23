"""FastAPI backend for InterviewAce AI (local, no paid AI API)."""
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pypdf import PdfReader
from .config import ROOT, UPLOAD_DIR
from .db import Base, engine, get_db
from .graph import run_flow
from .models import Answer, Interview, Question, Resume, User
from .security import check_password, current_user, hash_password, make_token, session_cookie
from .peer import router as peer_router
from .models import RecoveryCode, RevokedToken, TokenVersion, LoginSession
from .validation import RegisterBody, ProfileBody, ResetBody, ChangePasswordBody
from .config import SESSION_COOKIE
from .schema import upgrade
from . import operations
import time
import secrets
import hashlib
import jwt
from fastapi.security import HTTPAuthorizationCredentials
from .security import bearer
from .config import JWT_SECRET
from contextlib import asynccontextmanager, suppress
import asyncio
from . import peer
from .db import SessionLocal
from .models import Document, PeerRoom

@asynccontextmanager
async def lifespan(application):
    async def sweep_deadlines():
        while True:
            try:
                changed = []
                removed = []
                with SessionLocal() as db:
                    rooms = db.scalars(select(PeerRoom).where(PeerRoom.status == 'active')).all()
                    for room in rooms:
                        peer.expire(db, room)
                        if room.status == 'completed':
                            changed.append(room.id)
                    removed = peer.purge_scheduled_deletions(db)
                    db.execute(delete(LoginSession).where(LoginSession.expires_at < time.time()))
                    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < time.time()))
                    db.commit()
                for room_id in changed:
                    await peer.broadcast(room_id, {'type': 'refresh'})
                for room_id in removed:
                    await peer.broadcast(room_id, {'type': 'deleted'})
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Room deadline sweep failed')
            await asyncio.sleep(1)
    task = asyncio.create_task(sweep_deadlines())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

# EmailStr uses email-validator; requirements.txt includes it.
Base.metadata.create_all(bind=engine)
upgrade(engine)
app = FastAPI(title='InterviewAce AI', version='3.3.0', lifespan=lifespan)
operations.install(app)
app.include_router(peer_router)
FRONTEND = ROOT / 'frontend'
app.mount('/assets', StaticFiles(directory=str(FRONTEND)), name='assets')

class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class StartBody(BaseModel):
    role: str = Field(min_length=3, max_length=100)
    kind: str = Field(default='technical', pattern='^(technical|hr|mixed|custom)$')
    custom_kind: str | None = Field(default=None, max_length=100)
    difficulty: str = Field(default='medium', pattern='^(easy|medium|hard)$')
    question_limit: int = Field(default=5, ge=1, le=50, strict=True)
    resume_id: int | None = None

    @model_validator(mode='after')
    def validate_custom_type(self):
        if self.kind == 'custom':
            value = (self.custom_kind or '').strip()
            if len(value) < 3 or any(not character.isprintable() for character in value):
                raise ValueError('Custom interview type must contain 3–100 printable characters.')
            self.custom_kind = value
        else:
            self.custom_kind = None
        return self

class AnswerBody(BaseModel):
    text: str = Field(min_length=2, max_length=5000)

def owned_interview(db: Session, user_id: int, interview_id: int) -> Interview:
    interview = db.scalar(select(Interview).where(
        Interview.id == interview_id, Interview.user_id == user_id))
    if not interview:
        raise HTTPException(404, 'Interview not found.')
    return interview

def safe_ai_call(state: dict) -> dict:
    try:
        return run_flow(state)
    except Exception as exc:
        # Do not leak internal files, prompts, URLs or credentials to a client.
        raise HTTPException(503, 'Local AI is unavailable. Check Ollama and model downloads.') from exc

def question_payload(question: Question | None):
    if not question:
        return None
    return {'id': question.id, 'number': question.position, 'text': question.text,
            'difficulty': question.difficulty}

@app.get('/')
def home():
    return FileResponse(str(FRONTEND / 'index.html'))

@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    try:
        db.scalar(select(1))
    except Exception as exc:
        raise HTTPException(503, 'Database is unavailable.') from exc
    return {'status': 'ok', 'database': db.bind.dialect.name,
            'ai_mode': 'local Ollama', 'version': app.version}

@app.get('/api/live')
def live():
    return {'status': 'alive', 'version': app.version}

@app.get('/api/monitoring')
def monitoring(user: User = Depends(current_user)):
    return {'uptime_seconds': round(time.time() - operations.started),
            'responses_by_status': dict(operations.counts), 'active_socket_connections': sum(len(c) for c in peer.connections.values()),
            'scope': 'Aggregate counters for this single API process. No personal data.'}

@app.get('/robots.txt', include_in_schema=False)
def robots():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse('User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /docs\nDisallow: /redoc\n')

@app.post('/api/register', status_code=201)
def register(body: RegisterBody, request: Request, response: Response, db: Session = Depends(get_db)):
    email = str(body.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email already registered.')
    user = User(name=body.first_name + ' ' + body.last_name, first_name=body.first_name,
                last_name=body.last_name, contact_number=body.contact_number, email=email,
                password_hash=hash_password(body.password))
    db.add(user)
    recovery = secrets.token_urlsafe(24)
    try:
        db.flush()
        db.add(RecoveryCode(user_id=user.id, code_hash=hash_password(recovery)))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Registration could not be completed.')
    db.refresh(user)
    token = make_token(user.id)
    session_cookie(response, token)
    result = {'name': user.name, 'recovery_code': recovery}
    if request.headers.get('x-requested-with') != 'InterviewAce':
        result['token'] = token
    return result

@app.post('/api/login')
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(401, 'Incorrect email or password.')
    token = make_token(user.id)
    session_cookie(response, token)
    result = {'name': user.name}
    if request.headers.get('x-requested-with') != 'InterviewAce':
        result['token'] = token
    return result

@app.get('/api/me')
def me(user: User = Depends(current_user)):
    return {'id': user.id, 'name': user.name, 'first_name': user.first_name,
            'last_name': user.last_name, 'contact_number': user.contact_number, 'email': user.email}

@app.patch('/api/me')
def update_profile(body: ProfileBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = body.first_name + ' ' + body.last_name
    if len(name) > 100:
        raise HTTPException(422, 'Combined name must be at most 100 characters.')
    user.first_name = body.first_name; user.last_name = body.last_name
    user.contact_number = body.contact_number; user.name = name; db.commit()
    return {'name': user.name, 'first_name': user.first_name, 'last_name': user.last_name, 'contact_number': user.contact_number}

@app.post('/api/logout')
def logout(request: Request, response: Response, user: User = Depends(current_user), credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    token = credentials.credentials if credentials else request.cookies.get(SESSION_COOKIE)
    payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    db.merge(RevokedToken(digest=hashlib.sha256(token.encode()).hexdigest(), expires_at=payload['exp']))
    db.execute(delete(LoginSession).where(LoginSession.digest == hashlib.sha256(token.encode()).hexdigest()))
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path='/', samesite='strict')
    return {'logged_out': True}

@app.get('/api/sessions')
def sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(LoginSession).where(LoginSession.user_id == user.id, LoginSession.expires_at > time.time())).all()
    return [{'id': s.digest, 'created_at': s.created_at, 'last_seen_at': s.last_seen_at, 'expires_at': s.expires_at} for s in rows]

@app.post('/api/change-password')
def change_password(body: ChangePasswordBody, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not check_password(body.current_password, user.password_hash):
        raise HTTPException(400, 'Current password is incorrect.')
    user.password_hash = hash_password(body.new_password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.commit()
    session_cookie(response, make_token(user.id))
    return {'message': 'Password changed. Other devices are now logged out.'}

@app.delete('/api/sessions')
def end_sessions(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id)); db.commit()
    response.delete_cookie(SESSION_COOKIE, path='/', samesite='strict')
    return {'logged_out_all_devices': True}

@app.post('/api/password-reset')
def reset_password(body: ResetBody, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(body.email).lower()).with_for_update())
    recovery = db.get(RecoveryCode, user.id) if user else None
    if not recovery or not check_password(body.recovery_code, recovery.code_hash):
        raise HTTPException(400, 'Email or recovery code is incorrect.')
    user.password_hash = hash_password(body.new_password)
    code = secrets.token_urlsafe(24)
    recovery.code_hash = hash_password(code)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    version = db.get(TokenVersion, user.id)
    if version:
        version.version += 1
    else:
        db.add(TokenVersion(user_id=user.id, version=1))
    db.commit()
    return {'recovery_code': code, 'message': 'Password reset. Save your new recovery code and log in.'}

class RecoveryBody(BaseModel):
    password: str = Field(min_length=8, max_length=128)

@app.post('/api/recovery-code')
def recovery_code(body: RecoveryBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not check_password(body.password, user.password_hash):
        raise HTTPException(401, 'Incorrect password.')
    code = secrets.token_urlsafe(24)
    db.merge(RecoveryCode(user_id=user.id, code_hash=hash_password(code)))
    db.commit()
    return {'recovery_code': code}

@app.post('/api/resumes', status_code=201)
async def upload_resume(file: UploadFile = File(...),
                        user: User = Depends(current_user),
                        db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, 'Upload a PDF file.')
    content = await file.read(3 * 1024 * 1024 + 1)
    if len(content) > 3 * 1024 * 1024 or not content.startswith(b'%PDF-'):
        raise HTTPException(400, 'PDF must be valid and 3 MB or smaller.')
    target = UPLOAD_DIR / f'{uuid4().hex}.pdf'
    target.write_bytes(content)
    try:
        reader = PdfReader(str(target))
        if len(reader.pages) > 10:
            raise ValueError('Resume is too long.')
        extracted = '\n'.join((page.extract_text() or '') for page in reader.pages)[:10000]
        if not extracted.strip():
            raise ValueError('No selectable text detected (scan/OCR not included).')
        resume = Resume(user_id=user.id, filename=Path(file.filename).name[:255],
                        stored_path=str(target), extracted_text=extracted)
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return {'id': resume.id, 'filename': resume.filename,
                'preview': extracted[:300]}
    except Exception:
        db.rollback()
        target.unlink(missing_ok=True)
        raise HTTPException(400, 'PDF text could not be extracted. Try a text-based PDF under 10 pages.')

@app.get('/api/resumes')
def list_resumes(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Resume).where(Resume.user_id == user.id)
                      .order_by(Resume.id.desc())).all()
    return [{'id': r.id, 'filename': r.filename} for r in rows]

@app.delete('/api/resumes/{resume_id}')
def delete_resume(resume_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if not resume:
        raise HTTPException(404, 'Resume not found.')
    path = Path(resume.stored_path)
    db.delete(resume)
    db.commit()
    path.unlink(missing_ok=True)
    return {'deleted': True}

@app.post('/api/interviews/start', status_code=201)
def start_interview(body: StartBody, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    resume_text = ''
    if body.resume_id is not None:
        resume = db.scalar(select(Resume).where(
            Resume.id == body.resume_id, Resume.user_id == user.id))
        if not resume:
            raise HTTPException(404, 'Resume not found.')
        resume_text = resume.extracted_text[:2500]
    session = Interview(user_id=user.id, resume_id=body.resume_id,
                        role=body.role.strip(), kind=body.kind, custom_kind=body.custom_kind,
                        difficulty=body.difficulty, question_limit=body.question_limit)
    try:
        state = safe_ai_call({'role': session.role, 'kind': session.custom_kind or session.kind,
                              'difficulty': session.difficulty, 'asked': [],
                              'resume': resume_text, 'current_position': 0,
                              'question_limit': session.question_limit})
        db.add(session)
        db.flush()
        question = Question(interview_id=session.id, position=1,
                            text=state['next_question'], difficulty=session.difficulty)
        db.add(question)
        db.commit()
        db.refresh(question)
    except Exception:
        db.rollback()
        raise
    return {'interview_id': session.id, 'status': 'active',
            'question': question_payload(question)}

@app.get('/api/interviews')
def list_interviews(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Interview).where(Interview.user_id == user.id)
                      .order_by(Interview.id.desc())).all()
    return [{'id': r.id, 'role': r.role, 'kind': r.kind, 'custom_kind': r.custom_kind, 'status': r.status,
             'question_limit': r.question_limit} for r in rows]

@app.get('/api/interviews/{interview_id}')
def interview_details(interview_id: int, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    session = owned_interview(db, user.id, interview_id)
    questions = db.scalars(select(Question).where(Question.interview_id == session.id)
                           .order_by(Question.position)).all()
    answered = []
    current = None
    for q in questions:
        a = db.scalar(select(Answer).where(Answer.question_id == q.id))
        if a:
            answered.append({'question': q.text, 'answer': a.text,
                             'score': a.overall, 'feedback': a.feedback})
        else:
            current = question_payload(q)
    return {'interview_id': session.id, 'role': session.role, 'kind': session.kind,
            'custom_kind': session.custom_kind, 'status': session.status,
            'question_limit': session.question_limit, 'answered': answered, 'current': current}

@app.post('/api/interviews/{interview_id}/transcribe')
async def transcribe_answer(interview_id: int, consent: bool = Form(...), file: UploadFile = File(...),
                            user: User = Depends(current_user), db: Session = Depends(get_db)):
    interview = owned_interview(db, user.id, interview_id)
    if interview.status != 'active':
        raise HTTPException(409, 'This interview has already finished.')
    if not consent:
        raise HTTPException(400, 'Consent is required before audio transcription.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.webm', '.wav', '.ogg', '.mp3', '.m4a'}:
        raise HTTPException(400, 'Upload a supported audio recording.')
    content = await file.read(15 * 1024 * 1024 + 1)
    if not content or len(content) > 15 * 1024 * 1024:
        raise HTTPException(400, 'Audio must be nonempty and at most 15 MB.')
    path = UPLOAD_DIR / (uuid4().hex + suffix)
    path.write_bytes(content)
    try:
        result = await run_in_threadpool(peer.transcribe, path, True)
    except Exception as exc:
        raise HTTPException(503, 'Local transcription failed. Check the speech dependencies and Whisper model; you can still type your answer.') from exc
    finally:
        path.unlink(missing_ok=True)
    # Return a draft only; no answer or raw recording is persisted here.
    return {'transcript': result['transcript'][:5000], 'metrics': result['metrics']}

@app.post('/api/interviews/{interview_id}/answer')
def submit_answer(interview_id: int, body: AnswerBody,
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = owned_interview(db, user.id, interview_id)
    if session.status != 'active':
        raise HTTPException(409, 'Interview has already finished.')
    questions = db.scalars(select(Question).where(Question.interview_id == session.id)
                           .order_by(Question.position)).all()
    current = questions[-1]
    if db.scalar(select(Answer).where(Answer.question_id == current.id)):
        raise HTTPException(409, 'Question already answered.')
    resume = db.get(Resume, session.resume_id) if session.resume_id else None
    state = {'role': session.role, 'kind': session.custom_kind or session.kind,
             'difficulty': current.difficulty, 'question': current.text,
             'answer': body.text, 'asked': [q.text for q in questions],
             'resume': resume.extracted_text[:2500] if resume else '',
             'current_position': current.position, 'question_limit': session.question_limit}
    result = safe_ai_call(state)
    score = result['evaluation']
    answer = Answer(question_id=current.id, text=body.text,
                    correctness=score['correctness'], relevance=score['relevance'],
                    clarity=score['clarity'], examples=score['examples'],
                    overall=score['overall'], feedback=score['feedback'],
                    improved_answer=score['improved_answer'])
    db.add(answer)
    next_question = None
    if result['done']:
        session.status = 'completed'
    else:
        next_question = Question(interview_id=session.id,
                                 position=current.position + 1,
                                 text=result['next_question'],
                                 difficulty=result['difficulty'])
        db.add(next_question)
    db.commit()
    if next_question:
        db.refresh(next_question)
    return {'evaluation': score, 'status': session.status,
            'next_question': question_payload(next_question)}

@app.get('/api/interviews/{interview_id}/report')
def report(interview_id: int, user: User = Depends(current_user),
           db: Session = Depends(get_db)):
    session = owned_interview(db, user.id, interview_id)
    if session.status != 'completed':
        raise HTTPException(409, 'Finish the interview to see the report.')
    questions = db.scalars(select(Question).where(Question.interview_id == session.id)
                           .order_by(Question.position)).all()
    items = []
    for q in questions:
        ans = db.scalar(select(Answer).where(Answer.question_id == q.id))
        if ans:
            items.append({'question': q.text, 'answer': ans.text, 'score': ans.overall,
                          'feedback': ans.feedback, 'improved_answer': ans.improved_answer})
    average = round(sum(x['score'] for x in items) / len(items), 1) if items else 0
    return {'role': session.role, 'kind': session.kind, 'custom_kind': session.custom_kind,
            'average_score': average, 'count': len(items), 'items': items,
            'disclaimer': 'Practice feedback only, not a hiring assessment.'}

@app.delete('/api/interviews/{interview_id}')
def delete_interview(interview_id: int, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    session = owned_interview(db, user.id, interview_id)
    db.delete(session)
    db.commit()
    return {'deleted': True}

@app.delete('/api/me')
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    resumes = db.scalars(select(Resume).where(Resume.user_id == user.id)).all()
    paths = [Path(r.stored_path) for r in resumes]
    owned_rooms = select(PeerRoom.id).where(PeerRoom.interviewer_id == user.id)
    documents = db.scalars(select(Document).where(
        (Document.owner_id == user.id) | Document.room_id.in_(owned_rooms))).all()
    paths.extend(Path(d.stored_path) for d in documents)
    db.delete(user)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)
    return {'deleted': True}

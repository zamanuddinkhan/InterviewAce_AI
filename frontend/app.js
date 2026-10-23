'use strict';
const $ = id => document.getElementById(id);
// Authentication lives in an HttpOnly cookie; this flag controls UI visibility only.
sessionStorage.removeItem('interviewace_token');
let token = '';
let registerMode = false;
let activeInterviewId = null;
let busy = false;
let currentPage = 'home', workspaceReady = null;
async function showPage(page = 'home') {
  if (!token && page !== 'home') { $('authCard').scrollIntoView({behavior:'smooth'}); $('email').focus(); return; }
  const previous = currentPage;
  currentPage = ['home','solo','peer','history','profile'].includes(page) ? page : 'home';
  if (previous === 'peer' && currentPage !== 'peer') Peer.close();
  if (previous === 'solo' && currentPage !== 'solo') Solo.stopMedia();
  updatePanels(false);
  if (token && currentPage !== 'home') {
    try { await workspaceReady; Peer.page(currentPage); }
    catch(e) { toast(e.message,true); }
  }
  $('mainContent').scrollIntoView({behavior:'smooth',block:'start'});
}
document.addEventListener('click', event => {
  const link = event.target.closest('[data-page]');
  if (link) { event.preventDefault(); showPage(link.dataset.page); }
});
function connectionStatus() { $('connectionStatus').classList.toggle('hidden', navigator.onLine); }
window.addEventListener('online', connectionStatus); window.addEventListener('offline', connectionStatus); connectionStatus();

function toast(message, error = false) {
  const notice = $('notice');
  notice.textContent = message;
  notice.className = 'notice' + (error ? ' error' : '');
  setTimeout(() => { if (notice.textContent === message) notice.className = 'notice hidden'; }, 5500);
}
async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  headers['X-Requested-With'] = 'InterviewAce';
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  let response;
  try { response = await fetch('/api' + path, { ...options, headers, credentials:'same-origin', signal:options.signal || AbortSignal.timeout(180000) }); }
  catch(e) { throw new Error(e.name === 'TimeoutError' ? 'The request timed out. Check saved progress before retrying.' : 'Cannot reach the server. Check your connection and try again.'); }
  let data;
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) {
    if (response.status === 401 && token) { token = ''; Peer.close(); activeInterviewId = null; resetChat(); updatePanels(); }
    const error = new Error(Array.isArray(data.detail) ? data.detail.map(e => e.msg).join('; ') : (data.detail || `Request failed: ${response.status}`));
    error.details = data.detail; error.status = response.status; error.requestId = response.headers.get('X-Request-ID'); throw error;
  }
  return data;
}
function setBusy(value) {
  busy = value;
  document.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = value; });
}
function updatePanels(load = true) {
  $('authPanel').classList.toggle('hidden', !!token && currentPage !== 'home');
  $('authCard').classList.toggle('hidden', !!token);
  $('memberHome').classList.toggle('hidden', !token);
  $('workspace').classList.toggle('hidden', !token || currentPage === 'home');
  $('logoutBtn').classList.toggle('hidden', !token);
  document.querySelectorAll('.guest-only').forEach(item => item.classList.toggle('hidden', !!token));
  document.querySelectorAll('.member-only').forEach(item => item.classList.toggle('hidden', !token));
  if (!token) { currentPage = 'home'; workspaceReady = null; $('userBadge').textContent = 'Runs with free local AI'; Solo.stopMedia(); }
  document.querySelectorAll('#studioNav [data-page]').forEach(link => {
    if (link.dataset.page === currentPage) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  if (token && load) {
    loadResumes(); loadHistory();
    workspaceReady = Peer.show().then(profile => {
      Solo.profile(profile);
      $('memberWelcome').textContent = `Welcome back, ${profile.first_name || profile.name}!`;
      Peer.page(currentPage);
    });
    workspaceReady.catch(e => toast(e.message, true));
  }
}
function bubble(who, content, variant = 'ai') {
  const el = document.createElement('div');
  el.className = `bubble ${variant}`;
  const tag = document.createElement('span');
  tag.className = 'who';
  tag.textContent = who;
  const text = document.createElement('span');
  text.textContent = content;
  el.append(tag, text);
  $('conversation').appendChild(el);
  $('conversation').scrollTop = $('conversation').scrollHeight;
}
function resetChat() {
  Solo.reset();
  $('conversation').replaceChildren();
  $('report').classList.add('hidden');
  $('answerForm').classList.add('hidden');
}
function setQuestion(question) {
  if (!question) return;
  bubble(`AI INTERVIEWER • QUESTION ${question.number}`, question.text);
  $('sessionMeta').textContent = `Question ${question.number} • ${question.difficulty}`;
  $('statusBadge').textContent = 'In progress';
  $('answerForm').classList.remove('hidden');
  $('answerText').value = '';
  Solo.question(question.text);
}
$('authToggle').addEventListener('click', () => {
  registerMode = !registerMode;
  $('authTitle').textContent = registerMode ? 'Create an account' : 'Welcome back';
  $('authDescription').textContent = registerMode ? 'A few details, then your next chapter begins.' : 'Sign in and pick up where you left off.';
  $('authSubmit').textContent = registerMode ? 'Create my account' : 'Log in';
  ['registrationFields','confirmLabel','passwordHelp'].forEach(id => $(id).classList.toggle('hidden', !registerMode));
  ['firstName','lastName','contactNumber','confirmPassword'].forEach(id => { $(id).required = registerMode; $(id).disabled = !registerMode; });
  $('password').minLength = registerMode ? 12 : 1;
  $('password').autocomplete = registerMode ? 'new-password' : 'current-password';
  $('password').placeholder = registerMode ? 'Create a unique passphrase' : 'Enter your password';
  $('confirmPassword').setCustomValidity(''); $('authError').classList.add('hidden');
  $('authPrompt').textContent = registerMode ? 'Already registered?' : 'New here?';
  $('authToggle').textContent = registerMode ? 'Log in' : 'Create an account';
});
const passwordChecks = value => ({length:value.length >= 12 && value.length <= 128, upper:/\p{Lu}/u.test(value), lower:/\p{Ll}/u.test(value), number:/\p{Nd}/u.test(value), symbol:/[^\p{L}\p{N}\s]/u.test(value)});
function checkPassword() {
  const checks = passwordChecks($('password').value), count = Object.values(checks).filter(Boolean).length;
  $('passwordStrength').value = count;
  $('strengthLabel').textContent = count === 5 ? 'All requirements met — keep it unique' : `${count} of 5 password requirements met`;
  $('passwordRules').querySelectorAll('li').forEach(item => item.classList.toggle('met', checks[item.dataset.rule]));
  const mismatch = registerMode && $('confirmPassword').value && $('confirmPassword').value !== $('password').value;
  $('confirmPassword').setCustomValidity(mismatch ? 'Passwords do not match.' : '');
  $('confirmPasswordError').textContent = mismatch ? 'Passwords do not match.' : '';
}
$('password').addEventListener('input', checkPassword); $('confirmPassword').addEventListener('input', checkPassword);
$('togglePassword').onclick = () => { const show = $('password').type === 'password'; $('password').type = show ? 'text' : 'password'; $('togglePassword').textContent = show ? 'Hide' : 'Show'; $('togglePassword').setAttribute('aria-pressed', String(show)); $('togglePassword').setAttribute('aria-label', show ? 'Hide password' : 'Show password'); };
function fieldErrors(error) {
  document.querySelectorAll('#authForm .field-error').forEach(e => e.textContent = '');
  const fields = {first_name:'firstName',last_name:'lastName',contact_number:'contactNumber',email:'email',password:'password',confirm_password:'confirmPassword'};
  if (Array.isArray(error.details)) error.details.forEach(item => { const id = fields[item.loc?.at(-1)]; if (id) $(id+'Error').textContent = item.msg; });
  $('authError').textContent = error.message; $('authError').classList.remove('hidden');
}
$('authForm').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return; setBusy(true); $('authError').classList.add('hidden');
  try {
    const body = { email: $('email').value, password: $('password').value };
    if (registerMode) Object.assign(body, {first_name:$('firstName').value,last_name:$('lastName').value,contact_number:$('contactNumber').value,confirm_password:$('confirmPassword').value});
    const result = await api(registerMode ? '/register' : '/login', {
      method: 'POST', body: JSON.stringify(body),
    });
    token = 'cookie';
    currentPage = 'home';
    $('password').value = ''; $('confirmPassword').value = ''; checkPassword();
    $('userBadge').textContent = result.name;
    updatePanels();
    if (result.recovery_code) showRecovery(result.recovery_code);
    toast('Welcome, ' + result.name + '!');
  } catch (error) { fieldErrors(error); }
  finally { setBusy(false); }
});
$('logoutBtn').addEventListener('click', async () => {
  try { await api('/logout', {method:'POST'}); } catch (e) { toast(e.message, true); return; }
  Peer.close();
  token = ''; sessionStorage.removeItem('interviewace_token');
  activeInterviewId = null; resetChat(); updatePanels();
});

function showRecovery(code) {
  const dialog = document.createElement('dialog');
  const title = document.createElement('h2'); title.textContent = 'Save your password recovery code';
  const text = document.createElement('p'); text.textContent = 'This one-time code resets your password without an email service. Keep it private. It is shown only now.';
  const value = document.createElement('pre'); value.textContent = code;
  const close = document.createElement('button'); close.textContent = 'I saved my code'; close.className = 'primary'; close.onclick = () => { dialog.close(); dialog.remove(); };
  dialog.append(title, text, value, close); document.body.append(dialog); dialog.showModal();
}
const resetDetails = document.createElement('details');
resetDetails.innerHTML = '<summary>Forgot your password?</summary><form id="resetPasswordForm"><label>Email<input id="resetEmail" type="email" autocomplete="email" required></label><label>Private recovery code<input id="resetCode" autocomplete="off" required minlength="10"></label><label>New password<input id="resetNewPassword" type="password" autocomplete="new-password" required minlength="12" maxlength="128"></label><p class="field-help">Use 12–128 characters, uppercase, lowercase, a number and a symbol. Avoid common passwords and reused phrases.</p><label>Confirm new password<input id="resetConfirmPassword" type="password" autocomplete="new-password" required maxlength="128"></label><button class="secondary full" type="submit">Reset password</button></form>';
$('authCard').append(resetDetails);
$('resetPasswordForm').onsubmit = async event => {
  event.preventDefault(); setBusy(true);
  try { const result = await api('/password-reset', {method:'POST', body:JSON.stringify({email:$('resetEmail').value,recovery_code:$('resetCode').value,new_password:$('resetNewPassword').value,confirm_password:$('resetConfirmPassword').value})}); showRecovery(result.recovery_code); $('resetPasswordForm').reset(); toast(result.message); }
  catch(e) { toast(e.message,true); } finally { setBusy(false); }
};
async function loadResumes() {
  try {
    const data = await api('/resumes');
    const select = $('resumeSelect');
    const selected = select.value;
    select.replaceChildren(new Option('No resume', ''));
    data.forEach(r => select.add(new Option(r.filename, String(r.id))));
    if (data.some(r => String(r.id) === selected)) select.value = selected;
  } catch (error) { toast(error.message, true); }
}
async function uploadResume() {
  const file = $('resumeFile').files[0];
  if (!file) { toast('Choose a PDF resume first.', true); return; }
  const form = new FormData(); form.append('file', file);
  setBusy(true);
  try { const resume = await api('/resumes', { method: 'POST', body: form });
    toast('Resume uploaded and text extracted.'); $('resumeFile').value = '';
    await loadResumes();
    $('resumeSelect').value = String(resume.id);
  } catch (error) { toast(error.message, true); }
  finally { setBusy(false); }
}
$('uploadResume').addEventListener('click', uploadResume);
function customPracticeOptions() {
  for (const [select, label, input] of [['kind','customKindLabel','customKind'], ['questionLimit','customQuestionLabel','customQuestionLimit']]) {
    const custom = $(select).value === 'custom';
    $(label).classList.toggle('hidden', !custom); $(input).disabled = !custom; $(input).required = custom;
  }
}
$('kind').addEventListener('change', customPracticeOptions);
$('questionLimit').addEventListener('change', customPracticeOptions);
customPracticeOptions();
$('customKind').addEventListener('input', () => $('customKind').setCustomValidity(''));
$('startForm').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  if ($('kind').value === 'custom' && $('customKind').value.trim().length < 3) {
    $('customKind').setCustomValidity('Enter at least 3 characters for your interview focus.'); $('customKind').reportValidity(); return;
  }
  const body = { role: $('role').value.trim(), kind: $('kind').value,
    custom_kind: $('kind').value === 'custom' ? $('customKind').value.trim() : null,
    difficulty: $('difficulty').value, question_limit: Number($('questionLimit').value === 'custom' ? $('customQuestionLimit').value : $('questionLimit').value),
    resume_id: $('resumeSelect').value ? Number($('resumeSelect').value) : null };
  resetChat();
  $('sessionMeta').textContent = 'Generating a question on your computer...';
  $('sessionTitle').textContent = body.role;
  $('statusBadge').textContent = 'Loading';
  Solo.state('Preparing your question…');
  setBusy(true);
  try {
    const result = await api('/interviews/start', { method: 'POST', body: JSON.stringify(body) });
    activeInterviewId = result.interview_id;
    setQuestion(result.question);
    await loadHistory();
  } catch (error) { $('statusBadge').textContent = 'Unavailable'; Solo.state('Could not generate a question. Please retry.'); toast(error.message, true); }
  finally { setBusy(false); }
});
$('answerForm').addEventListener('submit', async event => {
  event.preventDefault(); if (busy || !activeInterviewId) return;
  const text = $('answerText').value.trim();
  if (!text) return;
  Solo.discardRecording();
  bubble('YOU', text, 'user');
  $('answerForm').classList.add('hidden');
  $('sessionMeta').textContent = 'Evaluating locally. This can take a little time...';
  Solo.state('Reviewing your answer…');
  setBusy(true);
  try {
    const result = await api(`/interviews/${activeInterviewId}/answer`, {
      method: 'POST', body: JSON.stringify({ text }),
    });
    bubble(`FEEDBACK • ${result.evaluation.overall}/100`,
      result.evaluation.feedback + '\n\nImproved answer: ' + result.evaluation.improved_answer,
      'feedback');
    if (result.status === 'completed') {
      $('statusBadge').textContent = 'Completed';
      const report = await api(`/interviews/${activeInterviewId}/report`);
      showReport(report);
      Solo.complete();
    } else { setQuestion(result.next_question); }
    await loadHistory();
  } catch (error) {
    toast(error.message + ' Refresh before retrying to check saved progress.', true);
    $('answerForm').classList.remove('hidden');
  } finally { setBusy(false); }
});
function showReport(report) {
  const panel = $('report'); panel.replaceChildren(); panel.classList.remove('hidden');
  const heading = document.createElement('h3'); heading.textContent = 'Your practice report';
  const score = document.createElement('div'); score.className = 'score';
  score.textContent = report.average_score + '/100';
  const summary = document.createElement('p'); summary.className = 'small';
  summary.textContent = `${report.count} answers reviewed. ${report.disclaimer}`;
  panel.append(heading, score, summary);
  report.items.forEach((item, index) => {
    const row = document.createElement('div'); row.className = 'report-card';
    row.textContent = `Q${index + 1} • ${item.score}/100 • ${item.feedback}`;
    panel.appendChild(row);
  });
  $('sessionMeta').textContent = 'Interview complete. Start another to practice more.';
}
async function loadHistory() {
  try {
    const data = await api('/interviews');
    const history = $('history'); history.replaceChildren();
    if (!data.length) { const p = document.createElement('p'); p.className = 'small';
      p.textContent = 'No interviews yet.'; history.append(p); return; }
    data.forEach(item => {
      const button = document.createElement('button'); button.className = 'history-item';
      button.textContent = `#${item.id} • ${item.role} (${item.status})`;
      button.addEventListener('click', () => openInterview(item.id)); history.append(button);
    });
  } catch (error) { toast(error.message, true); }
}
async function openInterview(id) {
  try {
    const data = await api(`/interviews/${id}`);
    activeInterviewId = id; resetChat();
    $('sessionTitle').textContent = data.role;
    $('statusBadge').textContent = data.status;
    data.answered.forEach(row => {
      bubble('AI INTERVIEWER', row.question);
      bubble('YOU', row.answer, 'user');
      bubble(`FEEDBACK • ${row.score}/100`, row.feedback, 'feedback');
    });
    if (data.current) setQuestion(data.current);
    if (data.status === 'completed') showReport(await api(`/interviews/${id}/report`));
  } catch (error) { toast(error.message, true); }
}
  api('/me').then(me => { token = 'cookie'; $('userBadge').textContent = me.name; updatePanels(); })
    .catch(() => { token = ''; sessionStorage.removeItem('interviewace_token'); updatePanels(); });

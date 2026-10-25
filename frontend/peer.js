'use strict';
window.Peer = (() => {
  let mounted = false, room = null, socket = null, stream = null, pc = null, recorder = null;
  let reconnect = null, codeDebounce = null, candidates = [], recordingChunks = [], lastStatus = '', refreshing = false, refreshAgain = false, connecting = false;
  let mounting = null, roomTab = 'live', devices = null, makingOffer = false, ignoreOffer = false, problemDraftActive = false, syncedProblemState = '';
  let remoteStream = null, previewUrl = null;
  const deletionTimers = new Map();
  const PROBLEM_BANK = {
    sum: {title:'Sum two integers',statement:'Read two integers from standard input and print their sum.',constraints:'Both integers are between -1,000,000 and 1,000,000.',starter:'a, b = map(int, input().split())\n# Print the sum',tests:[{input:'2 3\n',expected:'5'},{input:'-1 4\n',expected:'3'}]},
    reverse: {title:'Reverse a string',statement:'Read one line and print its characters in reverse order.',constraints:'The input contains 1–1,000 characters.',starter:'text = input()\n# Print the reversed text',tests:[{input:'hello\n',expected:'olleh'},{input:'python\n',expected:'nohtyp'}]},
    palindrome: {title:'Check a palindrome',statement:'Read one word and print True if it reads the same forwards and backwards when letter case is ignored; otherwise print False.',constraints:'The input is one non-empty word containing letters.',starter:'word = input().strip().lower()\n# Print whether word is a palindrome',tests:[{input:'Racecar\n',expected:'True'},{input:'Interview\n',expected:'False'}]},
    factorial: {title:'Calculate a factorial',statement:'Read a non-negative integer n and print n factorial. By definition, 0 factorial is 1.',constraints:'0 ≤ n ≤ 20.',starter:'n = int(input())\n# Calculate and print n factorial',tests:[{input:'0\n',expected:'1'},{input:'5\n',expected:'120'}]},
    maximum: {title:'Find the largest of three numbers',statement:'Read three space-separated integers and print the largest.',constraints:'The input always contains exactly three integers.',starter:'numbers = list(map(int, input().split()))\n# Print the largest number',tests:[{input:'3 9 4\n',expected:'9'},{input:'-5 -2 -8\n',expected:'-2'}]},
    vowels: {title:'Count vowels',statement:'Read a line and print the number of English vowels (a, e, i, o, u), ignoring letter case.',constraints:'The line contains at most 1,000 characters.',starter:'text = input().lower()\n# Count and print the vowels',tests:[{input:'InterviewAce\n',expected:'6'},{input:'rhythm\n',expected:'0'}]},
    fibonacci: {title:'Find a Fibonacci number',statement:'Read n and print the zero-indexed Fibonacci number F(n), where F(0)=0 and F(1)=1.',constraints:'0 ≤ n ≤ 30.',starter:'n = int(input())\na, b = 0, 1\n# Calculate F(n) and print it',tests:[{input:'0\n',expected:'0'},{input:'7\n',expected:'13'}]},
    prime: {title:'Check for a prime number',statement:'Read an integer and print True if it is prime; otherwise print False.',constraints:'2 ≤ n ≤ 1,000,000.',starter:'n = int(input())\n# Check whether n is prime',tests:[{input:'2\n',expected:'True'},{input:'21\n',expected:'False'}]},
    deduplicate: {title:'Remove duplicate numbers',statement:'Read space-separated integers and print each number once, preserving its first-seen order.',constraints:'The input contains at least one integer.',starter:'numbers = list(map(int, input().split()))\n# Print unique numbers in their original order',tests:[{input:'1 2 1 3 2\n',expected:'1 2 3'},{input:'4 4 4\n',expected:'4'}]},
    secondLargest: {title:'Find the second-largest distinct number',statement:'Read space-separated integers and print the second-largest distinct value.',constraints:'The input contains at least two distinct integers.',starter:'numbers = list(map(int, input().split()))\n# Find and print the second-largest distinct number',tests:[{input:'4 1 7 7 3\n',expected:'4'},{input:'10 2 8\n',expected:'8'}]},
    binarySearch: {title:'Binary search',statement:'Read n, then n sorted space-separated integers, then a target. Print the target index (zero-based), or -1 if it is absent.',constraints:'The list is sorted in ascending order and 0 ≤ n ≤ 1,000.',starter:'n = int(input())\nvalues = list(map(int, input().split()))\ntarget = int(input())\n# Print the zero-based index or -1',tests:[{input:'5\n1 3 5 7 9\n7\n',expected:'3'},{input:'4\n2 4 6 8\n5\n',expected:'-1'}]},
    fizzBuzz: {title:'FizzBuzz',statement:'Read n. For each number from 1 through n, print FizzBuzz when divisible by both 3 and 5, Fizz when divisible by 3, Buzz when divisible by 5, or the number otherwise. Print one result per line.',constraints:'1 ≤ n ≤ 100.',starter:'n = int(input())\nfor number in range(1, n + 1):\n    pass  # Replace this line with the FizzBuzz rules',tests:[{input:'5\n',expected:'1\n2\nFizz\n4\nBuzz'},{input:'3\n',expected:'1\n2\nFizz'}]}
  };
  const REPORT_COMPONENTS = [
    {key:'coding',title:'Coding',weight:.4,source:'Submit a final solution from the Coding editor.'},
    {key:'technical',title:'Interviewer technical & problem-solving',weight:.3,source:'The interviewer submits final feedback after ending the session.'},
    {key:'communication',title:'Speech metrics',weight:.2,source:'The candidate records or uploads an answer and consents to analysis.'},
    {key:'resume',title:'Resume rules',weight:.1,source:'The candidate uploads a resume in Shared files.'}
  ];
  const el = id => document.getElementById(id);
  const LANGUAGE_LABELS = {python:'Python', javascript:'JavaScript', c:'C', cpp:'C++'};
  function languageLabel(language) { return LANGUAGE_LABELS[language] || LANGUAGE_LABELS.python; }
  function languageStarter(language, problem) {
    const statement = (problem?.statement || 'Solve the assigned problem.').trim();
    if (language === 'python') return `# ${statement}\n\n# Read input and write your solution here.\n`;
    if (language === 'javascript') return `// ${statement}\n\nfunction solve() {\n  // Read input and write your solution here.\n}\n\nsolve();\n`;
    if (language === 'c') return `/* ${statement} */\n#include <stdio.h>\n\nint main(void) {\n    /* Read input and write your solution here. */\n    return 0;\n}\n`;
    return `/* ${statement} */\n#include <iostream>\n\nint main() {\n    // Read input and write your solution here.\n    return 0;\n}\n`;
  }
  function setLanguage(language, announce) {
    const selected = LANGUAGE_LABELS[language] ? language : 'python';
    el('languageSelect').value = selected;
    el('languageBadge').textContent = languageLabel(selected);
    el('codeEditorLabel').textContent = `${languageLabel(selected)} editor`;
    el('peerCode').setAttribute('aria-label', `${languageLabel(selected)} source code`);
    if (announce && room?.problem) {
      el('peerCode').value = languageStarter(selected, room.problem);
      room.problem = {...room.problem, language: selected};
      clearTimeout(codeDebounce);
      codeDebounce = setTimeout(() => {
        try { send({type:'code', source:el('peerCode').value, language:selected}); }
        catch (error) { toast(error.message, true); }
      }, 400);
    }
  }
  const action = fn => async event => {
    event?.preventDefault();
    const button = event?.submitter || (event?.currentTarget?.tagName === 'BUTTON' ? event.currentTarget : null);
    if (button) button.disabled = true;
    try { await fn(event); } catch (error) { toast(error.message, true); }
    finally { if (button) button.disabled = false; if (room) controls(); }
  };
  const request = (path, body, method = 'POST') => api('/rooms/' + room.id + path,
    {method, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  const send = data => { if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data)); else throw new Error('Room connection is offline. Reconnect before continuing.'); };
  function line(parent, text, tag = 'p') { const item = document.createElement(tag); item.textContent = text; parent.append(item); return item; }
  function details(parent, title, data) { const d = document.createElement('details'); line(d, title, 'summary'); line(d, JSON.stringify(data, null, 2), 'pre'); parent.append(d); }
  function setupProblemBank() {
    const select = el('problemBank'); select.replaceChildren();
    for (const [key, problem] of Object.entries(PROBLEM_BANK)) select.add(new Option(problem.title, key));
    select.add(new Option('Write a custom problem', 'custom'));
    select.value = 'sum';
    updateProblemForm();
    select.onchange = () => { problemDraftActive = true; updateProblemForm(); };
  }
  function updateProblemForm() {
    const custom = el('problemBank').value === 'custom', problem = PROBLEM_BANK[el('problemBank').value];
    const fields = [['problemTitle','title'],['problemStatement','statement'],['problemConstraints','constraints'],['problemStarter','starter']];
    for (const [id, key] of fields) { el(id).value = custom ? '' : problem[key]; el(id).placeholder = custom ? `Enter ${key === 'title' ? 'a title' : key === 'statement' ? 'the problem statement' : key === 'constraints' ? 'optional constraints' : 'optional starter code'}` : ''; }
    el('problemTests').value = custom ? '' : JSON.stringify(problem.tests, null, 2);
    el('problemTests').placeholder = '[{"input":"2 3\\n","expected":"5"}]';
    el('problemModeHelp').textContent = custom
      ? 'Write your own title and statement, then provide 1–5 test cases as a JSON array with input and expected output.'
      : 'Choose a ready-to-use problem. You can edit its details and test cases before assigning it.';
    el('problemSubmit').textContent = custom ? 'Send custom problem' : 'Assign coding problem';
    renderProblemPreview();
  }
  function problemDraft() {
    let tests = [];
    try { tests = JSON.parse(el('problemTests').value); } catch {}
    return {title:el('problemTitle').value.trim(), statement:el('problemStatement').value.trim(),
      constraints:el('problemConstraints').value.trim(), starter:el('problemStarter').value,
      tests:Array.isArray(tests) ? tests : []};
  }
  function syncProblemForm(problem) {
    const signature = JSON.stringify(problem);
    if (signature === syncedProblemState) return;
    syncedProblemState = signature;
    const preset = Object.entries(PROBLEM_BANK).find(([, item]) => JSON.stringify(item) === JSON.stringify(problem));
    el('problemBank').value = preset ? preset[0] : 'custom';
    updateProblemForm();
    if (!preset) {
      el('problemTitle').value = problem.title || '';
      el('problemStatement').value = problem.statement || '';
      el('problemConstraints').value = problem.constraints || '';
      el('problemStarter').value = problem.starter || '';
      el('problemTests').value = JSON.stringify(problem.tests || [], null, 2);
      el('problemModeHelp').textContent = 'This problem is assigned. Edit it here and send it again to replace it before the candidate submits.';
    }
    el('problemSubmit').textContent = 'Update coding problem';
  }
  function renderProblemPreview() {
    if (!room || room.role !== 'interviewer' || (room.problem && !problemDraftActive)) return;
    const draft = problemDraft();
    el('sharedProblemTitle').textContent = draft.title || (el('problemBank').value === 'custom' ? 'Custom problem draft' : 'Problem preview');
    el('sharedProblemStatement').textContent = `${draft.statement || 'Add a problem statement in the form to preview it.'}${draft.constraints ? `\nConstraints: ${draft.constraints}` : ''}`;
    el('sharedProblemTests').textContent = draft.tests.length ? JSON.stringify(draft.tests, null, 2) : 'Add valid JSON test cases to preview them.';
    el('editorHint').textContent = 'Preview only. Click Assign coding problem to send this challenge to the candidate.';
  }
  async function show() {
    if (!mounted) {
      if (!mounting) mounting = (async () => {
      const markup = await fetch('/assets/peer.html?v=3.3.6').then(r => { if (!r.ok) throw new Error('Workspace could not load. Refresh to try again.'); return r.text(); });
      const wrapper = document.createElement('div'); wrapper.id = 'peerWorkspace'; wrapper.innerHTML = markup;
      const solo = document.createElement('section'); solo.className = 'solo-studio'; solo.id='soloStudio';
      while (el('workspace').firstChild) solo.append(el('workspace').firstChild);
      const historyPanel=wrapper.querySelector('#peerHistoryPanel'),profilePanel=wrapper.querySelector('#profilePanel');
      el('workspace').append(solo,wrapper,historyPanel,profilePanel); mounted = true; bind();
      })().catch(error=>{mounting=null;throw error;});
      await mounting;
    }
    await history();
    const profile = await api('/me');
    el('profileFirstName').value = profile.first_name; el('profileLastName').value = profile.last_name; el('profileContact').value = profile.contact_number;
    const invitation = new URLSearchParams(location.search).get('room');
    if (invitation) el('joinCode').value = invitation;
    return profile;
  }
  function page(view) {
    if(!mounted)return;
    for(const [id,target] of [['soloStudio','solo'],['peerWorkspace','peer'],['peerHistoryPanel','history'],['profilePanel','profile']])el(id).classList.toggle('hidden',view!==target);
  }
  function tab(name) {
    roomTab=name;
    el('peerRoom').querySelectorAll('[data-room-panel]').forEach(panel=>{
      const roleAllowed=!panel.classList.contains('interviewer-only') || room?.role==='interviewer';
      const candidateAllowed=!panel.classList.contains('candidate-only') || room?.role==='candidate';
      panel.classList.toggle('hidden',panel.dataset.roomPanel!==name || !roleAllowed || !candidateAllowed || (panel.id==='peerReport' && room?.status!=='completed'));
    });
    el('peerRoom').querySelector('.peer-layout').dataset.tab=name;
    el('peerRoom').querySelectorAll('[data-room-tab]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.roomTab===name)));
  }
  function controls() {
    if(!room)return;
    const active=room.status==='active', ended=room.status==='completed', candidate=room.role==='candidate';
    el('peerStart').disabled=room.status!=='waiting' || !room.candidate_joined;
    el('peerRoom').querySelectorAll('#sendQuestion button, #problemForm button, #peerChatForm button').forEach(button=>button.disabled=!active);
    const submitted=room.events?.some(event=>event.kind==='submission');
    el('problemSubmit').disabled = !active || !!submitted;
    el('runCode').disabled=el('submitCode').disabled=!active || !candidate || !room.problem || submitted;
    el('peerCode').readOnly=!candidate || !active || !!submitted;
    el('enableMedia').disabled=ended;
    el('callPeer').disabled=ended || !room.candidate_joined || socket?.readyState!==WebSocket.OPEN;
    const callState = pc?.connectionState;
    const callLabel = callState === 'connected' ? 'Call connected' : callState === 'connecting' ? 'Call connecting' : 'Connect call';
    el('callPeer').setAttribute('aria-label', callLabel); el('callPeer').title = callLabel;
    el('callPeer').setAttribute('aria-pressed', String(callState === 'connected'));
    el('toggleMic').disabled=el('toggleCamera').disabled=ended;
    el('recordAudio').disabled=!active || recorder?.state==='recording';
    el('peerFeedback').querySelector('button').disabled=!ended;
  }
  async function history() {
    const rows = await api('/rooms');
    const list = el('peerHistory');
    for (const timer of deletionTimers.values()) clearInterval(timer);
    deletionTimers.clear();
    list.replaceChildren();
    if (!rows.length) line(list, 'Your first peer interview starts here. Create a room or join an invitation.');
    for (const row of rows) {
      const article = document.createElement('article'); article.className = 'history-row'; list.append(article);
      if (row.delete_after) {
        showDeletionUndo(row, article, row.delete_after);
      } else {
        const entry = document.createElement('div'); entry.className = 'history-entry'; article.append(entry);
        const button = line(entry, `${row.topic} | ${row.role} | ${row.status} | ${row.id}`, 'button');
        button.className = 'history-item'; button.onclick = action(() => open(row.id));
        if (row.role === 'interviewer' && row.status !== 'active') {
          const remove = line(entry, 'Delete room', 'button'); remove.className = 'icon-control delete-room';
          remove.setAttribute('aria-label', `Delete room ${row.id}`); remove.title = 'Delete room';
          remove.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/></svg>';
          remove.onclick = action(async () => {
            const result = await api(`/rooms/${row.id}`, {method:'DELETE'});
            if (room?.id === row.id) close();
            const deadline = Number(result?.undo_until);
            const article = remove.closest('.history-row');
            if (result?.scheduled && Number.isFinite(deadline) && article?.isConnected) showDeletionUndo(row, article, deadline);
            else await history();
          });
        }
      }
    }
    const reports = await Promise.all(rows.filter(r => !r.delete_after && r.status === 'completed').slice(0, 20).reverse().map(r => api(`/rooms/${r.id}/report`)));
    drawProgress(reports);
  }
  function showDeletionUndo(row, article, deadline) {
    const status = document.createElement('div'); status.className = 'history-deletion'; status.setAttribute('role', 'status'); article.replaceChildren(status);
    line(status, `${row.topic} | ${row.role} | ${row.id}`, 'strong');
    const countdown = line(status, '', 'span');
    const undo = line(status, 'Undo', 'button'); undo.className = 'secondary undo-delete';
    undo.setAttribute('aria-label', `Undo deletion of interview ${row.id}`);
    undo.title = 'Restore this interview';
    let timer;
    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil(deadline - Date.now() / 1000));
      countdown.textContent = remaining ? `Deleting in ${remaining} second${remaining === 1 ? '' : 's'}` : 'Undo window ended';
      if (!remaining) {
        undo.disabled = true;
        clearInterval(timer);
        deletionTimers.delete(row.id);
        setTimeout(() => history().catch(error => toast(error.message, true)), 1100);
      }
    };
    timer = setInterval(updateCountdown, 100);
    deletionTimers.set(row.id, timer);
    updateCountdown();
    undo.onclick = action(async () => {
      await api(`/rooms/${row.id}/undo-delete`, {method:'POST'});
      clearInterval(timer); deletionTimers.delete(row.id);
      await history(); toast('Room restored.');
    });
  }
  function drawProgress(reports) {
    const container = el('progressScores'); container.replaceChildren();
    const scores = reports.filter(r => Number.isFinite(r.overall_score));
    if (!scores.length) {
      line(container, 'No scored assessments yet. Complete an interview and add feedback to see your progress.').className = 'score-empty';
      return;
    }
    const list = document.createElement('ol'); list.className = 'score-list';
    scores.forEach((report, index) => {
      const row = document.createElement('li'), score = Math.min(100, Math.max(0, report.overall_score));
      line(row, `Interview ${index + 1}`, 'span');
      const meter = document.createElement('meter'); meter.min = 0; meter.max = 100; meter.value = score;
      meter.setAttribute('aria-label', `Interview ${index + 1} overall score`); row.append(meter);
      line(row, `${Number(score).toFixed(1).replace(/\.0$/, '')}%`, 'strong'); list.append(row);
    });
    container.append(list);
  }
  async function open(id) {
    await showPage('peer'); close(); room = await api('/rooms/' + id); lastStatus = ''; roomTab='live'; render();
    el('peerRoom').classList.remove('hidden'); connect();
    el('peerWorkspace').querySelectorAll('.peer-home-only').forEach(node=>node.classList.add('hidden'));
    el('peerRoom').scrollIntoView({behavior: 'smooth', block: 'start'});
  }
  async function refresh() {
    if (!room) return;
    if (refreshing) { refreshAgain = true; return; }
    refreshing = true;
    const id = room.id;
    try { const data = await api('/rooms/' + id); if (room?.id === id) { room = data; render(); } }
    finally { refreshing = false; if (refreshAgain) { refreshAgain = false; refresh().catch(e => toast(e.message, true)); } }
  }
  function render() {
    const interviewer = room.role === 'interviewer';
    if (interviewer && room.problem && !problemDraftActive) syncProblemForm(room.problem);
    el('peerTitle').textContent = room.topic;
    const names = room.role === 'interviewer'
      ? {local: room.interviewer_name, remote: room.candidate_name}
      : {local: room.candidate_name, remote: room.interviewer_name};
    el('localVideoLabel').textContent = names.local || 'Loading participant...';
    el('remoteVideoLabel').textContent = names.remote || 'Waiting for participant...';
    const statusText=room.status==='waiting' ? (room.candidate_joined?'Candidate joined — ready to start':'Waiting for a candidate') : room.status==='active'?'Interview in progress':'Interview completed';
    el('peerIdentity').textContent=`You are the ${room.role}. ${statusText}.`;
    el('peerRoomCode').textContent=`Room code: ${room.id}`;
    el('timerLabel').textContent=room.status==='active'?'Time remaining':room.status==='completed'?'Session ended':'Session duration';
    if(room.status!=='active')el('peerTimer').textContent=room.status==='completed'?'00:00':`${Math.floor(room.duration_seconds/60)}:${String(room.duration_seconds%60).padStart(2,'0')}`;
    el('roomHelp').textContent=room.status==='waiting'?'Test your camera and microphone now. The timer starts only after the interviewer starts the session.':room.status==='active'?'Use the tabs to switch between the call, coding, documents and feedback.':'Review your report and final feedback below.';
    el('inviteLink').textContent = `${location.origin}/?room=${room.id}`;
    el('peerRoom').querySelectorAll('.interviewer-only').forEach(e => e.classList.toggle('hidden', !interviewer));
    el('peerRoom').querySelectorAll('.candidate-only').forEach(e => e.classList.toggle('hidden', interviewer));
    el('peerStart').classList.toggle('hidden', !interviewer || room.status !== 'waiting');
    el('peerEnd').classList.toggle('hidden', !interviewer || room.status === 'completed');
    el('documentKind').querySelector('[value=resume]').disabled = interviewer;
    if (interviewer) el('documentKind').value = 'resource';
    const language = room.problem?.language || el('languageSelect').value || 'python';
    setLanguage(language, false);
    el('languageSelect').disabled = interviewer || room.status !== 'active';
    el('peerCode').readOnly = interviewer || room.status !== 'active';
    if (document.activeElement !== el('peerCode') || interviewer) el('peerCode').value = room.code;
    const previewing = interviewer && (!room.problem || problemDraftActive);
    const problem = previewing ? problemDraft() : room.problem;
    el('sharedProblemTitle').textContent = problem?.title || (previewing ? (el('problemBank').value === 'custom' ? 'Custom problem draft' : 'Problem preview') : 'Waiting for a problem');
    el('sharedProblemStatement').textContent = problem ? `${problem.statement || 'Add a problem statement in the form to preview it.'}${problem.constraints ? `\nConstraints: ${problem.constraints}` : ''}` : '';
    el('sharedProblemTests').textContent = problem ? (problem.tests?.length ? JSON.stringify(problem.tests, null, 2) : 'Add valid JSON test cases to preview them.') : '';
    el('editorHint').textContent=interviewer
      ? (previewing ? 'This is a live preview. Click Assign coding problem to send this challenge to the candidate.' : 'You are the interviewer: this is the candidate’s read-only code. The assigned problem is shown above.')
      : room.status!=='active'?`Your ${languageLabel(language)} editor is here. It unlocks when the interviewer starts the session.`:!problem?'You can write code now. Run and Submit unlock after the interviewer assigns a problem.':'Write your solution below, run the tests, then submit your final answer.';
    const chat = el('peerChat'); chat.replaceChildren();
    for (const event of room.events) {
      if (['chat', 'question'].includes(event.kind)) {
        const div = document.createElement('div'); div.className = 'chat-entry';
        line(div, event.kind === 'question' ? 'INTERVIEWER QUESTION' : (event.user_name || 'Participant'), 'strong');
        line(div, event.payload.text); chat.append(div);
      }
    }
    chat.scrollTop = chat.scrollHeight;
    const chatAvailable = room.status === 'active';
    el('peerMessage').disabled = !chatAvailable;
    el('peerMessage').placeholder = chatAvailable ? 'Type a message' : 'Messaging is available after the interviewer starts the session';
    el('peerChatForm').querySelector('button[type="submit"]').disabled = !chatAvailable;
    const executions = room.events.filter(e => ['execution', 'submission'].includes(e.kind));
    if (executions.length) el('codeResults').textContent = JSON.stringify(executions.at(-1).payload, null, 2);
    const docs = el('peerDocuments'); docs.replaceChildren();
    const selected = el('ragDocument').value; el('ragDocument').replaceChildren();
    for (const doc of room.documents) {
      const row = document.createElement('div'); row.className = 'document-row';
      line(row, `${doc.filename} · ${doc.kind}`);
      const isImage = /\.(png|jpe?g|gif|webp)$/i.test(doc.filename);
      if (isImage) {
        const preview = line(row, 'Preview image', 'button'); preview.className = 'link';
        preview.onclick = action(async () => {
          const response = await fetch(`/api/rooms/${room.id}/documents/${doc.id}`, {credentials:'same-origin'});
          if (!response.ok) throw new Error('Image is unavailable.');
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          previewUrl = URL.createObjectURL(await response.blob());
          const image = document.createElement('img'); image.className = 'shared-image-preview'; image.alt = `Preview of ${doc.filename}`; image.src = previewUrl;
          row.append(image);
        });
      }
      const button = line(row, 'Download', 'button'); button.className = 'link'; button.onclick = action(async () => {
        const response = await fetch(`/api/rooms/${room.id}/documents/${doc.id}`, {credentials:'same-origin'});
        if (!response.ok) throw new Error('Document is unavailable.');
        saveBlob(await response.blob(), doc.filename);
      });
      const remove = line(row, 'Delete my upload', 'button'); remove.className = 'link'; remove.onclick = action(async () => {
        await request(`/documents/${doc.id}`, undefined, 'DELETE'); await refresh();
      });
      docs.append(row);
      if (doc.searchable) el('ragDocument').add(new Option(doc.filename, String(doc.id)));
    }
    if (selected) el('ragDocument').value = selected;
    const resumes = room.documents.filter(d => d.analysis);
    el('resumeAnalysis').replaceChildren();
    for (const doc of resumes) { line(el('resumeAnalysis'), `Resume quality: ${doc.analysis.score}/100`, 'h3'); doc.analysis.suggestions.forEach(s => line(el('resumeAnalysis'), s)); details(el('resumeAnalysis'), 'Checks and target relevance', doc.analysis); }
    const drafts = room.events.filter(e => e.kind === 'rag_draft');
    if (interviewer && drafts.length) renderDraft(drafts.at(-1).payload);
    if (room.status === 'completed') {
      stopMedia();
      if(lastStatus!=='completed')roomTab='feedback';
      api(`/rooms/${room.id}/report`).then(renderReport).catch(e => toast(e.message, true));
    }
    controls();tab(roomTab);
    if (lastStatus !== room.status) { lastStatus = room.status; history().catch(e => toast(e.message, true)); }
  }
  function renderDraft(draft) {
    const target = el('ragDraft'); target.replaceChildren();
    line(target, draft.question, 'h3'); line(target, `Suggested answer: ${draft.suggested_answer}`);
    draft.sources.forEach(s => line(target, `${s.filename}, ${s.location || 'page'} ${s.page}: ${s.text}`));
    const button = line(target, 'Use this question for review', 'button'); button.className = 'secondary';
    button.onclick = () => { tab('live'); el('peerQuestion').value = draft.question; el('peerQuestion').focus(); };
  }
  function renderReport(report) {
    if (!room || room.id !== report.room_id) return;
    const target = el('peerReport'); target.replaceChildren(); target.classList.remove('hidden');
    target.className = 'panel peer-report';
    const scores = report.scores || {};
    const weight = component => Number(report.weights?.[component.key] ?? component.weight);
    const availableWeight = REPORT_COMPONENTS.reduce((sum, component) => sum + (Number.isFinite(scores[component.key]) ? weight(component) : 0), 0);
    const availableCount = REPORT_COMPONENTS.filter(component => Number.isFinite(scores[component.key])).length;
    const percent = value => `${Number(value).toFixed(1).replace(/\.0$/, '')}%`;
    const section = (parent, title) => { const node = document.createElement('section'); node.className = 'report-block'; line(node, title, 'h3'); parent.append(node); return node; };

    const intro = document.createElement('div'); intro.className = 'report-heading';
    const titleGroup = document.createElement('div'); line(titleGroup, 'INTERVIEW SUMMARY', 'span').className = 'eyebrow';
    line(titleGroup, 'Feedback & report', 'h2');
    line(titleGroup, `${report.topic} · ${Math.round(report.duration_seconds)} seconds`, 'p').className = 'report-subtitle';
    intro.append(titleGroup); target.append(intro);

    const overview = document.createElement('section'); overview.className = `report-overview${availableCount ? '' : ' is-pending'}`;
    const overviewCopy = document.createElement('div');
    line(overviewCopy, availableCount ? 'Combined practice score' : 'Score pending', 'h3');
    line(overviewCopy, availableCount
      ? `${availableCount} of 4 categories are assessed. The displayed percentage uses the available categories.`
      : 'No assessment evidence has been recorded yet. Scores are not guessed or filled with zero.', 'p');
    overview.append(overviewCopy);
    if (Number.isFinite(report.overall_score)) {
      const score = document.createElement('div'); score.className = 'report-total';
      line(score, percent(report.overall_score), 'strong'); line(score, 'out of 100', 'span'); overview.append(score);
    } else line(overview, 'Add assessment evidence below to calculate your percentage.', 'strong').className = 'report-pending-hint';
    target.append(overview);

    const breakdown = section(target, 'Score breakdown');
    line(breakdown, 'Scores are percentages. Base weights are 40%, 30%, 20% and 10%; available categories are proportionally renormalized.', 'p').className = 'report-section-help';
    const grid = document.createElement('div'); grid.className = 'report-score-grid';
    for (const component of REPORT_COMPONENTS) {
      const score = scores[component.key], present = Number.isFinite(score), baseWeight = weight(component);
      const card = document.createElement('article'); card.className = `report-score-card${present ? '' : ' is-missing'}`;
      const head = document.createElement('div'); head.className = 'report-score-head';
      line(head, component.title, 'h4'); line(head, `${Math.round(baseWeight * 100)}% weight`, 'span').className = 'weight-pill'; card.append(head);
      line(card, present ? percent(score) : 'Not assessed', 'strong').className = 'report-component-score';
      if (present) {
        const meter = document.createElement('progress'); meter.max = 100; meter.value = Math.max(0, Math.min(100, score)); meter.setAttribute('aria-label', `${component.title} score ${percent(score)}`); card.append(meter);
        const normalizedWeight = availableWeight ? baseWeight / availableWeight : 0;
        const points = (score * normalizedWeight).toFixed(1).replace(/\.0$/, '');
        line(card, `${percent(normalizedWeight * 100)} of this total · adds ${points} points`, 'p').className = 'report-score-meta';
      } else line(card, component.source, 'p').className = 'report-score-meta';
      grid.append(card);
    }
    breakdown.append(grid);

    const missing = REPORT_COMPONENTS.filter(component => !Number.isFinite(scores[component.key]));
    if (missing.length) {
      const actions = section(target, 'How to complete the report');
      const list = document.createElement('ul'); list.className = 'report-next-list';
      for (const component of missing) line(list, `${component.title}: ${component.source}`, 'li');
      actions.append(list);
    }

    if (report.interviewer_feedback) {
      const feedback = section(target, 'Human interviewer feedback');
      const ratings = document.createElement('div'); ratings.className = 'report-rating-grid';
      for (const [label, key] of [['Technical knowledge','technical'],['Problem solving','problem_solving'],['Communication','communication']]) {
        const rating = document.createElement('div'); rating.className = 'report-rating';
        line(rating, label, 'span'); line(rating, percent(report.interviewer_feedback[key]), 'strong'); ratings.append(rating);
      }
      feedback.append(ratings);
      for (const [label, value] of [['Strengths',report.interviewer_feedback.strengths],['Areas to improve',report.interviewer_feedback.improvements]]) {
        if (value) { const note = document.createElement('div'); note.className = 'report-note'; line(note, label, 'strong'); line(note, value, 'p'); feedback.append(note); }
      }
      line(feedback, 'Technical knowledge and problem solving form the human 30% score. The communication rating is shown for context; it does not replace consented speech metrics.', 'p').className = 'report-section-help';
    }

    if (report.coding) {
      const coding = section(target, 'Final coding submission');
      line(coding, `${report.coding.passed} of ${report.coding.total} tests passed`, 'strong');
      for (const [index, test] of (report.coding.tests || []).entries()) {
        const row = document.createElement('div'); row.className = `report-test${test.passed ? ' is-passed' : ' is-failed'}`;
        line(row, `Test ${index + 1} · ${test.passed ? 'Passed' : 'Failed'}`, 'strong');
        if (test.output) line(row, `Output: ${test.output}`, 'p');
        if (test.error) line(row, `Error: ${test.error}`, 'p');
        coding.append(row);
      }
      if (report.coding.source) {
        const source = document.createElement('details'); source.className = 'report-source';
        line(source, 'View submitted Python source', 'summary');
        line(source, report.coding.source, 'pre'); coding.append(source);
      }
    }

    if (report.communication) {
      const speech = section(target, 'Automated speech metrics');
      const metrics = document.createElement('div'); metrics.className = 'report-rating-grid';
      for (const [label, value] of [['Speaking pace',`${report.communication.words_per_minute} words/min`],['Filler words',report.communication.filler_count],['Duration',`${report.communication.duration_seconds} sec`]]) {
        const item = document.createElement('div'); item.className = 'report-rating'; line(item, label, 'span'); line(item, String(value), 'strong'); metrics.append(item);
      }
      speech.append(metrics);
      if (report.communication.method) line(speech, report.communication.method, 'p').className = 'report-section-help';
      (report.communication.suggestions || []).forEach(suggestion => line(speech, suggestion, 'p'));
      if (report.communication.notice) line(speech, report.communication.notice, 'p').className = 'report-section-help';
    }

    if (report.resume) {
      const resume = section(target, 'Automated resume checks');
      const checks = document.createElement('ul'); checks.className = 'report-check-list';
      for (const [name, passed] of Object.entries(report.resume.checks || {})) line(checks, `${passed ? '✓' : '•'} ${name.replaceAll('_', ' ')}`, 'li');
      resume.append(checks);
      if (report.resume.matched_terms?.length) line(resume, `Matched role terms: ${report.resume.matched_terms.join(', ')}`, 'p');
      if (report.resume.missing_terms?.length) line(resume, `Missing role terms: ${report.resume.missing_terms.join(', ')}`, 'p');
      if (report.resume.method) line(resume, report.resume.method, 'p').className = 'report-section-help';
      (report.resume.suggestions || []).forEach(suggestion => line(resume, suggestion, 'p'));
    }

    if (report.questions?.length) {
      const questions = section(target, 'Questions asked');
      const list = document.createElement('ol'); list.className = 'report-next-list';
      report.questions.forEach(question => line(list, question, 'li')); questions.append(list);
    }

    if (availableCount) {
      const next = section(target, 'Suggested next steps');
      const list = document.createElement('ul'); list.className = 'report-next-list';
      (report.improvement_plan || []).forEach(step => line(list, step, 'li')); next.append(list);
    }
    if (report.scoring_method) {
      const method = document.createElement('details'); method.className = 'report-method';
      line(method, 'How the combined percentage is calculated', 'summary');
      line(method, report.scoring_method, 'p'); target.append(method);
    }
    if (report.notice) line(target, report.notice, 'p').className = 'report-disclaimer';
    const button = line(target, 'Download report (JSON)', 'button'); button.type = 'button'; button.className = 'secondary report-download';
    button.onclick = () => saveBlob(new Blob([JSON.stringify(report, null, 2)], {type:'application/json'}), `interviewace-${room.id}.json`);
    tab(roomTab);
  }
  function saveBlob(blob, filename) { const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  async function connect() {
    if (!room || connecting || socket?.readyState === WebSocket.CONNECTING || socket?.readyState === WebSocket.OPEN) return;
    connecting = true;
    const id = room.id;
    try {
      const auth = {authenticate:true};
      const isLocalHost = ['localhost', '127.0.0.1', '::1', '[::1]'].includes(location.hostname);
      const backendOrigin = isLocalHost ? '' : (window.INTERVIEWACE_BACKEND_WS_ORIGIN || '');
      let address;
      if (backendOrigin) {
        const issued = await api(`/rooms/${id}/ws-ticket`, {method:'POST'});
        auth.ticket = issued.ticket;
        address = new URL(`/api/rooms/${id}/ws`, backendOrigin);
      } else address = new URL(`/api/rooms/${id}/ws`, location.origin);
      address.protocol = address.protocol === 'https:' ? 'wss:' : 'ws:';
      if (room?.id !== id || !token) return;
      const connection = socket = new WebSocket(address);
      connection.onopen = () => { connecting = false; connection.send(JSON.stringify(auth)); controls(); };
      connection.onmessage = action(async event => {
      const message = JSON.parse(event.data);
      if (message.type === 'refresh') await refresh();
      else if (message.type === 'timer') {
        const seconds = message.remaining_seconds;
        if(message.status==='active')el('peerTimer').textContent=`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
        el('peerTimer').classList.toggle('low', message.status === 'active' && seconds <= 60);
        if (room.status !== message.status) await refresh();
      } else if (message.type === 'code' && room.role === 'interviewer') {
        el('peerCode').value = message.source;
        if (message.language) setLanguage(message.language, false);
      }
      else if (['offer','answer','ice'].includes(message.type)) await signal(message);
      else if (message.type === 'error') toast(message.message, true);
      else if (message.type === 'deleted') { close(); await history(); }
      });
      connection.onclose = event => {
        connecting = false;
        if (socket === connection) socket = null;
        if (event.code === 1008) toast('Session expired or room access changed. Please log in again.',true);
        else if (room?.id === id && token && event.code !== 4000) reconnect = setTimeout(connect, 2500);
      };
    } catch (error) {
      if (room?.id === id && token) {
        toast(error.message || 'Room connection could not start. Retrying shortly.', true);
        reconnect = setTimeout(connect, 2500);
      }
    } finally { connecting = false; }
  }
  function deviceChanged(next) {
    stream=next;
    const camera=next?.getVideoTracks().find(t=>t.readyState==='live'), mic=next?.getAudioTracks().find(t=>t.readyState==='live');
    el('localPlaceholder').classList.toggle('hidden',!!camera?.enabled);
    const cameraOn = !!camera?.enabled, micOn = !!mic?.enabled;
    for (const [id, on, onLabel, offLabel] of [['toggleCamera', cameraOn, 'Turn camera off', 'Enable camera'], ['toggleMic', micOn, 'Mute microphone', 'Enable microphone']]) {
      const button = el(id), label = on ? onLabel : offLabel;
      button.setAttribute('aria-label', label); button.title = label; button.setAttribute('aria-pressed', String(on));
    }
    const allOn = cameraOn && micOn, enable = el('enableMedia');
    enable.setAttribute('aria-pressed', String(allOn));
    enable.setAttribute('aria-label', allOn ? 'Camera and microphone are on' : 'Enable camera and microphone');
    enable.title = allOn ? 'Camera and microphone are on' : 'Enable camera and microphone';
    if(pc) for(const transceiver of pc.getTransceivers()) {
      const kind=transceiver.receiver.track.kind;
      const track=next?.getTracks().find(t=>t.kind===kind && t.readyState==='live') || null;
      transceiver.sender.replaceTrack(track).catch(e=>{el('mediaStatus').textContent=DeviceMedia.explain(e,kind);});
      if(track && transceiver.sender.setStreams)transceiver.sender.setStreams(next);
    }
  }
  async function media() {
    await devices.enable(['video','audio']);
    stream=devices.stream;
    if(room?.candidate_joined && !pc)el('mediaStatus').textContent += ' Use Connect call to talk with your peer.';
  }
  async function playRemote() {
    try { await el('remoteVideo').play(); el('retryRemoteAudio').classList.add('hidden'); }
    catch {el('retryRemoteAudio').classList.remove('hidden');el('mediaStatus').textContent='Peer media received. Click Play peer audio to allow playback.';}
  }
  function makePC() {
    if(pc)return pc;
    const peer=pc=new RTCPeerConnection({iceServers:[]});
    remoteStream=new MediaStream();el('remoteVideo').srcObject=remoteStream;
    for(const kind of ['audio','video']) {
      const track=stream?.getTracks().find(t=>t.kind===kind && t.readyState==='live');
      peer.addTransceiver(track || kind,{direction:'sendrecv',...(track?{streams:[stream]}:{})});
    }
    peer.ontrack=event=>{
      if(peer!==pc || !remoteStream)return;
      if(!remoteStream.getTracks().some(t=>t.id===event.track.id))remoteStream.addTrack(event.track);
      if(event.track.kind==='video') {
        event.track.onunmute=()=>el('remotePlaceholder').classList.add('hidden');
        event.track.onmute=()=>el('remotePlaceholder').classList.remove('hidden');
      }
      playRemote();
    };
    peer.onicecandidate=event=>{if(event.candidate && socket?.readyState===1)send({type:'ice',candidate:event.candidate});};
    peer.onnegotiationneeded=async()=>{
      if(peer!==pc || peer.signalingState!=='stable')return;
      try {makingOffer=true;await peer.setLocalDescription();send({type:peer.localDescription.type,description:peer.localDescription});}
      catch(error){el('mediaStatus').textContent='Connection could not start. Check that your peer is online, then reconnect.';}
      finally{makingOffer=false;}
    };
    peer.onconnectionstatechange=()=>{
      if(peer!==pc)return;
      const state=peer.connectionState;
      el('mediaStatus').textContent=state==='connected'?'Call connected. Camera and microphone can be controlled independently.':`Call: ${state}. ${state==='failed'?'Try Connect call again. Direct connections may fail across restricted networks.':''}`;
      controls();
      if(state==='connected')playRemote();
    };
    return peer;
  }
  let settingAnswer=false;
  async function signal(message) {
    if(!room || room.status==='completed')return;
    if(message.type==='ice') {
      if(ignoreOffer)return;
      if(pc?.remoteDescription)await pc.addIceCandidate(message.candidate);else candidates.push(message.candidate);
      return;
    }
    const peer=makePC(), description=message.description;
    if(!description || !['offer','answer'].includes(description.type))return;
    const ready=!makingOffer && (peer.signalingState==='stable' || settingAnswer);
    const collision=description.type==='offer' && !ready;
    ignoreOffer=room.role==='interviewer' && collision;
    if(ignoreOffer)return;
    settingAnswer=description.type==='answer';
    try {await peer.setRemoteDescription(description);} finally{settingAnswer=false;}
    for(const candidate of candidates)await peer.addIceCandidate(candidate);candidates=[];
    if(description.type==='offer') {
      await peer.setLocalDescription();send({type:peer.localDescription.type,description:peer.localDescription});
      if(!stream?.getTracks().length)el('mediaStatus').textContent='Peer is connecting. Enable your camera or microphone to share your own media.';
    }
  }
  function stopMedia() {
    if(recorder?.state==='recording')recorder.stop();
    devices?.stop();stream=null;
    if(pc){pc.onnegotiationneeded=null;pc.close();}pc=null;candidates=[];makingOffer=false;ignoreOffer=false;
    remoteStream?.getTracks().forEach(track=>track.stop());remoteStream=null;
    if(el('remoteVideo'))el('remoteVideo').srcObject=null;
    el('remotePlaceholder')?.classList.remove('hidden');
  }
  function close() {
    clearTimeout(reconnect); clearTimeout(codeDebounce); room = null; connecting = false;
    problemDraftActive = false; syncedProblemState = '';
    if (socket) { socket.onclose = null; socket.close(); } socket = null; stopMedia();
    if (mounted) {
      el('peerRoom').classList.add('hidden');
      el('peerWorkspace').querySelectorAll('.peer-home-only').forEach(node=>node.classList.remove('hidden'));
      ['peerChat','peerDocuments','resumeAnalysis','ragDraft','peerReport'].forEach(id => el(id).replaceChildren());
      el('peerReport').classList.add('hidden'); el('codeResults').textContent = 'Execution results appear here for both participants.';
      el('peerCode').value = ''; el('audioStatus').textContent = '';
      el('problemBank').value = 'sum'; updateProblemForm();
    }
  }
  async function uploadAudio(file) {
    if (!el('audioConsent').checked) throw new Error('Consent is required before audio analysis.');
    const data = new FormData(); data.append('consent', 'true'); data.append('file', file);
    el('audioStatus').textContent = 'Transcribing locally…';
    try { const result = await api(`/rooms/${room.id}/communication`, {method:'POST', body:data}); el('audioStatus').textContent = `Communication ${result.score}/100 · ${result.words_per_minute} words/min · ${result.filler_count} fillers. ${result.notice}`; }
    catch (e) { el('audioStatus').textContent = e.message; throw e; }
  }
  function bind() {
    setupProblemBank();
    devices=DeviceMedia.create(el('localVideo'),el('mediaStatus'),deviceChanged);
    el('peerRoom').querySelectorAll('[data-room-tab]').forEach(button=>button.onclick=()=>tab(button.dataset.roomTab));
    el('openEditor').onclick=()=>tab('coding');
    el('retryRemoteAudio').onclick=playRemote;
    window.addEventListener('pagehide',stopMedia);
    el('createRoom').onsubmit = action(async () => { const data = await api('/rooms', {method:'POST', body:JSON.stringify({topic:el('peerTopic').value, duration_seconds:Number(el('peerMinutes').value)*60})}); await open(data.id); await history(); });
    el('joinRoom').onsubmit = action(async () => { const code = el('joinCode').value.trim().toUpperCase(); await api(`/rooms/${encodeURIComponent(code)}/join`, {method:'POST'}); await open(code); });
    el('profileForm').onsubmit = action(async () => { const data = await api('/me', {method:'PATCH', body:JSON.stringify({first_name:el('profileFirstName').value,last_name:el('profileLastName').value,contact_number:el('profileContact').value})}); el('userBadge').textContent = data.name; Solo.profile(data); toast('Profile saved.'); });
    el('changePasswordForm').onsubmit = action(async () => { const result=await api('/change-password',{method:'POST',body:JSON.stringify({current_password:el('changeCurrent').value,new_password:el('changeNew').value,confirm_password:el('changeConfirm').value})}); el('changePasswordForm').reset(); close(); toast(result.message); });
    el('logoutAll').onclick = action(async () => { await api('/sessions',{method:'DELETE'}); close(); token=''; activeInterviewId=null; resetChat(); updatePanels(); toast('Logged out on all devices.'); });
    el('recoveryForm').onsubmit = action(async () => { const data = await api('/recovery-code', {method:'POST',body:JSON.stringify({password:el('recoveryPassword').value})}); el('recoveryForm').reset(); showRecovery(data.recovery_code); });
    el('deleteAccount').onclick = action(async () => { if (!confirm('Permanently delete your account, rooms you created, and stored personal data?')) return; await api('/me', {method:'DELETE'}); close(); token = ''; sessionStorage.removeItem('interviewace_token'); updatePanels(); });
    el('copyInvite').onclick = action(async () => { await navigator.clipboard.writeText(`${location.origin}/?room=${room.id}`); toast('Invitation copied.'); });
    el('peerStart').onclick = action(async () => { await request('/start'); await refresh(); });
    el('peerEnd').onclick = action(async () => { await request('/end'); await refresh(); });
    el('leaveRoom').onclick = () => close();
    el('sendQuestion').onsubmit = action(async () => { await request('/questions', {text:el('peerQuestion').value}); el('peerQuestion').value = ''; await refresh(); });
    el('problemForm').onsubmit = action(async () => {
      let tests;
      try { tests = JSON.parse(el('problemTests').value); }
      catch { throw new Error('Tests must be valid JSON: use an array of objects with input and expected strings.'); }
      if (!Array.isArray(tests) || tests.length < 1 || tests.length > 5 || tests.some(test => !test || typeof test.input !== 'string' || typeof test.expected !== 'string'))
        throw new Error('Add between 1 and 5 test cases. Each needs string fields named input and expected.');
      await request('/problem', {title:el('problemTitle').value, statement:el('problemStatement').value, constraints:el('problemConstraints').value, starter:el('problemStarter').value, tests});
      problemDraftActive = false;
      await refresh();
    });
    ['problemTitle','problemStatement','problemConstraints','problemStarter','problemTests'].forEach(id => el(id).addEventListener('input', () => { problemDraftActive = true; renderProblemPreview(); }));
    el('languageSelect').onchange = () => { setLanguage(el('languageSelect').value, true); };
    el('peerCode').oninput = () => { clearTimeout(codeDebounce); codeDebounce = setTimeout(() => { try { send({type:'code',source:el('peerCode').value,language:el('languageSelect').value}); } catch(e) { toast(e.message,true); } }, 400); };
    for (const [id, final] of [['runCode',false],['submitCode',true]]) el(id).onclick = action(async () => { el('codeResults').textContent = 'Running in the local sandbox…'; try { await request('/execute', {source:el('peerCode').value,language:el('languageSelect').value,final}); await refresh(); } catch(e) { el('codeResults').textContent = e.message; throw e; } });
    el('peerChatForm').onsubmit = action(async () => { send({type:'chat',text:el('peerMessage').value}); el('peerMessage').value = ''; });
    el('peerPdf').onchange = () => {
      const isImage = /\.(png|jpe?g|gif|webp)$/i.test(el('peerPdf').files[0]?.name || '');
      el('imageNoteLabel').classList.toggle('hidden', !isImage);
      el('imageNote').required = isImage;
    };
    el('peerUpload').onsubmit = action(async () => { const data = new FormData(); data.append('file',el('peerPdf').files[0]); data.append('kind',el('documentKind').value); data.append('note',el('imageNote').value); await api(`/rooms/${room.id}/documents`, {method:'POST',body:data}); el('peerUpload').reset(); el('imageNoteLabel').classList.add('hidden'); el('imageNote').required = false; await refresh(); });
    el('ragForm').onsubmit = action(async () => { const draft = await request('/rag', {document_id:Number(el('ragDocument').value),query:el('ragQuery').value}); renderDraft(draft); });
    el('peerFeedback').onsubmit = action(async () => { await request('/feedback', {technical:Number(el('ratingTechnical').value),problem_solving:Number(el('ratingProblem').value),communication:Number(el('ratingCommunication').value),strengths:el('feedbackStrengths').value,improvements:el('feedbackImprovements').value}); await refresh(); toast('Feedback saved.'); });
    el('enableMedia').onclick = action(media);
    el('callPeer').onclick=action(async()=>{
      if(!room?.candidate_joined)throw new Error('Invite a candidate first. You can still preview your own camera and microphone.');
      if(!stream?.getTracks().length)await media();
      if(pc && ['failed','closed'].includes(pc.connectionState)){pc.close();pc=null;}
      makePC();
      el('mediaStatus').textContent='Connecting to your peer…';
    });
    el('toggleMic').onclick=action(()=>devices.toggle('audio'));
    el('toggleCamera').onclick=action(()=>devices.toggle('video'));
    el('recordAudio').onclick = action(async () => {
      if (!el('audioConsent').checked) throw new Error('Check consent before recording.');
      if (!window.MediaRecorder || !navigator.mediaDevices) throw new Error('Recording requires a supported browser on localhost or HTTPS.');
      const audio = await navigator.mediaDevices.getUserMedia({audio:true});
      const roomId = room.id; recordingChunks = []; recorder = new MediaRecorder(audio);
      recorder.ondataavailable = e => recordingChunks.push(e.data);
      recorder.onstop = () => { audio.getTracks().forEach(t => t.stop()); el('stopAudio').disabled = true; el('recordAudio').disabled = false; if (room?.id === roomId && room.status === 'active') uploadAudio(new File(recordingChunks, 'answer.webm', {type:recorder.mimeType})).catch(e => toast(e.message,true)); };
      recorder.start(); el('recordAudio').disabled = true; el('stopAudio').disabled = false; el('audioStatus').textContent = 'Recording your answer. Stop before the session ends to analyze.';
    });
    el('stopAudio').onclick = () => { if (recorder?.state === 'recording') recorder.stop(); };
    el('audioUpload').onsubmit = action(() => uploadAudio(el('audioFile').files[0]));
  }
  return {show, close, page};
})();

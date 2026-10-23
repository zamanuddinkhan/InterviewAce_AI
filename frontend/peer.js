'use strict';
window.Peer = (() => {
  let mounted = false, room = null, socket = null, stream = null, pc = null, recorder = null;
  let reconnect = null, codeDebounce = null, candidates = [], recordingChunks = [], lastStatus = '', refreshing = false, refreshAgain = false;
  let mounting = null, roomTab = 'live', devices = null, makingOffer = false, ignoreOffer = false;
  let remoteStream = null, previewUrl = null;
  const deletionTimers = new Map();
  const el = id => document.getElementById(id);
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
  async function show() {
    if (!mounted) {
      if (!mounting) mounting = (async () => {
      const markup = await fetch('/assets/peer.html?v=3.3.0').then(r => { if (!r.ok) throw new Error('Workspace could not load. Refresh to try again.'); return r.text(); });
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
      line(row, `${score}/100`, 'strong'); list.append(row);
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
    el('peerTitle').textContent = room.topic;
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
    el('peerCode').readOnly = interviewer || room.status !== 'active';
    if (document.activeElement !== el('peerCode') || interviewer) el('peerCode').value = room.code;
    const problem = room.problem;
    el('sharedProblemTitle').textContent = problem?.title || 'Waiting for a problem';
    el('sharedProblemStatement').textContent = problem ? `${problem.statement}\nConstraints: ${problem.constraints}` : '';
    el('sharedProblemTests').textContent = problem ? JSON.stringify(problem.tests, null, 2) : '';
    el('editorHint').textContent=interviewer?'You are the interviewer: this is the candidate’s read-only code. Assign a problem above; the candidate can run and submit.':room.status!=='active'?'Your Python editor is here. It unlocks when the interviewer starts the session.':!problem?'You can write code now. Run and Submit unlock after the interviewer assigns a problem.':'Write your solution below, run the tests, then submit your final answer.';
    const chat = el('peerChat'); chat.replaceChildren();
    for (const event of room.events) {
      if (['chat', 'question'].includes(event.kind)) {
        const div = document.createElement('div'); div.className = 'chat-entry';
        line(div, event.kind === 'question' ? 'INTERVIEWER QUESTION' : `Participant #${event.user_id}`, 'strong');
        line(div, event.payload.text); chat.append(div);
      }
    }
    chat.scrollTop = chat.scrollHeight;
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
    line(target, 'Final practice report', 'h2');
    line(target, report.overall_score === null ? 'Score unavailable' : `${report.overall_score}/100`, 'h1');
    line(target, `${Math.round(report.duration_seconds)} seconds · ${report.topic}`);
    for (const [name, score] of Object.entries(report.scores)) {
      const row = document.createElement('div'); row.className = 'score-row'; line(row, name); line(row, score === null ? 'Unavailable' : `${Math.round(score)}/100`, 'strong');
      if (score !== null) { const meter = document.createElement('progress'); meter.max = 100; meter.value = score; meter.setAttribute('aria-label', name); row.append(meter); } target.append(row);
    }
    line(target, report.scoring_method, 'p');
    if (report.interviewer_feedback) details(target, 'Human interviewer feedback', report.interviewer_feedback);
    if (report.communication) details(target, 'Automated speech metrics', report.communication);
    if (report.resume) details(target, 'Automated resume checks', report.resume);
    if (report.coding) details(target, 'Final Python submission', report.coding);
    line(target, 'Next steps', 'h3'); report.improvement_plan.forEach(s => line(target, s)); line(target, report.notice);
    const button = line(target, 'Download report (JSON)', 'button'); button.className = 'secondary';
    button.onclick = () => saveBlob(new Blob([JSON.stringify(report, null, 2)], {type:'application/json'}), `interviewace-${room.id}.json`);
    tab(roomTab);
  }
  function saveBlob(blob, filename) { const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  function connect() {
    const id = room.id;
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/rooms/${id}/ws`);
    socket.onopen = () => {socket.send(JSON.stringify({authenticate:true}));controls();};
    socket.onmessage = action(async event => {
      const message = JSON.parse(event.data);
      if (message.type === 'refresh') await refresh();
      else if (message.type === 'timer') {
        const seconds = message.remaining_seconds;
        if(message.status==='active')el('peerTimer').textContent=`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
        el('peerTimer').classList.toggle('low', message.status === 'active' && seconds <= 60);
        if (room.status !== message.status) await refresh();
      } else if (message.type === 'code' && room.role === 'interviewer') el('peerCode').value = message.source;
      else if (['offer','answer','ice'].includes(message.type)) await signal(message);
      else if (message.type === 'error') toast(message.message, true);
      else if (message.type === 'deleted') { close(); await history(); }
    });
    socket.onclose = event => { if (event.code === 1008) toast('Session expired or room access changed. Please log in again.',true); else if (room?.id === id && token && event.code !== 4000) reconnect = setTimeout(connect, 2500); };
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
    clearTimeout(reconnect); clearTimeout(codeDebounce); room = null;
    if (socket) { socket.onclose = null; socket.close(); } socket = null; stopMedia();
    if (mounted) {
      el('peerRoom').classList.add('hidden');
      el('peerWorkspace').querySelectorAll('.peer-home-only').forEach(node=>node.classList.remove('hidden'));
      ['peerChat','peerDocuments','resumeAnalysis','ragDraft','peerReport'].forEach(id => el(id).replaceChildren());
      el('peerReport').classList.add('hidden'); el('codeResults').textContent = 'Execution results appear here for both participants.';
      el('peerCode').value = ''; el('audioStatus').textContent = '';
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
    el('problemBank').onchange = () => {
      if (el('problemBank').value === 'custom') return;
      const reverse = el('problemBank').value === 'reverse';
      el('problemTitle').value = reverse ? 'Reverse a string' : 'Sum two integers';
      el('problemStatement').value = reverse ? 'Read a string from standard input and print it reversed.' : 'Read two integers from standard input and print their sum.';
      el('problemConstraints').value = reverse ? '1–1000 characters' : '-1000000 ≤ a, b ≤ 1000000';
      el('problemStarter').value = reverse ? 'text = input()\n# Print the reversed text' : 'a, b = map(int, input().split())\n# Print the sum';
      el('problemTests').value = JSON.stringify(reverse ? [{input:'hello\n',expected:'olleh'},{input:'python\n',expected:'nohtyp'}] : [{input:'2 3\n',expected:'5'},{input:'-1 4\n',expected:'3'}], null, 2);
    };
    el('problemForm').onsubmit = action(async () => { await request('/problem', {title:el('problemTitle').value, statement:el('problemStatement').value, constraints:el('problemConstraints').value, starter:el('problemStarter').value, tests:JSON.parse(el('problemTests').value)}); await refresh(); });
    el('peerCode').oninput = () => { clearTimeout(codeDebounce); codeDebounce = setTimeout(() => { try { send({type:'code',source:el('peerCode').value}); } catch(e) { toast(e.message,true); } }, 400); };
    for (const [id, final] of [['runCode',false],['submitCode',true]]) el(id).onclick = action(async () => { el('codeResults').textContent = 'Running in the local sandbox…'; try { await request('/execute', {source:el('peerCode').value,final}); await refresh(); } catch(e) { el('codeResults').textContent = e.message; throw e; } });
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

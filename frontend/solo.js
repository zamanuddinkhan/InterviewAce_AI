/* Honest AI presence: animated illustration, optional local speech, local STT. */
window.Solo = (() => {
  let devices = null, questionText = '', recorder = null, generation = 0, timer = null;
  const el = id => document.getElementById(id);
  function state(text) { if (el('coachStatus')) el('coachStatus').textContent = text; }
  function profile(user) {
    const name = (user?.first_name || user?.name || '').trim();
    el('soloInitial').textContent = Array.from(name)[0]?.toLocaleUpperCase() || '?';
  }
  function cancelVoice() { window.speechSynthesis?.cancel(); el('aiCoach')?.classList.remove('speaking'); }
  function reset() {
    discardRecording();
    questionText=''; cancelVoice();
    if (el('readQuestion')) el('readQuestion').disabled=true;
    state('Ready when you are.');
  }
  function discardRecording() {
    generation++;clearTimeout(timer);if(recorder?.state==='recording')recorder.stop();
    if(el('soloRecord')){el('soloRecord').disabled=false;el('soloStopRecord').disabled=true;}
  }
  function question(text) { discardRecording();questionText=text; cancelVoice(); el('readQuestion').disabled=false; state('Your question is ready. Take your time.'); }
  function complete() { reset(); state('Practice complete. Your report is ready.'); }
  function stopMedia() {
    discardRecording(); devices?.stop();
    cancelVoice();
    if (el('soloStopRecord')) { el('soloStopRecord').disabled=true; el('soloRecord').disabled=false; }
  }
  function bind() {
    devices = DeviceMedia.create(el('soloVideo'),el('soloMediaStatus'), stream => {
      const camera = stream?.getVideoTracks().some(t => t.enabled && t.readyState==='live');
      const mic = stream?.getAudioTracks().some(t => t.enabled && t.readyState==='live');
      if (recorder?.state === 'recording') recorder.stream.getAudioTracks().forEach(track => { track.enabled=!!mic; });
      el('soloVideoPlaceholder').classList.toggle('hidden',!!camera);
      for (const [id, enabled, label] of [['soloCamera',camera,camera?'Turn camera off':'Enable camera'], ['soloMic',mic,mic?'Mute microphone':'Enable microphone']]) {
        el(id).setAttribute('aria-label',label); el(id).title=label; el(id).setAttribute('aria-pressed',String(!!enabled));
      }
    });
    const safe = (id, fn) => async () => {
      el(id).disabled=true;
      try { await fn(); } catch(e) { el('soloMediaStatus').textContent=e.message; toast(e.message,true); }
      finally { el(id).disabled=false; }
    };
    el('soloCamera').onclick=safe('soloCamera',()=>devices.toggle('video'));
    el('soloMic').onclick=safe('soloMic',()=>devices.toggle('audio'));
    el('soloStopMedia').onclick=()=>{stopMedia();el('soloMediaStatus').textContent='Camera and microphone are off.';};
    el('readQuestion').onclick=()=>{
      if (!questionText) return;
      if (!window.speechSynthesis) { el('voiceStatus').textContent='Read-aloud is unavailable in this browser. The question remains available as text.';return; }
      const voices=speechSynthesis.getVoices().filter(v=>v.localService);
      const voice=voices.find(v=>/^en/i.test(v.lang)) || voices[0];
      if (!voice) { el('voiceStatus').textContent='No installed local voice was found. Install a speech voice in Windows settings, or read the question on screen.';return; }
      cancelVoice();const utterance=new SpeechSynthesisUtterance(questionText);utterance.voice=voice;utterance.rate=.95;
      utterance.onstart=()=>{el('aiCoach').classList.add('speaking');state('Reading your question…');};
      utterance.onend=()=>{el('aiCoach').classList.remove('speaking');state('Your turn. Type or record your answer.');};
      utterance.onerror=event=>{el('aiCoach').classList.remove('speaking');if(!['canceled','interrupted'].includes(event.error))el('voiceStatus').textContent='Read-aloud could not start. You can continue using the text question.';};
      speechSynthesis.speak(utterance);el('voiceStatus').textContent='Reading with an installed local voice.';
    };
    el('soloRecord').onclick=async()=>{
      if (!el('soloAudioConsent').checked) { el('soloAudioStatus').textContent='Please give consent before recording an answer.';return; }
      if (!activeInterviewId) { el('soloAudioStatus').textContent='Start an AI interview before recording an answer.';return; }
      if (!window.MediaRecorder) { el('soloAudioStatus').textContent='Recording is unsupported in this browser. You can type your answer.';return; }
      try {
        await devices.enable(['audio']);
        const stream=devices.stream;
        if (!stream?.getAudioTracks().some(t=>t.readyState==='live' && t.enabled)) return;
        const ticket=++generation, interviewId=activeInterviewId;
        const recordingStream=new MediaStream(stream.getAudioTracks().filter(t=>t.readyState==='live').map(t=>t.clone()));
        const options=MediaRecorder.isTypeSupported('audio/webm')?{mimeType:'audio/webm'}:{};
        const recording=recorder=new MediaRecorder(recordingStream,options), chunks=[];let recordingTimer=null;cancelVoice();
        recording.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
        recording.onstop=async()=>{
          clearTimeout(recordingTimer);recordingStream.getTracks().forEach(t=>t.stop());
          if(ticket!==generation)return;
          el('soloStopRecord').disabled=true;
          el('soloAudioStatus').textContent='Transcribing locally. Please wait…';
          try {
            const type=recording.mimeType, extension=type.includes('ogg')?'ogg':type.includes('mp4')?'m4a':'webm';
            const file=new File(chunks,`answer.${extension}`,{type});
            const form=new FormData();form.append('consent','true');form.append('file',file);
            const result=await api(`/interviews/${interviewId}/transcribe`,{method:'POST',body:form});
            if(ticket!==generation || activeInterviewId!==interviewId)return;
            el('answerText').value=result.transcript;
            el('soloAudioStatus').textContent='Transcription ready. Review or edit the text, then submit your answer.';
          } catch(e){el('soloAudioStatus').textContent=e.message;}
          finally{if(ticket===generation)el('soloRecord').disabled=false;}
        };
        recorder.start();el('soloRecord').disabled=true;el('soloStopRecord').disabled=false;
        el('soloAudioStatus').textContent='Recording this answer. Stop when you finish (maximum two minutes).';
        timer=recordingTimer=setTimeout(()=>{if(recording.state==='recording')recording.stop();},120000);
      } catch(e){el('soloAudioStatus').textContent=DeviceMedia.explain(e,'Microphone');}
    };
    el('soloStopRecord').onclick=()=>{if(recorder?.state==='recording')recorder.stop();};
    window.addEventListener('pagehide',stopMedia);
  }
  document.addEventListener('DOMContentLoaded',bind);
  return {state,reset,question,complete,stopMedia,discardRecording,profile};
})();

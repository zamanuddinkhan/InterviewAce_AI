/* Shared, consent-driven device handling. No device access happens on page load. */
window.DeviceMedia = (() => {
  'use strict';
  function explain(error, kind = 'Camera/microphone') {
    const name = error?.name;
    if (name === 'NotAllowedError' || name === 'SecurityError') return `${kind} permission is blocked. Use the camera/lock icon beside the browser address, allow access, and check Windows Settings > Privacy & security > Camera/Microphone.`;
    if (name === 'NotFoundError' || name === 'OverconstrainedError') return `${kind} device was not found. Connect a device or continue with the other available device.`;
    if (name === 'NotReadableError' || name === 'AbortError') return `${kind} is busy or unavailable. Close other apps using it, then try again.`;
    return error?.message || `${kind} could not be enabled.`;
  }
  function create(video, status, changed = () => {}) {
    let stream = null, generation = 0;
    const get = () => { if (!stream) stream = new MediaStream(); return stream; };
    function describe(failures = []) {
      const active = get().getTracks().filter(t => t.readyState === 'live' && t.enabled).map(t => t.kind === 'video' ? 'Camera' : 'microphone');
      status.textContent = `${active.length ? active.join(' and ') + ' enabled.' : 'Camera and microphone are off.'}${failures.length ? ' ' + failures.join(' ') : ''}`;
      return active;
    }
    async function enable(kinds = ['video','audio']) {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw new Error('Device access requires http://localhost, http://127.0.0.1, or HTTPS. A plain HTTP network IP cannot use camera/microphone.');
      const ticket = generation, failures = [];
      for (const kind of kinds) {
        if (ticket !== generation) break;
        const existing = get().getTracks().find(track => track.kind === kind && track.readyState === 'live');
        if (existing) { existing.enabled = true; continue; }
        try {
          const result = await navigator.mediaDevices.getUserMedia({video:kind === 'video', audio:kind === 'audio'});
          if (ticket !== generation) { result.getTracks().forEach(track => track.stop()); continue; }
          result.getTracks().forEach(track => { get().addTrack(track); track.onended = () => changed(get()); });
        } catch (error) { failures.push(explain(error, kind === 'video' ? 'Camera' : 'Microphone')); }
      }
      if (ticket !== generation) return null;
      if (video) { video.srcObject = get(); video.play().catch(() => {}); }
      changed(get());
      const active = describe(failures);
      if (!active.length && failures.length) throw new Error(failures.join(' '));
      return get();
    }
    function toggle(kind) {
      const tracks = get().getTracks().filter(t => t.kind === kind && t.readyState === 'live');
      if (!tracks.length) return enable([kind]);
      const enabled = !tracks[0].enabled; tracks.forEach(t => t.enabled = enabled); changed(get()); describe();
      return Promise.resolve(get());
    }
    function stop() {
      generation++; stream?.getTracks().forEach(t => t.stop()); stream = null;
      if (video) video.srcObject = null;
      changed(null);
    }
    return {enable, toggle, stop, get stream() { return stream; }};
  }
  return {create, explain};
})();

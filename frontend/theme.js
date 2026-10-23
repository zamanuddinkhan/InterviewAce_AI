/* Runs before styles paint; theme preference contains no account/session data. */
(() => {
  'use strict';
  const key = 'interviewace_theme';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = null;
  try { const saved = localStorage.getItem(key); if (['light', 'dark'].includes(saved)) preference = saved; } catch { /* Storage may be blocked. */ }
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    const dark = theme === 'dark', button = document.getElementById('themeToggle');
    if (button) {
      const label = dark ? 'Switch to light mode' : 'Switch to dark mode';
      button.setAttribute('aria-label', label); button.title = label;
      button.setAttribute('aria-pressed', String(dark));
    }
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#050608' : '#f4f6fa');
    document.dispatchEvent(new CustomEvent('interviewace:themechange', {detail:{theme}}));
  }
  const selected = () => preference || (system.matches ? 'dark' : 'light');
  apply(selected());
  document.addEventListener('DOMContentLoaded', () => {
    apply(selected());
    document.getElementById('themeToggle')?.addEventListener('click', () => {
      preference = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(key, preference); } catch { /* Toggle still works in memory. */ }
      apply(preference);
    });
    const year = document.getElementById('footerYear'); if (year) year.textContent = new Date().getFullYear();
  });
  system.addEventListener('change', () => { if (!preference) apply(selected()); });
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = ['light','dark'].includes(event.newValue) ? event.newValue : null;
    apply(selected());
  });
})();

/* OrkiLab optional, non-destructive quick navigation pilot for long trainer interfaces.
   Never edits training controls, persists settings or triggers training actions. */
(() => {
  'use strict';
  function label(text) {
    return typeof window.t === 'function' ? window.t(text) : text;
  }
  function init() {
    const grid = document.querySelector('.main-grid');
    const sidebar = grid?.querySelector('.sidebar');
    if (!grid || !sidebar || document.getElementById('orkilab-trainer-quicknav')) return;
    const nav = document.createElement('nav');
    nav.id = 'orkilab-trainer-quicknav';
    nav.className = 'orkilab-trainer-quicknav';
    nav.setAttribute('aria-label', label('Trainer quick navigation'));
    const heading = document.createElement('span');
    heading.className = 'orkilab-quicknav-heading';
    heading.textContent = label('Jump to');
    nav.append(heading);

    function addTarget(text, target, panel) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'orkilab-quicknav-link';
      b.textContent = text;
      b.addEventListener('click', () => {
        if (panel?.classList.contains('collapsed')) {
          const clickable = panel.querySelector('.panel-title[onclick]');
          if (clickable && typeof window.togglePanel === 'function') window.togglePanel(clickable);
          else panel.classList.remove('collapsed');
        }
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      });
      nav.append(b);
    }

    const panels = Array.from(sidebar.querySelectorAll('.panel')).filter(panel => !!panel.querySelector(':scope > .panel-title[onclick]'));
    for (const panel of panels) {
      const title = panel.querySelector(':scope > .panel-title > span:first-child');
      const text = title?.textContent?.trim();
      if (text) addTarget(text, panel, panel);
    }
    for (const [selector, text] of [
      ['#terminal', 'Console'],
      ['#ds-grid', 'Dataset Manager'],
      ['#gallery', 'Generated previews']
    ]) {
      const target = grid.querySelector(selector);
      if (target) addTarget(label(text), target, target.closest('.panel'));
    }
    if (nav.querySelectorAll('button').length) grid.parentNode.insertBefore(nav, grid);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();

/* The settings card: given a capability's `settings` declaration (the JSON
   shape settings.py's `as_json` produces -- a list of
   {type:'choice', id, label, default, options:[{label, value, preview?}]}
   or {type:'number', id, label, default, min, max, step}) and its current
   `values` ({id: value}, missing ones taken from each setting's default),
   renders the card into `container` and calls `onChange(values)` with the
   full {id: value} every time something changes.

   Declared data in, a plain callback out: this never reaches into a note
   or a chip itself -- see SettingsCard.render's caller for that wiring. */
(function () {
  'use strict';

  function el(t, c, h) {
    const e = document.createElement(t);
    if (c) e.className = c;
    if (h != null) e.innerHTML = h;
    return e;
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  }

  function valueOf(setting, values) {
    return (values && Object.prototype.hasOwnProperty.call(values, setting.id)) ? values[setting.id] : setting.default;
  }

  /* One <audio> at a time across every card: picking a second preview
     stops whichever one was already playing. `nowPlayingButton` is tracked
     alongside the audio so its sc-playing class comes off wherever it was
     left -- a second voice started, the same ▶ toggled off, or play()
     rejecting (a 404 or 503 preview). */
  let nowPlaying = null;
  let nowPlayingButton = null;
  function stopPlaying() {
    if (nowPlaying) nowPlaying.pause();
    if (nowPlayingButton) nowPlayingButton.classList.remove('sc-playing');
    nowPlaying = null;
    nowPlayingButton = null;
  }
  function playPreview(url, button) {
    if (nowPlaying && nowPlaying.dataset && nowPlaying.dataset.url === url) { stopPlaying(); return }
    stopPlaying();
    const a = new Audio(url);
    a.dataset.url = url;
    a.addEventListener('ended', stopPlaying);
    nowPlaying = a;
    nowPlayingButton = button;
    button.classList.add('sc-playing');
    a.play().catch(() => { if (nowPlaying === a) stopPlaying() });
  }

  /* `current` is one object shared by every row of the card, mutated in
     place: a row that changes it reads every other row's latest value too,
     so picking a voice after dragging speed can't revert speed to the value
     it had when the card was last drawn. */
  function renderChoice(setting, current, onChange, redraw) {
    const row = el('div', 'sc-row sc-choice');
    row.append(el('div', 'sc-label', esc(setting.label)));
    const list = el('div', 'sc-options');
    const value = valueOf(setting, current);
    for (const option of setting.options) {
      const on = option.value === value;
      const opt = el('button', 'sc-option' + (on ? ' sc-on' : ''));
      opt.type = 'button';
      opt.setAttribute('aria-pressed', on ? 'true' : 'false');
      let html = '';
      if (option.preview) html += `<span class="sc-play" role="button" aria-label="Play ${esc(option.label)}">▶</span>`;
      html += `<span class="sc-optlabel">${esc(option.label)}</span>`;
      opt.innerHTML = html;
      opt.addEventListener('click', e => {
        const play = e.target.closest('.sc-play');
        if (play) { e.stopPropagation(); playPreview(option.preview, play); return }
        current[setting.id] = option.value;
        onChange({...current});
        redraw();
      });
      list.append(opt);
    }
    row.append(list);
    return row;
  }

  function renderNumber(setting, current, onChange) {
    const row = el('div', 'sc-row sc-number');
    const id = 'sc-' + setting.id + '-' + Math.random().toString(36).slice(2);
    const label = el('label', 'sc-label', esc(setting.label));
    label.htmlFor = id;
    row.append(label);
    const value = valueOf(setting, current);
    const input = el('input', 'sc-range');
    input.type = 'range';
    input.id = id;
    input.min = setting.min;
    input.max = setting.max;
    input.step = setting.step;
    input.value = value;
    const readout = el('span', 'sc-value', String(value));
    input.addEventListener('input', () => {
      readout.textContent = input.value;
      current[setting.id] = Number(input.value);
      onChange({...current});
    });
    row.append(input, readout);
    return row;
  }

  /* `container` is cleared and filled with one row per setting; `onChange`
     is called with the full values dict (every declared id, not just the
     one that changed) whenever any row changes. Returns nothing: callers
     that need the latest values keep their own copy from `onChange`. */
  function render(container, settings, values, onChange) {
    const current = {...(values || {})};
    container.classList.add('sc-card');
    const draw = () => {
      container.replaceChildren();
      for (const setting of settings) {
        container.append(setting.type === 'choice' ? renderChoice(setting, current, onChange, draw)
                                                     : renderNumber(setting, current, onChange));
      }
    };
    draw();
  }

  window.SettingsCard = {render};
})();

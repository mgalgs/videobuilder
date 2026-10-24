/* Capability, font, sound and music suggestions while a director types a note
   (editor.html's #message): see suggest.py and suggest-notes.md for the
   design. A plain script, not a module, so it shares director.js's top-level
   `const`/`let` bindings (`state`, `player`, `tlNoteClip`); `noteCapabilityIds`
   and `noteAssetIds`, declared here at top level for the same reason, are how
   director.js reads a note's chips when it sends the note (see addPending in
   director.js). A capability pick (one of CAP_FAMILIES) carries an {id,
   settings} entry, `settings` the non-default values that chip's settings
   card picked (capValues), empty for a chip with nothing changed or no card
   at all. A font, sound effect or music pick (ASSET_FAMILIES) carries a plain
   id, with no settings card. No suggestion of any kind is ever written into
   the note's own text (no insertText, no replaced span): every pick becomes a
   chip below the note instead -- the only difference is that a capability's
   chip also responds to typing its #id directly, while a font/sfx/music chip
   is picked only, with no typed form. */
let noteCapabilityIds = () => [];
let noteAssetIds = () => ({fonts: [], sfx: [], music: []});
// Restores picked (non-typed) chips, and the values their cards held, after
// editPending puts a pending note's text back into the box; a capability's
// own #id chips also reappear from the text once 'input' fires, but a font/
// sfx/music chip has no typed form, so restoring it here is the only way back.
let restorePickedCapIds = () => {};
let restorePickedAssetIds = () => {};
(() => {
'use strict';
if (!document.getElementById('message')) return;
const $ = id => document.getElementById(id);
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e };
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const phone = () => innerWidth <= 700;
const svg = (p, w = 16, sw = 2) => `<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
const I = {
  play: '<path d="M8 5.5v13l10-6.5z" fill="currentColor" stroke="none"/>',
  stop: '<rect x="7" y="7" width="10" height="10" rx="1.5" fill="currentColor" stroke="none"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  looks: '<path d="M12 3a9 9 0 0 0 0 18c1.5 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10" cy="7" r="1.2"/><circle cx="15" cy="7" r="1.2"/>',
  type: '<path d="M5 6V4h14v2M12 4v16M9 20h6"/>',
  fonts: '<path d="M4 20l6-16h1l6 16M6.5 14h8"/><path d="M17 20h4"/>',
  sfx: '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 7v10"/>',
  music: '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
  capabilities: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
};
const FAM = ['looks', 'type', 'fonts', 'sfx', 'music', 'capabilities'];
// The families that are capabilities in the strict sense (named moves with a
// definition and an api, not an asset like a font file or a music track): a
// capability's chip also responds to typing its #id (see hashtagCapIds).
const CAP_FAMILIES = ['looks', 'type', 'capabilities'];
// Assets: a font, a sound effect or a music track. Picked only -- no #id
// hashtag form for these -- but a pick still never touches the note's own
// text, the same as a capability (see pick()).
const ASSET_FAMILIES = ['fonts', 'sfx', 'music'];
const ASSET_LABEL = {fonts: 'Font', sfx: 'Sound', music: 'Music'};
const FAM_LABEL = {looks: 'Looks', type: 'Type', fonts: 'Fonts', sfx: 'Sound effects', music: 'Music', capabilities: 'More'};
const FAM_TAB = {looks: 'Looks', type: 'Type styles', fonts: 'Fonts', sfx: 'Sound effects', music: 'Music', capabilities: 'Other capabilities'};
const DEBOUNCE_MS = 600;
const MIN_WORDS = 3;

/* ---- catalog: fetched once, lazily ---- */
let CAT = null, catPromise = null;
function loadCatalog() {
  if (!catPromise) catPromise = fetch('api/suggest/catalog').then(r => r.ok ? r.json() : null).then(data => {
    CAT = data;
    if (data) for (const f of data.fonts) {
      const st = el('style');
      st.textContent = `@font-face{font-family:"sg-${f.id}";src:url(api/fonts/${f.id}/file)}`;
      document.head.append(st);
    }
    return data;
  }).catch(() => null);
  return catPromise;
}
const BY = {};
const CAPS = {}; // capability id -> {id, family, title, settings}: every #id a hashtag can name
function indexCatalog() {
  if (!CAT) return;
  for (const fam of CAP_FAMILIES) for (const c of CAT[fam]) {
    BY[fam + ':' + c.id] = c;
    if (!(c.id in CAPS)) CAPS[c.id] = {id: c.id, family: fam, title: c.title, settings: c.settings || null};
  }
  for (const f of CAT.fonts) BY['fonts:' + f.id] = f;
  for (const s of CAT.sfx) BY['sfx:' + s.id] = s;
  for (const m of CAT.music) BY['music:' + m.id] = m;
}
const keyOf = i => i.family + ':' + i.id;
const nameOf = (f, id) => { const x = BY[f + ':' + id]; if (!x) return id;
  return f === 'fonts' ? x.family : f === 'sfx' || f === 'music' ? (f === 'music' ? x.title : x.id) : x.title };
const fmtTime = t => Math.floor(t / 60) + ':' + String(Math.round(t % 60)).padStart(2, '0');

/* ---- where it lives on this page ---- */
let ta, cards, chips, tail, think, xbtn, capChips, capCards;
function mount() {
  ta = $('message');
  if (!ta) return false;
  cards = el('div', 'sg-cards'); cards.setAttribute('role', 'list'); cards.setAttribute('aria-label', 'Suggested for this note');
  chips = el('div', 'sg-chips'); chips.setAttribute('aria-label', 'More you can ask for');
  tail = el('div', 'sg-tail');
  capChips = el('div', 'sg-capchips');
  capChips.setAttribute('aria-label', 'Capabilities, fonts, sounds and music this note references');
  capCards = el('div', 'sg-capcards'); capCards.setAttribute('aria-label', 'Settings for the capabilities this note references');
  think = el('span', 'sg-think', '<span class="sg-dots"><i></i><i></i><i></i></span><span class="sg-slowtext">Still thinking…</span>');
  think.title = 'Looking for capabilities that fit this note';
  xbtn = el('button', 'sg-x', svg(I.x, 16, 2.4));
  xbtn.type = 'button'; xbtn.setAttribute('aria-label', 'Hide suggestions for this note');
  xbtn.title = 'Hide suggestions for this note (Esc)';
  xbtn.onclick = dismiss;
  xbtn.classList.add('sg-hidden'); tail.classList.add('sg-hidden'); // until the first render() decides otherwise
  tail.append(think, xbtn);
  const composer = $('composer'), extras = composer.querySelector('.composer-extras');
  composer.insertBefore(cards, extras);
  extras.append(chips, tail);
  composer.querySelector('.composer-row').insertAdjacentElement('afterend', capChips);
  capChips.insertAdjacentElement('afterend', capCards);
  ta.addEventListener('input', onInput);
  ta.addEventListener('keydown', e => { if (e.key === 'Escape' && shown.length) { e.preventDefault(); dismiss() } });
  return true;
}

/* ---- state ---- */
let shown = [], dismissed = false, timer = 0, inflight = null, staticChips = false;
let hiddenNote = 0, seqCounter = 0, lastSeq = 0, modelOn = null, sentText = null;
let pickedCapIds = []; // ids picked from a suggestion, in pick order (a chip the creator can remove)
let capValues = {}; // id -> {settingId: value}, only entries that differ from that setting's own default
let capCardsKey = null; // the chip ids the cards below them were last built for
let pickedAssetIds = {fonts: [], sfx: [], music: []}; // ids picked from a suggestion, per family, in pick order

function currentVideo() { return typeof state !== 'undefined' ? state.video : null }
function currentClip() { return typeof tlNoteClip === 'function' ? tlNoteClip() : null }
function currentAt() {
  if (typeof state === 'undefined' || typeof player === 'undefined') return null;
  return state.stamp ? player.currentTime : null;
}

function onInput() {
  if (!ta.value.trim()) {
    dismissed = false; shown = []; staticChips = false; sentText = null; pickedCapIds = []; capValues = {};
    pickedAssetIds = {fonts: [], sfx: [], music: []};
    stopAll();
    render(); renderCapChips(); cancel(); return
  }
  renderCapChips();
  if (dismissed) return;
  const before = shown.length;
  shown = shown.filter(i => !i.replace || ta.value.includes(i.replace.span));
  if (shown.length !== before) render();
  cancel();
  clearTimeout(timer);
  timer = setTimeout(ask, DEBOUNCE_MS);
  if (modelOn === false) { staticChips = true; render() }
}

function cancel() { if (inflight) { inflight.abort(); inflight = null } clearTimeout(think.h1); clearTimeout(think.h2); think.classList.remove('on', 'slow') }

async function ensureModel() {
  if (modelOn !== null) return modelOn;
  try {
    const r = await fetch('api/suggest/config');
    const data = r.ok ? await r.json() : {model: false};
    modelOn = !!data.model;
  } catch (e) { modelOn = false }
  return modelOn;
}

async function ask() {
  const text = ta.value.trim();
  if (!text || text.split(/\s+/).length < MIN_WORDS) return;
  if (!await ensureModel()) { staticChips = true; render(); return }
  if (text === sentText) return;
  cancel();
  const controller = new AbortController();
  const seq = ++seqCounter;
  inflight = controller;
  think.h1 = setTimeout(() => think.classList.add('on'), 2000);
  think.h2 = setTimeout(() => think.classList.add('slow'), 3500);
  const body = {video: currentVideo(), text, surface: 'editor', clip: currentClip(),
               at: currentAt(), seq};
  try {
    const r = await fetch('api/suggest', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                          body: JSON.stringify(body), signal: controller.signal});
    if (inflight !== controller) return;  // superseded
    inflight = null;
    cancel();
    if (!r.ok) return;
    const data = await r.json();
    if (data.seq < lastSeq) return;
    lastSeq = data.seq;
    sentText = text;
    await loadCatalog();
    indexCatalog();
    if (!dismissed) {
      shown = data.items.filter(i => !i.replace || ta.value.includes(i.replace.span));
      render();
    }
  } catch (e) {
    if (inflight === controller) { inflight = null; cancel() }
  }
}

function dismiss() {
  dismissed = true; cancel(); clearTimeout(timer); shown = []; staticChips = false; render();
  hiddenNote = 1; render();
  setTimeout(() => { hiddenNote = 0; render() }, 3500);
}

/* ---- drawing the strip ---- */
function thumb(i, big) {
  const f = i.family, x = BY[keyOf(i)];
  if (!x) return '';
  if (f === 'looks' || f === 'type' || f === 'capabilities') {
    const k = f === 'looks' ? (x.kind === 'filter' ? 'Filter look' : 'Look') : f === 'type' ? 'Type' : (x.category || '').split(' ')[0];
    return `<img class="sg-poster" src="${x.poster}" alt="" loading="lazy" onerror="this.style.display='none'">` +
      `<video class="sg-loop" muted loop playsinline preload="none" src="${x.clip}"></video>` +
      (big ? '' : `<span class="sg-kind">${esc(k)}</span>`);
  }
  if (f === 'fonts') return `<span class="sg-fontthumb" style="font-family:'sg-${x.id}'">${esc(sample())}</span>` +
    (big ? '' : '<span class="sg-kind">Font</span>');
  const bars = Array.from({length: 20}, (_, n) => 20 + Math.abs(Math.sin(n * 1.7 + x.id.length)) * 70);
  return `<span class="sg-wave">${bars.map(h => `<i style="height:${h.toFixed(0)}%"></i>`).join('')}</span>` +
    `<button type="button" class="sg-play" data-play="${esc(keyOf(i))}" aria-label="Play ${esc(nameOf(f, i.id))}">${svg(I.play, 14)}</button>` +
    (big ? '' : `<span class="sg-kind" style="left:auto;right:5px">${f === 'sfx' ? 'Sound' : 'Music'}</span>`);
}
function sample() {
  const v = ta ? ta.value : '';
  const q = /["“]([^”"]{2,40})["”]/.exec(v);
  if (q) return q[1];
  const w = v.replace(/\([^)]*\)/g, '').split(/\s+/).filter(Boolean);
  return w.length ? w.slice(Math.max(0, w.length - 4)).join(' ').replace(/[,.;:!?]+$/, '') : 'The quick brown fox';
}
function render() {
  if (!cards) return;
  const strong = shown.filter(i => i.strength === 'strong');
  cards.replaceChildren(); chips.replaceChildren();
  const usePhone = phone();
  if (!usePhone) for (const i of strong) {
    const x = BY[keyOf(i)]; if (!x) continue;
    const b = el('button', 'sg-card'); b.type = 'button'; b.setAttribute('role', 'listitem'); b.dataset.key = keyOf(i);
    if (i.why) b.title = i.why;
    b.innerHTML = `<span class="sg-thumb">${thumb(i)}</span><span class="sg-name">${esc(nameOf(i.family, i.id)).replace(/([/_])/g, '$1<wbr>')}</span>` +
      (i.why ? `<span class="sg-why">${esc(i.why)}</span>` : '');
    b.onmouseenter = () => { b.classList.add('sg-looping'); b.querySelector('video')?.play().catch(() => {}) };
    b.onmouseleave = () => { b.classList.remove('sg-looping'); b.querySelector('video')?.pause() };
    b.onclick = e => { const p = e.target.closest('[data-play]'); if (p) { e.stopPropagation(); play(i); return } pick(i) };
    b.tabIndex = -1;
    cards.append(b);
  }
  if (usePhone) for (const i of strong) {
    const x = BY[keyOf(i)]; if (!x) continue;
    const c = el('button', 'sg-chip sg-strongchip'); c.type = 'button'; c.dataset.key = keyOf(i);
    if (i.why) c.title = i.why;
    const dot = i.family === 'fonts' ? `<span class="sg-dot" style="font-family:'sg-${x.id}';font-weight:700">Aa</span>` :
      (i.family === 'sfx' || i.family === 'music') ? `<span class="sg-mini" data-play="1" aria-label="Play">${svg(I.play, 12)}</span>` :
      `<span class="sg-dot" style="background-image:url(${x.poster})"></span>`;
    c.innerHTML = dot + esc(nameOf(i.family, i.id));
    c.tabIndex = -1;
    c.onclick = e => { if (e.target.closest('[data-play]')) { e.stopPropagation(); play(i); return } pick(i) };
    chips.append(c);
  }
  const fams = staticChips ? FAM : FAM.filter(f => shown.some(i => i.family === f));
  for (const f of fams) {
    const c = el('button', 'sg-chip'); c.type = 'button'; c.dataset.fam = f;
    c.innerHTML = svg(I[f], 15) + FAM_LABEL[f];
    c.tabIndex = -1;
    c.onclick = () => openPicker(f);
    chips.append(c);
  }
  if (hiddenNote) { const n = el('span', 'sg-think on', 'Suggestions hidden for this note'); n.style.color = '#8a8a93'; chips.append(n) }
  const any = strong.length || fams.length;
  xbtn.classList.toggle('sg-hidden', !any);
  tail.classList.toggle('sg-hidden', !any && !think.classList.contains('on') && !inflight);
  $('composer').querySelector('.composer-extras').classList.toggle('sg-on', !!(any || hiddenNote || inflight));
}

/* ---- capability references: #id anywhere in the note becomes a chip below it,
   live as the creator types, the same chip a suggestion pick adds ---- */
const HASHTAG_RE = /#([a-z][a-z0-9-]*)/gi;
function hashtagCapIds(text, caps) {
  const out = [];
  let m;
  HASHTAG_RE.lastIndex = 0;
  while ((m = HASHTAG_RE.exec(text))) {
    const id = m[1].toLowerCase();
    if (caps[id] && !out.includes(id)) out.push(id);
  }
  return out;
}
function capChipIds() {
  const ids = hashtagCapIds(ta.value, CAPS);
  for (const id of pickedCapIds) if (!ids.includes(id)) ids.push(id);
  return ids;
}
// What a note actually sends for its chips: one {id, settings} per id, `settings`
// whatever capValues holds for it (already the diff from default -- see renderCapChips).
function capChipEntries() {
  return capChipIds().map(id => ({id, settings: capValues[id] || {}}));
}
// What a note actually sends for its font/sfx/music chips: {fonts, sfx, music}, each
// the ids pickedAssetIds holds for that family, in pick order (there is no #id hashtag
// form for these -- picked only, see pick()).
function assetPickEntries() {
  return {fonts: [...pickedAssetIds.fonts], sfx: [...pickedAssetIds.sfx], music: [...pickedAssetIds.music]};
}
// `values` as the settings card's onChange hands it (every declared id) narrowed
// to the ones that actually differ from that setting's own default -- what a note
// should carry, since a card nobody touched should look exactly like no card at all.
function settingsValuesDiff(settings, values) {
  const out = {};
  for (const s of settings || []) {
    if (values && Object.prototype.hasOwnProperty.call(values, s.id) && values[s.id] !== s.default) out[s.id] = values[s.id];
  }
  return out;
}
function renderCapChips() {
  if (!capChips) return;
  const ids = capChipIds();
  // Rebuilding a card on every keystroke would cut off a voice sample mid-play
  // and reset the card's scroll, so cards are rebuilt only when the chips change.
  const cardKey = ids.map(id => id + (CAPS[id] ? '' : '?')).join(' ');
  const rebuildCards = capCards && cardKey !== capCardsKey;
  if (rebuildCards) { capCards.replaceChildren(); capCardsKey = cardKey }
  const capChipEls = [];
  for (const id of ids) {
    const cap = CAPS[id];
    const typedOnly = !pickedCapIds.includes(id);
    const c = el('span', 'sg-capchip' + (typedOnly ? ' sg-capchip-typed' : ''));
    c.append(el('span', 'sg-capchip-name', esc(cap ? cap.title : id)), el('span', 'sg-capchip-id', '#' + esc(id)));
    if (!typedOnly) {
      const rm = el('button', 'sg-capchip-x', svg(I.x, 12, 2.4));
      rm.type = 'button';
      rm.setAttribute('aria-label', `Remove #${id}`);
      rm.onclick = () => { pickedCapIds = pickedCapIds.filter(x => x !== id); delete capValues[id]; renderCapChips() };
      c.append(rm);
    }
    capChipEls.push(c);
    // A chip whose capability declares settings (narration's voice/speed, say) gets
    // its own card, stacked below the chip row in the same order as the chips.
    if (rebuildCards && cap && cap.settings && cap.settings.length && window.SettingsCard) {
      const card = el('div', 'sg-capcard');
      window.SettingsCard.render(card, cap.settings, capValues[id] || {}, values => {
        capValues[id] = settingsValuesDiff(cap.settings, values);
      });
      capCards.append(card);
    }
  }
  // Asset chips (font/sfx/music) are picked only -- typing never adds or removes one --
  // and a sound or music chip's play button may be mid-playback (play()'s own `btns`
  // lookup holds these exact nodes): each chip is built once and reused by (family, id)
  // across renders, so a chip playing a track survives every other chip changing too,
  // not just a keystroke.
  renderCapChips.assetChipByKey = renderCapChips.assetChipByKey || new Map();
  const assetChipEls = [], liveKeys = [];
  for (const fam of ASSET_FAMILIES) for (const id of pickedAssetIds[fam]) {
    const k = fam + ':' + id;
    liveKeys.push(k);
    let c = renderCapChips.assetChipByKey.get(k);
    if (!c) {
      c = el('span', 'sg-capchip sg-assetchip');
      c.append(el('span', 'sg-assetchip-kind', svg(I[fam], 13) + ASSET_LABEL[fam]),
               el('span', 'sg-capchip-name', esc(nameOf(fam, id))));
      if (fam === 'sfx' || fam === 'music') {
        const p = el('button', 'sg-assetchip-play', svg(I.play, 12));
        p.type = 'button';
        p.setAttribute('data-play', fam + ':' + id);
        p.setAttribute('aria-label', `Play ${nameOf(fam, id)}`);
        p.onclick = () => play({family: fam, id});
        c.append(p);
      }
      const rm = el('button', 'sg-capchip-x', svg(I.x, 12, 2.4));
      rm.type = 'button';
      rm.setAttribute('aria-label', `Remove ${nameOf(fam, id)}`);
      rm.onclick = () => {
        if (playing && playing.key === k) stopAll();
        pickedAssetIds[fam] = pickedAssetIds[fam].filter(x => x !== id);
        renderCapChips();
      };
      c.append(rm);
      renderCapChips.assetChipByKey.set(k, c);
    }
    assetChipEls.push(c);
  }
  for (const k of [...renderCapChips.assetChipByKey.keys()]) {
    if (!liveKeys.includes(k)) renderCapChips.assetChipByKey.delete(k);
  }
  capChips.replaceChildren(...capChipEls, ...assetChipEls);
}

/* ---- picking: every pick becomes a chip; none of them ever touch the note's
   own text (see the file header for why) ---- */
function pick(i) {
  if (CAP_FAMILIES.includes(i.family)) {
    // A capability pick adds a #id chip below the note, exactly like typing
    // the id's hashtag would (see hashtagCapIds/renderCapChips).
    if (!pickedCapIds.includes(i.id)) pickedCapIds.push(i.id);
  } else {
    // A font, sfx or music pick adds the same kind of chip, just with no typed
    // form and no settings (see renderCapChips, assetPickEntries).
    const list = pickedAssetIds[i.family];
    if (list && !list.includes(i.id)) list.push(i.id);
  }
  renderCapChips();
  shown = shown.filter(x => keyOf(x) !== keyOf(i));
  render();
}

/* ---- sound: sfx plays the real take, music plays its source's audio_url ---- */
let playing = null;
function stopAll() { if (playing) { playing.stop(); playing = null } }
function play(i) {
  const k = keyOf(i);
  if (playing && playing.key === k) { stopAll(); return }
  stopAll();
  const x = BY[k]; if (!x) return;
  const btns = [...document.querySelectorAll(`[data-play="${CSS.escape(k)}"]`)];
  const on = v => { for (const b of btns) { b.innerHTML = svg(v ? I.stop : I.play, 12);
    b.closest('.sg-card,.sg-srow,.sg-chip')?.classList.toggle('sg-playing', v);
    b.closest('.sg-srow')?.classList.toggle('playing', v) } };
  const src = i.family === 'sfx' ? 'api/suggest/sfx-file?id=' + encodeURIComponent(i.id) : x.audio_url;
  const a = new Audio(src);
  a.play().catch(() => {});
  a.onended = () => { on(false); playing = null };
  on(true);
  playing = {key: k, stop: () => { a.pause(); on(false) }};
}

/* ---- the picker ---- */
let pk = null;
function closePicker() { if (!pk) return; stopAll(); pk.shade.remove(); pk.box.remove(); pk = null }
async function openPicker(fam) {
  await loadCatalog();
  indexCatalog();
  if (!CAT) return;
  closePicker();
  const ph = phone();
  const sug = new Set(shown.map(keyOf));
  const expandedFamilies = new Set();
  const shade = el('div', 'sg-shade' + (ph ? ' phone' : '')), box = el('div', 'sg-picker' + (ph ? ' phone' : ''));
  box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', 'Add to your note'); box.tabIndex = -1;
  shade.onclick = closePicker;
  const count = {looks: CAT.looks.length, type: CAT.type.length, fonts: CAT.fonts.length, sfx: CAT.sfx.length,
                music: CAT.music.length, capabilities: CAT.capabilities.length};
  box.innerHTML = (ph ? '<div class="sg-grab"></div>' : '') +
    '<div class="sg-phead"><div><strong>Add to your note</strong>' +
    '<span>Picking one adds a chip below your note, without changing what you wrote</span></div>' +
    `<button type="button" class="sg-pclose" aria-label="Close">${svg(I.x, 20, 2.2)}</button></div>` +
    `<div class="sg-tabs" role="tablist">${FAM.map(f => `<button type="button" role="tab" data-tab="${f}">${FAM_TAB[f]}<span class="n">${count[f]}</span></button>`).join('')}</div>` +
    '<div class="sg-pbody"></div>';
  const body = box.querySelector('.sg-pbody');
  const first = arr => arr.slice().sort((a, b) => (sug.has(b.k) ? 1 : 0) - (sug.has(a.k) ? 1 : 0));
  const badge = k => sug.has(k) ? '<span class="sg-badge">Suggested</span>' : '';
  const capCard = c => { const k = c.family + ':' + c.id;
    return `<button type="button" class="sg-gcard" data-pick="${esc(k)}" title="${esc(c.card)}"><span class="sg-thumb">${badge(k)}${thumb({family: c.family, id: c.id}, true)}</span><b>${esc(c.title)}</b><small>${esc(c.card)}</small></button>` };
  const withFam = (fam, arr) => arr.map(c => ({...c, family: fam, k: fam + ':' + c.id}));
  let h = '';
  const looksScene = first(withFam('looks', CAT.looks.filter(c => c.kind !== 'filter')));
  const looksFilter = first(withFam('looks', CAT.looks.filter(c => c.kind === 'filter')));
  h += `<section class="sg-sec" data-sec="looks"><h3>Looks</h3><p>One named art style for the whole video, or for one clip.</p>` +
    `<div class="sg-sub">Scene looks: for a picture the video draws</div><div class="sg-grid">${looksScene.map(capCard).join('')}</div>` +
    `<div class="sg-sub">Filter looks: for footage, photos, screen captures</div><div class="sg-grid">${looksFilter.map(capCard).join('')}</div></section>`;
  h += `<section class="sg-sec" data-sec="type"><h3>Type styles</h3><p>How words arrive and move.</p><div class="sg-grid">${first(withFam('type', CAT.type)).map(capCard).join('')}</div></section>`;
  const fs = first(CAT.fonts.map(f => ({...f, k: 'fonts:' + f.id})));
  h += `<section class="sg-sec" data-sec="fonts"><h3>Fonts</h3><p>Shown in your own words. Every one of these is installed for the builder.</p>` +
    `<div class="sg-fontgrid">${fs.map(f => `<button type="button" class="sg-fcard" data-pick="${esc(f.k)}">${sug.has(f.k) ? '<span class="sg-badge">Suggested</span>' : ''}<span class="sample" style="font-family:'sg-${f.id}'">${esc(sample())}</span><span class="meta"><b>${esc(f.family)}</b><span>${esc(f.about)}</span></span></button>`).join('')}</div></section>`;
  const ss = first(CAT.sfx.map(s => ({...s, k: 'sfx:' + s.id})));
  h += `<section class="sg-sec" data-sec="sfx"><h3>Sound effects</h3><p>Each lands on the frame of the motion it sells. Listen, then use.</p>` +
    `<div class="sg-list">${ss.map(s => `<div class="sg-srow ${sug.has(s.k) ? 'sug' : ''}"><button type="button" class="p" data-play="${esc(s.k)}" aria-label="Play ${esc(s.id)}">${svg(I.play, 12)}</button>` +
      `<span class="info"><b>${esc(s.id)}</b><span>${esc(s.role)} · ${esc(s.family)} · ${s.dur.toFixed(2)} s${s.takes > 1 ? ` · ${s.takes} takes` : ''}${sug.has(s.k) ? ' · <span style="color:#ffb3ab">suggested</span>' : ''}</span></span>` +
      `<button type="button" class="use" data-pick="${esc(s.k)}">Use</button></div>`).join('')}</div>` +
    '<p class="sg-note">Real takes from the vb-sfx-1 pack (earshot, MIT), base take of each.</p></section>';
  const ms = first(CAT.music.map(m => ({...m, k: 'music:' + m.id})));
  h += `<section class="sg-sec" data-sec="music"><h3>Music</h3><p>${ms.length ? esc(ms[0].source || '') : 'No music sources are configured.'}</p>` +
    `<div class="sg-list">${ms.map(m => `<div class="sg-srow ${sug.has(m.k) ? 'sug' : ''}"><button type="button" class="p" data-play="${esc(m.k)}" aria-label="Play ${esc(m.title)}">${svg(I.play, 12)}</button>` +
      `<span class="info"><b style="font-family:inherit;font-size:13.5px">${esc(m.title)}</b><span>${(m.tags || []).map(t => `<span class="sg-tag">${esc(t)}</span>`).join('')} ${m.duration != null ? fmtTime(m.duration) : ''}</span></span>` +
      `<button type="button" class="use" data-pick="${esc(m.k)}">Use</button></div>`).join('')}</div></section>`;
  // Capabilities, curated (hand-written) and from the videobuilder.capabilities registry alike (a registry
  // entry carries `group`, which a curated one never does -- that's how the two are told apart here).
  // With the search box empty, curated ones show flat as before; each registry family collapses into
  // one row (title, count, a few cards) until clicked, since there can be hundreds in one family.
  const matchWords = (c, words) => words.every(w => [c.title, ...(c.aliases || []), ...(c.phrasings || [])]
    .join(' ').toLowerCase().includes(w));
  function buildCapSection(query) {
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (words.length) {
      const matches = CAT.capabilities.filter(c => matchWords(c, words));
      if (!matches.length) return `<p class="sg-sub">No capabilities match “${esc(query.trim())}”.</p>`;
      return `<div class="sg-grid">${first(withFam('capabilities', matches)).map(capCard).join('')}</div>`;
    }
    const curated = CAT.capabilities.filter(c => !c.group), fromFamilies = CAT.capabilities.filter(c => c.group);
    const cats = [...new Set(curated.map(c => c.category))];
    let out = cats.map(cat => `<div class="sg-sub">${esc(cat)}</div><div class="sg-grid">` +
      `${first(withFam('capabilities', curated.filter(c => c.category === cat))).map(capCard).join('')}</div>`).join('');
    for (const cat of [...new Set(fromFamilies.map(c => c.category))]) {
      const items = fromFamilies.filter(c => c.category === cat), open = expandedFamilies.has(cat);
      out += `<div class="sg-capfam${open ? ' open' : ''}"><button type="button" class="sg-capfam-head" data-togglefam="${esc(cat)}">` +
        `<span class="sg-arrow">${open ? '▾' : '▸'}</span><b>${esc(cat)}</b><span class="n">${items.length}</span></button>`;
      if (!open) {
        out += `<div class="sg-grid sg-capfam-preview">${first(withFam('capabilities', items)).slice(0, 4).map(capCard).join('')}</div>`;
      } else {
        const groups = [], byGroup = {};
        for (const c of items) { if (!byGroup[c.group]) { byGroup[c.group] = []; groups.push(c.group) } byGroup[c.group].push(c) }
        out += groups.map(g => `<div class="sg-sub">${esc(g)}</div><div class="sg-grid">` +
          `${first(withFam('capabilities', byGroup[g])).map(capCard).join('')}</div>`).join('');
      }
      out += '</div>';
    }
    return out;
  }
  h += `<section class="sg-sec" data-sec="capabilities"><h3>Other capabilities</h3><p>Everything else the builder can do, each with its demo.</p>` +
    `<input type="search" class="sg-capsearch" placeholder="Search capabilities" aria-label="Search capabilities">` +
    `<div class="sg-capbody">${buildCapSection('')}</div></section>`;
  body.innerHTML = h;
  if (!ph) {
    const vw = innerWidth, vh = innerHeight;
    const panel = $('panel'), composer = $('composer');
    if (panel && composer) {
      const pr = panel.getBoundingClientRect(), cr = composer.getBoundingClientRect();
      const w = Math.min(640, pr.left - 40), hh = Math.min(620, vh - 90);
      Object.assign(box.style, {right: (vw - pr.left + 12) + 'px', width: w + 'px', height: hh + 'px',
                               top: Math.max(64, cr.bottom - hh) + 'px'});
    }
  }
  document.body.append(shade, box);
  pk = {shade, box};
  box.querySelector('.sg-pclose').onclick = closePicker;
  box.addEventListener('keydown', e => { if (e.key === 'Escape') { closePicker(); ta.focus() } });
  const tabs = [...box.querySelectorAll('[data-tab]')], secs = [...body.querySelectorAll('[data-sec]')];
  const tabRow = box.querySelector('.sg-tabs');
  const setTab = f => tabs.forEach(t => { const on = t.dataset.tab === f; t.classList.toggle('on', on);
    if (on && (t.offsetLeft < tabRow.scrollLeft || t.offsetLeft + t.offsetWidth > tabRow.scrollLeft + tabRow.clientWidth))
      tabRow.scrollLeft = t.offsetLeft - 24 });
  const top = s => s.offsetTop - body.offsetTop - 2;
  tabs.forEach(t => t.onclick = () => { const s = body.querySelector(`[data-sec="${t.dataset.tab}"]`);
    body.scrollTo({top: top(s)}); setTab(t.dataset.tab) });
  body.addEventListener('scroll', () => { let cur = secs[0]; for (const s of secs) if (top(s) - 48 <= body.scrollTop) cur = s;
    if (body.scrollTop + body.clientHeight >= body.scrollHeight - 4) cur = secs[secs.length - 1]; setTab(cur.dataset.sec) });
  body.style.scrollBehavior = 'auto'; body.scrollTop = top(body.querySelector(`[data-sec="${fam}"]`)); body.style.scrollBehavior = '';
  setTab(fam);
  const wireCards = root => { for (const c of root.querySelectorAll('.sg-gcard')) {
    c.onmouseenter = () => { c.classList.add('sg-looping'); c.querySelector('video')?.play().catch(() => {}) };
    c.onmouseleave = () => { c.classList.remove('sg-looping'); c.querySelector('video')?.pause() };
  } };
  wireCards(body);
  const capSearch = box.querySelector('.sg-capsearch'), capBody = box.querySelector('.sg-capbody');
  const renderCapBody = () => { capBody.innerHTML = buildCapSection(capSearch.value); wireCards(capBody) };
  capSearch.addEventListener('input', renderCapBody);
  capBody.addEventListener('click', e => {
    const t = e.target.closest('[data-togglefam]');
    if (!t) return;
    const fam = t.dataset.togglefam;
    if (expandedFamilies.has(fam)) expandedFamilies.delete(fam); else expandedFamilies.add(fam);
    renderCapBody();
  });
  body.addEventListener('click', e => {
    const p = e.target.closest('[data-play]');
    if (p) { const [f, ...id] = p.dataset.play.split(':'); play({family: f, id: id.join(':')}); return }
    const g = e.target.closest('[data-pick]');
    if (!g) return;
    if (ph && g.classList.contains('sg-gcard') && !g.classList.contains('sg-sel')) {
      body.querySelectorAll('.sg-sel').forEach(x => { x.classList.remove('sg-sel', 'sg-looping'); x.querySelector('.sg-usepill')?.remove() });
      g.classList.add('sg-sel', 'sg-looping'); g.querySelector('video')?.play().catch(() => {});
      const u = el('span', 'sg-usepill', 'Use');
      Object.assign(u.style, {position: 'absolute', left: '6px', bottom: '6px', background: '#fff', color: '#111',
                             borderRadius: '14px', padding: '4px 12px', fontWeight: 800, fontSize: '12px', zIndex: 3});
      g.querySelector('.sg-thumb').append(u);
      return;
    }
    const [f, ...id] = g.dataset.pick.split(':'), k = f + ':' + id.join(':');
    const it = shown.find(x => keyOf(x) === k) || {family: f, id: id.join(':'), replace: null};
    closePicker();
    pick(it);
  });
  if (document.activeElement !== ta) box.focus({preventScroll: true});
}

/* ---- start ---- */
async function start() {
  if (!mount()) return;
  noteCapabilityIds = capChipEntries;
  noteAssetIds = assetPickEntries;
  restorePickedCapIds = entries => {
    pickedCapIds = [...new Set((entries || []).map(e => typeof e === 'string' ? e : e.id))];
    capValues = {}; capCardsKey = null;
    for (const e of entries || []) if (e && typeof e === 'object' && e.settings) capValues[e.id] = {...e.settings};
  };
  restorePickedAssetIds = assets => {
    pickedAssetIds = {fonts: [...new Set(assets?.fonts || [])], sfx: [...new Set(assets?.sfx || [])],
                      music: [...new Set(assets?.music || [])]};
  };
  // Loaded eagerly (not only once the model/debounce asks for it): a typed #id becomes
  // a chip as soon as the catalog is in, whether or not the AI suggest model is on.
  loadCatalog().then(() => { indexCatalog(); renderCapChips() });
  await ensureModel();
}
start();
})();

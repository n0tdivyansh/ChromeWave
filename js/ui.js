'use strict';
/* ============================================================
   UI: menu screens with keyboard navigation
   ============================================================ */
(function (TG) {
  const U = TG.U;
  const UI = (TG.UI = { cur: null, capture: null });
  const S = () => TG.Save.data;
  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));
  const root = () => document.getElementById('ui');
  const SCREENS = {};
  UI.SCREENS = SCREENS;

  /* ---------- Core ---------- */
  UI.init = function () {
    TG.Input.on((e, code) => UI.onKey(e, code));
  };

  UI.show = function (name, params) {
    const def = SCREENS[name];
    if (!def) return;
    if (UI.cur && UI.cur.leave) { try { UI.cur.leave(); } catch (e) { /* ok */ } }
    UI.capture = null;
    const r = root();
    r.innerHTML = '';
    const el = document.createElement('section');
    el.className = 'screen scr-' + name + (def.studio ? ' studio' : '') + (def.overlay ? ' overlay' : '');
    r.appendChild(el);
    const ctx = { name, params: params || {}, el, def, focused: null, modal: null };
    UI.cur = ctx;
    document.body.classList.toggle('menu', def.dim !== false);
    document.body.classList.toggle('studio-on', !!def.studio);
    def.render(ctx);
    UI.wire(el);
    const first = ctx.initial ? $(ctx.initial, el) : null;
    UI.focus(first || UI.focusables(ctx)[0]);
    if (TG.Game && TG.Game.onScreen) TG.Game.onScreen(name, def);
  };
  UI.refresh = function (keepSel) {
    const ctx = UI.cur;
    if (!ctx) return;
    const idx = ctx.focused ? ctx.focused.dataset.key : null;
    const scroll = {};
    $$('[data-scroll]', ctx.el).forEach((s) => { scroll[s.dataset.scroll] = s.scrollTop; });
    ctx.el.innerHTML = '';
    ctx.modal = null;
    ctx.def.render(ctx);
    UI.wire(ctx.el);
    $$('[data-scroll]', ctx.el).forEach((s) => { if (scroll[s.dataset.scroll] != null) s.scrollTop = scroll[s.dataset.scroll]; });
    const sel = keepSel || (idx != null ? '[data-key="' + idx + '"]' : null);
    const el = sel ? $(sel, ctx.el) : null;
    UI.focus(el || UI.focusables(ctx)[0], true);
  };
  UI.hide = function () {
    if (UI.cur && UI.cur.leave) { try { UI.cur.leave(); } catch (e) { /* ok */ } }
    root().innerHTML = '';
    UI.cur = null;
    UI.capture = null;
    document.body.classList.remove('menu', 'studio-on');
  };
  UI.wire = function (el) {
    $$('[data-nav]', el).forEach((n) => {
      if (n._wired) return;
      n._wired = true;
      n.addEventListener('mouseenter', () => { if (UI.cur && (!UI.cur.modal || UI.cur.modal.contains(n))) UI.focus(n); });
    });
    $$('[data-arrow]', el).forEach((a) => {
      if (a._wired) return;
      a._wired = true;
      a.addEventListener('click', (e) => {
        e.stopPropagation();
        const row = a.closest('[data-nav]');
        if (row && row._adjust) { row._adjust(+a.dataset.arrow); TG.Audio.play('nav'); }
      });
    });
  };
  UI.focusables = function (ctx) {
    const scope = ctx.modal || ctx.el;
    return $$('[data-nav]', scope).filter((n) => n.offsetParent !== null && !n.hasAttribute('data-off'));
  };
  UI.focus = function (el, silent) {
    const ctx = UI.cur;
    if (!ctx || !el) return;
    if (ctx.focused && ctx.focused !== el) ctx.focused.classList.remove('focus');
    ctx.focused = el;
    el.classList.add('focus');
    if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    if (ctx.onFocus) ctx.onFocus(el, silent);
  };
  UI.move = function (dir) {
    const ctx = UI.cur;
    const list = UI.focusables(ctx);
    const cur = ctx.focused;
    if (!cur || list.indexOf(cur) < 0) { UI.focus(list[0]); return; }
    const r0 = cur.getBoundingClientRect();
    const c0x = r0.left + r0.width / 2, c0y = r0.top + r0.height / 2;
    let best = null, bs = Infinity;
    const horiz = dir === 'left' || dir === 'right';
    // left/right stay in the same row; up/down prefer the same column, then the nearest item
    for (const sameLine of horiz ? [true] : [true, false]) {
      for (const el of list) {
        if (el === cur) continue;
        const r = el.getBoundingClientRect();
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        const dx = cx - c0x, dy = cy - c0y;
        if (sameLine && (horiz ? r.bottom <= r0.top || r.top >= r0.bottom : r.right <= r0.left || r.left >= r0.right)) continue;
        // cross distance: the nearer of centre-to-centre and edge-to-edge alignment, so a left-aligned item wins over a centred one
        const crossV = Math.min(Math.abs(dx), Math.abs(r.left - r0.left)), crossH = Math.min(Math.abs(dy), Math.abs(r.top - r0.top));
        let main, cross;
        // a candidate must lie past the current item's edge (a focused tile's small lift doesn't count as "below")
        if (dir === 'up') { if (r.bottom > r0.top + 8) continue; main = -dy; cross = crossV; }
        else if (dir === 'down') { if (r.top < r0.bottom - 8) continue; main = dy; cross = crossV; }
        else if (dir === 'left') { if (r.right > r0.left + 8) continue; main = -dx; cross = crossH; }
        else { if (r.left < r0.right - 8) continue; main = dx; cross = crossH; }
        const sc = main + cross * 2.4;
        if (sc < bs) { bs = sc; best = el; }
      }
      if (best) break;
    }
    if (!best && (dir === 'up' || dir === 'down') && ctx.wrap !== false) {
      const col = list.filter((el) => Math.abs(el.getBoundingClientRect().left - r0.left) < 40);
      if (col.length > 1) best = dir === 'down' ? col[0] : col[col.length - 1];
      if (best === cur) best = null;
    }
    if (best) { UI.focus(best); TG.Audio.play('nav'); }
  };
  UI.step = function (d) {
    const ctx = UI.cur;
    const list = UI.focusables(ctx);
    if (!list.length) return;
    let i = list.indexOf(ctx.focused);
    i = i < 0 ? 0 : (i + d + list.length) % list.length;
    UI.focus(list[i]);
    TG.Audio.play('nav');
  };
  UI.onKey = function (e, code) {
    if (!UI.cur) return false;
    TG.Audio.init();
    if (UI.capture) return UI.capture(code, e);
    const ctx = UI.cur;
    if (ctx.onKey && ctx.onKey(code, e) === true) return true;
    const f = ctx.focused;
    switch (code) {
      case 'ArrowUp': case 'KeyW': if (ctx.linear && !ctx.modal) UI.step(-1); else UI.move('up'); return true;
      case 'ArrowDown': case 'KeyS': if (ctx.linear && !ctx.modal) UI.step(1); else UI.move('down'); return true;
      case 'ArrowLeft': case 'KeyA':
        if (f && f._adjust) { f._adjust(-1); TG.Audio.play('nav'); return true; }
        UI.move('left'); return true;
      case 'ArrowRight': case 'KeyD':
        if (f && f._adjust) { f._adjust(1); TG.Audio.play('nav'); return true; }
        UI.move('right'); return true;
      case 'Enter': case 'NumpadEnter': case 'Space':
        if (f) { if (!f._silent) TG.Audio.play('select'); f.click(); }
        return true;
      case 'Backspace':
        UI.back(); return true;
      default: return false;
    }
  };
  UI.back = function () {
    const ctx = UI.cur;
    if (!ctx) return;
    if (ctx.modal) { UI.closeModal(); TG.Audio.play('back'); return; }
    if (ctx.onBack) { TG.Audio.play('back'); ctx.onBack(); }
  };
  UI.modal = function (html, buttons, opt) {
    const ctx = UI.cur;
    opt = opt || {};
    const wrap = U.el('div', 'modal-wrap');
    wrap.innerHTML = '<div class="modal">' + html + '<div class="modal-btns">' + buttons.map((b, i) => '<button class="btn ' + (b.cls || '') + '" data-nav data-mb="' + i + '">' + b.label + '</button>').join('') + '</div></div>';
    ctx.el.appendChild(wrap);
    ctx.prevFocus = ctx.focused;
    ctx.modal = wrap;
    buttons.forEach((b, i) => { $('[data-mb="' + i + '"]', wrap).addEventListener('click', () => { UI.closeModal(); if (b.fn) b.fn(); }); });
    UI.wire(wrap);
    UI.focus($('[data-mb="' + (opt.focus || 0) + '"]', wrap), true);
  };
  UI.closeModal = function () {
    const ctx = UI.cur;
    if (!ctx || !ctx.modal) return;
    ctx.modal.remove();
    ctx.modal = null;
    if (ctx.prevFocus && ctx.el.contains(ctx.prevFocus)) UI.focus(ctx.prevFocus, true);
    else UI.focus(UI.focusables(ctx)[0], true);
  };
  UI.toast = function (text, kind) {
    const t = document.getElementById('toast');
    const n = U.el('div', 'toast ' + (kind || ''), text);
    t.appendChild(n);
    setTimeout(() => n.classList.add('out'), 2200);
    setTimeout(() => n.remove(), 2700);
  };

  /* ---------- Reusable pieces ---------- */
  const esc = U.esc;
  const money = (n) => U.money(n);
  function header(title, eyebrow) {
    return '<header class="head"><div class="head-title">' + (eyebrow ? '<span class="eyebrow">' + esc(eyebrow) + '</span>' : '') +
      '<h1>' + esc(title) + '</h1></div><div class="wallet"><span class="wallet-label">Balance</span><span class="wallet-val">' + money(S().money) + '</span></div></header>';
  }
  function hints(list) {
    return '<footer class="hints">' + list.map((h) => '<span' + (h[0] === 'Backspace' ? ' data-back' : '') + '><kbd' + (/[←↑→↓]/.test(h[0]) ? ' class="ar"' : '') + '>' + h[0] + '</kbd>' + esc(h[1]) + '</span>').join('') + '</footer>';
  }
  const HINTS = [['↑↓←→', 'Navigate'], ['Enter', 'Select'], ['Backspace', 'Back']];
  function speedTxt(kmh) {
    return S().settings.units === 'mph' ? Math.round(kmh * 0.6214) + ' mph' : Math.round(kmh) + ' km/h';
  }
  function bars(v, v2) {
    let h = '';
    for (let i = 0; i < 20; i++) {
      const t = (i + 0.5) / 20;
      h += '<i class="' + (t <= v ? 'on' : v2 && t <= v2 ? 'nx' : '') + '"></i>';
    }
    return h;
  }
  function statBlock(st, st2) {
    const b = TG.statBars(st), b2 = st2 ? TG.statBars(st2) : null;
    const row = (label, key, val, val2) => '<div class="stat"><span class="stat-l">' + label + '</span><span class="stat-bar">' + bars(b[key], b2 && b2[key] > b[key] + 0.001 ? b2[key] : 0) + '</span><span class="stat-v">' + val + (val2 && val2 !== val ? ' <em><i class="ar">→</i> ' + val2 + '</em>' : '') + '</span></div>';
    const grip = (s) => Math.round(U.clamp((s.grip - 0.9) / 0.65, 0, 1) * 100) + '';
    return '<div class="stats">' +
      row('Speed', 'speed', speedTxt(st.top), st2 ? speedTxt(st2.top) : null) +
      row('0-100', 'accel', st.t0100.toFixed(1) + ' s', st2 ? st2.t0100.toFixed(1) + ' s' : null) +
      row('Handling', 'grip', grip(st) + '/100', st2 ? grip(st2) + '/100' : null) +
      row('Nitro', 'nitro', st.nitroTank.toFixed(1) + ' s tank', st2 ? st2.nitroTank.toFixed(1) + ' s tank' : null) + '</div>';
  }
  function adjRow(key, label, valueHtml, fn, extraCls) {
    return { html: '<div class="row ' + (extraCls || '') + '" data-nav data-key="' + key + '" data-adj="1"><span class="row-label">' + label + '</span><span class="row-val"><i class="arr" data-arrow="-1">◀</i><b class="row-b">' + valueHtml + '</b><i class="arr" data-arrow="1">▶</i></span></div>', key, fn };
  }
  function studioHeader(title, sub) {
    return '<header class="gar-head"><div><span class="gar-eyebrow">' + esc(sub) + '</span>' +
      '<h1 class="gar-title">' + esc(title) + '</h1></div>' +
      '<div class="mm-wallet"><small>Balance</small><b>' + money(S().money) + '</b></div></header>';
  }
  function bindAdj(el, rows) {
    rows.forEach((r) => {
      const n = $('[data-key="' + r.key + '"]', el);
      if (n) n._adjust = r.fn;
    });
  }
  // showroom: the 3D car spins slowly on the turntable (if WebGL is available)
  UI.showAng = 2.2;
  function showroomInto(canvas, model, color, det) {
    if (canvas._raf) cancelAnimationFrame(canvas._raf);
    requestAnimationFrame(() => {
      const r = canvas.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.max(200, Math.round(r.width * dpr));
      canvas.height = Math.max(100, Math.round(r.height * dpr));
      let last = performance.now();
      const frame = (t) => {
        if (!canvas.isConnected) return;
        const CG = TG.CarGL;
        const gl = CG && CG.has(model.id);
        if (gl) UI.showAng += Math.min(0.1, (t - last) / 1000) * 0.3;
        last = t;
        TG.Art.showroom(canvas, model, color, gl ? { angle: UI.showAng, det } : {});
        if (gl || (CG && CG.ok && !CG.ready)) canvas._raf = requestAnimationFrame(frame);
      };
      frame(last);
    });
  }
  function flagCanvas(id, w, h) {
    const c = U.canvas(w * 2, h * 2);
    TG.Art.flag(c.getContext('2d'), id, 0, 0, w * 2, h * 2);
    c.className = 'flag';
    c.style.width = w + 'px'; c.style.height = h + 'px';
    return c;
  }
  function thumbInto(canvas, themeId) {
    const img = TG.Art.themePreview(TG.THEMES[themeId], canvas.width, canvas.height);
    canvas.getContext('2d').drawImage(img, 0, 0);
  }
  // cars sorted by price (TG.CARS order stays as is: the cups use its indices)
  const byPrice = () => TG._byPrice || (TG._byPrice = TG.CARS.slice().sort((a, b) => a.price - b.price || a.index - b.index));
  const ownedIds = () => byPrice().filter((c) => S().cars[c.id]).map((c) => c.id);
  function unlockedTracks() {
    const list = [];
    TG.CUPS.forEach((cup, ci) => { if (ci < S().unlocked) cup.tracks.forEach((t) => list.push(t.id)); });
    return list;
  }
  function carCfg(carId, profile, name) {
    const c = S().cars[carId];
    return { carId, color: c.color, det: c.det ? Object.assign({}, c.det) : null, up: Object.assign({}, c.up), profile, manual: S().settings.trans === 'manual', name };
  }
  UI.carCfg = carCfg;

  /* ================= PANTALLAS ================= */
  SCREENS.title = {
    overlay: false,
    render(ctx) {
      ctx.el.innerHTML =
        '<div class="title-wrap">' +
        '<div class="logo"><div class="logo-top">CHROME</div><div class="logo-main">WAVE</div>' +
        '</div>' +
        '<button class="press" data-nav>Press <kbd>Enter</kbd> to race</button>' +
        '<button class="press press-menu" data-nav>Menu</button></div>' +
        '<div class="title-foot"><span><kbd class="ar">↑↓←→</kbd> / <kbd>WASD</kbd> drive</span><span><kbd>Space</kbd> nitro</span><span><kbd>P</kbd> pause</span><span><kbd>M</kbd> music</span></div>';
      // one click straight into a race (the Arcade Race setup and the player's car)
      $('.press', ctx.el).addEventListener('click', () => {
        const q = S().quick;
        TG.Audio.init();
        TG.Game.startRace({ mode: 'quick', trackId: q.track, laps: q.laps, rivals: q.rivals, players: [carCfg(S().active, 'solo', 'You')] });
      });
      $('.press-menu', ctx.el).addEventListener('click', () => {
        TG.Audio.init();
        TG.Music.play('menu');
        UI.show('main');
      });
    },
  };

  // Line icons for the main menu (24×24, drawn with currentColor)
  const ICONS = {
    career: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3.2 3.6 3.2 14.4 0 18M12 3c-3.2 3.6-3.2 14.4 0 18"/>',
    quick: '<path d="M5 21V4h13l-2.5 4.5L18 13H5"/><path d="M9 4v9M13 4v9M5 8.5h11"/>',
    versus: '<path d="M3 5l5 14 5-14M21 7c-1-1.5-2.5-2-4-2-2 0-3.5 1-3.5 3 0 4.5 7.5 2.5 7.5 7 0 2-1.5 3-3.5 3-1.5 0-3-.5-4-2"/>',
    time: '<circle cx="12" cy="13.5" r="7.5"/><path d="M12 13.5V9.5M9.5 2.5h5M12 2.5V6M18.5 6.5l1.5-1.5"/>',
    garage: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.3-.6-.6-2.3z"/>',
    dealer: '<path d="M3 16.5l1.8-5.5A2 2 0 0 1 6.7 9.6h10.6a2 2 0 0 1 1.9 1.4l1.8 5.5v2H3z"/><circle cx="7.5" cy="16.5" r="1.3"/><circle cx="16.5" cy="16.5" r="1.3"/>',
    options: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    shop: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><path d="M1 14h6M9 8h6M17 16h6"/>',
    paint: '<path d="M12 2.7S5 10.7 5 15a7 7 0 0 0 14 0c0-4.3-7-12.3-7-12.3z"/>',
    keys: '<rect x="2.5" y="6" width="19" height="12" rx="1"/><path d="M6 10h1M10 10h1M14 10h1M18 10h1M7 14h10"/>',
    export: '<path d="M12 15V3M7 8l5-5 5 5M4 15v5h16v-5"/>',
    import: '<path d="M12 3v12M7 10l5 5 5-5M4 15v5h16v-5"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  };
  const icon = (k) => '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">' + ICONS[k] + '</svg>';

  SCREENS.main = {
    render(ctx) {
      const modes = [
        ['career', 'World Tour', '8 cups, 32 tracks and big prize money. Podium every cup to unlock the next.'],
        ['quick', 'Arcade Race', 'Any unlocked track, your laps, your rivals. Jump straight in.'],
        ['versus', 'Head to Head', 'Split screen on one keyboard. Settle it on the track.'],
        ['time', 'Time Attack', 'Just you, the clock and the ghost of your best lap.'],
      ];
      const utils = [
        ['garage', 'Garage', 'Your rides, tuning and detailing.'],
        ['dealer', 'Showroom', 'Rovenza, Arvane, Lindqvist, Hoshida and more.'],
        ['options', 'Settings', 'Sound, graphics and controls.'],
      ];
      const all = modes.concat(utils);
      const model = TG.Save.activeModel(), car = TG.Save.car();
      const st = TG.carStats(model, car.up);
      const d = S();
      ctx.el.innerHTML =
        '<header class="mm-top"><div class="mm-logo"><span>Chrome</span><b>wave</b></div>' +
        '<div class="mm-wallet"><small>Balance</small><b>' + money(d.money) + '</b></div></header>' +
        '<section class="mm-hero">' +
          '<div class="mm-pitch"><div class="mm-kicker"></div><h1 class="mm-title"></h1><p class="mm-desc"></p>' +
            '<div class="mm-chips"><span><b>' + d.stats.races + '</b>races</span><span><b>' + d.stats.wins + '</b>wins</span>' +
            '<span><b>' + Object.keys(d.cars).length + '/' + TG.CARS.length + '</b>cars</span></div></div>' +
          '<div class="mm-ride"><canvas class="mm-car"></canvas><div class="mm-tag"><span>Your ride</span>' +
            '<small>' + esc(model.brand) + '</small><b>' + esc(model.name) + '</b>' +
            '<em><i><small>Top</small>' + speedTxt(st.top) + '</i><i><small>0-100</small>' + st.t0100.toFixed(1) + ' s</i></em></div></div>' +
        '</section>' +
        '<nav class="mm-modes">' + modes.map((m, i) =>
          '<button class="mm-tile" data-nav data-key="' + m[0] + '"><span class="mm-num">0' + (i + 1) + '</span>' + icon(m[0]) + '<span class="mm-name">' + m[1] + '</span></button>').join('') + '</nav>' +
        '<nav class="mm-utils">' + utils.map((m) =>
          '<button class="mm-util" data-nav data-key="' + m[0] + '">' + icon(m[0]) + '<span>' + m[1] + '</span></button>').join('') + '</nav>' +
        hints([['↑↓←→', 'Navigate'], ['Enter', 'Select'], ['Backspace', 'Title screen']]);
      all.forEach((it) => $('[data-key="' + it[0] + '"]', ctx.el).addEventListener('click', () => UI.show(it[0])));
      showroomInto($('.mm-car', ctx.el), model, car.color, car.det);
      // the hero text follows whichever option is highlighted
      const kicker = $('.mm-kicker', ctx.el), title = $('.mm-title', ctx.el), desc = $('.mm-desc', ctx.el), pitch = $('.mm-pitch', ctx.el);
      ctx.onFocus = (el) => {
        const i = all.findIndex((it) => it[0] === el.dataset.key);
        if (i < 0 || title.textContent === all[i][1]) return;
        kicker.textContent = i < modes.length ? 'Mode 0' + (i + 1) : 'Pit lane';
        title.textContent = all[i][1];
        desc.textContent = all[i][2];
        pitch.classList.remove('swap'); void pitch.offsetWidth; pitch.classList.add('swap');
      };
      ctx.onBack = () => UI.show('title');
      ctx.initial = ctx.params.focus ? '[data-key="' + ctx.params.focus + '"]' : null;
    },
  };

  /* ---------- World Tour: cup list + live preview of the focused cup ---------- */
  SCREENS.career = {
    render(ctx) {
      ctx.linear = true;
      const d = S(), n = TG.CUPS.length;
      const TROPHY = ['', 'Gold', 'Silver', 'Bronze'];
      if (ctx.sel == null) ctx.sel = ctx.params.i != null ? ctx.params.i : Math.min(d.unlocked - 1, n - 1);
      const status = (i) => {
        const st = d.cups[i];
        if (i >= d.unlocked) return '<b class="wt-st lock">Locked</b>';
        if (st.run) return '<b class="wt-st live">Race ' + (st.run.race + 1) + '/4</b>';
        if (st.trophy) return '<b class="wt-st g' + st.trophy + '">' + TROPHY[st.trophy] + '</b>';
        return '<b class="wt-st">Open</b>';
      };
      const preview = (i) => {
        const cup = TG.CUPS[i], locked = i >= d.unlocked, st = d.cups[i];
        return '<div class="wt-pv"><canvas class="wt-thumb" width="640" height="300"></canvas>' + (locked ? '<div class="wt-lock">Locked</div>' : '') + '</div>' +
          '<span>Cup ' + (i + 1) + ' of ' + n + '</span><b class="wt-name"><i class="flag-slot"></i>' + esc(cup.name) + '</b>' +
          '<div class="wt-facts">' + [['1st prize', money(cup.prize)], ['Rivals', speedTxt(TG.cupSpeed(cup))], ['Trophy', st.trophy ? TROPHY[st.trophy] : 'None yet']]
            .map((x) => '<div><span>' + x[0] + '</span><b>' + x[1] + '</b></div>').join('') + '</div>' +
          '<ol class="wt-tracks">' + cup.tracks.map((t) => '<li>' + esc(t.name) + '</li>').join('') + '</ol>' +
          '<p class="small muted">' + (locked ? 'Finish on the podium in the ' + esc(TG.CUPS[i - 1].name) + ' to unlock it.' : st.run ? 'In progress: race ' + (st.run.race + 1) + ' of 4 is next.' : 'A top-3 finish unlocks the next cup. Replay any open cup to earn more.') + '</p>';
      };
      const fill = () => {
        const box = $('.wt-prev', ctx.el);
        box.innerHTML = preview(ctx.sel);
        thumbInto($('.wt-thumb', box), TG.CUPS[ctx.sel].tracks[0].theme);
        $('.flag-slot', box).appendChild(flagCanvas(TG.CUPS[ctx.sel].flag, 24, 16));
      };
      ctx.el.innerHTML = header('World Tour', Math.min(d.unlocked, n) + ' of ' + n + ' cups open') +
        '<div class="wt"><div class="hg-box wt-prev"></div><div class="wt-list">' + TG.CUPS.map((cup, i) =>
          '<button class="wt-cup' + (i >= d.unlocked ? ' locked' : '') + '" data-nav data-key="cup' + i + '" data-i="' + i + '"><span class="wt-n">' + String(i + 1).padStart(2, '0') + '</span>' +
          '<span class="flag-slot"></span><span class="wt-cn">' + esc(cup.name) + '</span>' + status(i) + '</button>').join('') + '</div></div>' +
        hints([['↑↓', 'Choose cup'], ['Enter', 'Open'], ['Backspace', 'Back']]);
      fill();
      $$('.wt-cup', ctx.el).forEach((b) => {
        const i = +b.dataset.i;
        $('.flag-slot', b).appendChild(flagCanvas(TG.CUPS[i].flag, 24, 16));
        b.addEventListener('click', () => {
          if (i >= S().unlocked) { TG.Audio.play('error'); UI.toast('Cup locked: finish on the podium in the ' + TG.CUPS[i - 1].name + '.', 'warn'); return; }
          UI.show('cup', { i });
        });
      });
      ctx.onFocus = (el) => { const i = el.dataset.i; if (i != null && +i !== ctx.sel) { ctx.sel = +i; fill(); } };
      ctx.onBack = () => UI.show('main', { focus: 'career' });
      ctx.initial = '[data-key="cup' + ctx.sel + '"]';
    },
  };

  function standings(run) {
    const rows = run.drivers.map((dv) => ({ name: dv.name, car: TG.CAR[dv.carId], pts: run.points[dv.id] || 0, me: false }));
    rows.push({ name: 'You', car: TG.Save.activeModel(), pts: run.points.player || 0, me: true });
    rows.sort((a, b) => b.pts - a.pts || (a.me ? -1 : 1));
    return rows;
  }
  UI.standings = standings;

  function carPicker(ctx, key, label, getId, setId) {
    const ids = ownedIds();
    const id = getId();
    const m = TG.CAR[id];
    return adjRow(key, label, esc(m.brand + ' ' + m.name), (dlt) => {
      const list = ownedIds();
      let i = list.indexOf(getId());
      i = (i + dlt + list.length) % list.length;
      setId(list[i]);
      TG.Save.save();
      UI.refresh();
    }, ids.length < 2 ? 'single' : '');
  }

  // rival level (1-10) for a track, based on progress and the chosen difficulty
  function rivalLevel(t) {
    const D = TG.DIFFICULTY[S().settings.difficulty] || TG.DIFFICULTY.normal;
    return 1 + Math.round(U.clamp(TG.raceLevel(t) + D.off, 0, 1) * 9);
  }
  function lvlBar(t) {
    const n = rivalLevel(t);
    const D = TG.DIFFICULTY[S().settings.difficulty] || TG.DIFFICULTY.normal;
    const up = TG.aiUpgrades(U.clamp(TG.raceLevel(t) + D.off, 0, 1));
    const parts = up.motor + up.turbo + up.tires > 0 ? '<em>Engine ' + up.motor + ' · Turbo ' + up.turbo + ' · Tires ' + up.tires + '</em>' : '<em>Stock parts</em>';
    return '<span class="lvl" title="Rival level and parts">Rivals <i style="--l:' + n * 10 + '%"></i><b>' + n + '/10</b>' + parts + '</span>';
  }

  SCREENS.cup = {
    render(ctx) {
      ctx.linear = true;
      const i = ctx.params.i;
      const cup = TG.CUPS[i];
      const st = S().cups[i];
      const run = st.run;
      const model = TG.Save.activeModel(), car = TG.Save.car();
      const cst = TG.carStats(model, car.up);
      const nextIdx = run ? run.race : 0;
      const recs = S().records;
      // the route: one card per race, left to right
      const route = cup.tracks.map((t, ti) => {
        const th = TG.THEMES[t.theme];
        const done = run && ti < run.race;
        const res = run && run.results[ti];
        const rec = recs[t.id];
        const status = done ? '<b class="rc-res">' + U.ord(res) + '</b>' : ti === nextIdx ? '<b class="rc-next">Next</b>' : rec && rec.lap ? '<b>' + U.timeShort(rec.lap) + '</b>' : '';
        return '<div class="rc' + (ti === nextIdx ? ' next' : '') + (done ? ' done' : '') + '"><canvas class="rc-thumb" width="320" height="180" data-theme="' + t.theme + '"></canvas>' +
          '<div class="rc-top"><span>Race ' + (ti + 1) + '</span>' + status + '</div><div class="rc-name">' + esc(t.name) + '</div>' +
          '<div class="rc-meta">' + TG.TIME_LABEL[th.time] + ' · ' + TG.WEATHER_LABEL[th.weather] + ' · 3 laps</div>' + lvlBar(t) + '</div>';
      }).join('');
      let left = '';
      if (run) {
        const rows = standings(run), me = rows.findIndex((r) => r.me);
        const shown = rows.slice(0, 6).map((r, k) => [r, k]);
        if (me >= 6) shown.push([rows[me], me]);
        left = '<div class="hg-box cup-stand"><span>Cup standings</span><table class="tbl"><tbody>' +
          shown.map(([r, k]) => '<tr class="' + (r.me ? 'me' : '') + '"><td class="pos">' + (k + 1) + '</td><td>' + esc(r.name) + '</td><td class="num">' + r.pts + '</td></tr>').join('') +
          '</tbody></table></div>';
      } else {
        const pct = TG.ECON.prizePct;
        const cell = (k, v) => '<div><span>' + U.ord(k + 1) + '</span><b>' + money(Math.round((cup.prize * v) / 50) * 50) + '</b></div>';
        left = '<div class="hg-box cup-prizes"><span>Prize per race</span><div class="prize-list">' + [0, 1, 2, 3, 4].map((k) => cell(k, pct[k])).join('') + '</div>' +
          '<span>Cup finish bonus</span><div class="prize-list">' + TG.ECON.cupBonus.map((v, k) => cell(k, v)).join('') + '</div>' +
          '<p class="small muted">Points 25-18-15-12-10-8-6-4-2-1 · Coin ' + money(cup.coin) + '</p></div>';
      }
      const pick = carPicker(ctx, 'car', 'Car', () => S().active, (id) => { S().active = id; });
      const next = cup.tracks[nextIdx];
      const grip = Math.round(U.clamp((cst.grip - 0.9) / 0.65, 0, 1) * 100);
      ctx.el.innerHTML = header(cup.name, 'Cup ' + (i + 1) + ' of ' + TG.CUPS.length + (run ? ' · race ' + (run.race + 1) + ' of 4' : '')) +
        '<div class="cupv"><div class="route">' + route + '</div><div class="hg-row">' + left +
        '<div class="hg-box cup-car"><span>Your car</span>' + pick.html + '<div class="cup-car-stats">' +
        [['Top speed', speedTxt(cst.top)], ['0-100', cst.t0100.toFixed(1) + ' s'], ['Handling', grip + '/100']].map((x) => '<div><span>' + x[0] + '</span><b>' + x[1] + '</b></div>').join('') + '</div>' +
        (cst.top < TG.cupSpeed(cup) * 0.97 ? '<p class="warn-txt">Rivals reach ' + speedTxt(TG.cupSpeed(cup)) + ' and upgrade every race. Tune your engine or buy a faster car.</p>' : '') + '</div>' +
        '<div class="hg-box hg-act"><button class="btn primary big" data-nav data-key="go">' + (run ? 'Continue' : 'Start cup') + '</button><div class="cup-nexttrack">' + esc(next.name) + '</div>' +
        (run ? '<button class="btn ghost" data-nav data-key="reset">Restart cup</button>' : '') +
        '<button class="btn ghost" data-nav data-key="garage">Go to garage</button></div></div></div>' +
        hints([['↑↓', 'Navigate'], ['←→', 'Change car'], ['Enter', 'Select'], ['Backspace', 'Back']]);
      bindAdj(ctx.el, [pick]);
      $$('.rc-thumb', ctx.el).forEach((c) => thumbInto(c, c.dataset.theme));
      $('[data-key="go"]', ctx.el).addEventListener('click', () => {
        const d = S();
        if (!d.cups[i].run) {
          const seed = (Date.now() & 0xffff) + i * 97;
          d.cups[i].run = { race: 0, points: {}, results: [], drivers: TG.Race.makeDrivers(cup, 15, seed) };
          TG.Save.save();
        }
        const r = d.cups[i].run;
        TG.Game.startRace({
          mode: 'career', trackId: cup.tracks[r.race].id, laps: 3, rivals: 15, drivers: r.drivers, cupIndex: i,
          players: [carCfg(d.active, 'solo', 'You')],
        });
      });
      const rs = $('[data-key="reset"]', ctx.el);
      if (rs) rs.addEventListener('click', () => UI.modal('<h2>Restart the cup?</h2><p>You will lose the points earned in this cup. The money you won is kept.</p>', [
        { label: 'Restart', cls: 'primary', fn: () => { S().cups[i].run = null; TG.Save.save(); UI.refresh(); } },
        { label: 'Cancel', cls: 'ghost' },
      ], { focus: 1 }));
      $('[data-key="garage"]', ctx.el).addEventListener('click', () => UI.show('garage', { from: { name: 'cup', params: { i } } }));
      ctx.onBack = () => UI.show('career', { i });
      ctx.initial = '[data-key="go"]';
    },
  };

  /* ---------- Arcade Race / Time Attack / Head to Head ---------- */
  function trackPicker(key, getId, setId) {
    const t = TG.TRACKS[getId()];
    const cup = TG.CUPS[t.cup];
    return adjRow(key, 'Track', esc(t.name) + ' <small>' + esc(cup.name) + '</small>', (dl) => {
      const list = unlockedTracks();
      let i = list.indexOf(getId());
      if (i < 0) i = 0;
      i = (i + dl + list.length) % list.length;
      setId(list[i]);
      TG.Save.save();
      UI.refresh();
    });
  }
  function fillPreview(el) {
    $$('.pv', el).forEach((c) => thumbInto(c, c.dataset.theme));
    $$('[data-flag]', el).forEach((s) => s.appendChild(flagCanvas(s.dataset.flag, 24, 16)));
  }
  function ensureTrack(obj) {
    const list = unlockedTracks();
    if (list.indexOf(obj.track) < 0) obj.track = list[0];
  }

  /* ---------- Race setup: step 1 cup carousel, step 2 track carousel + options ---------- */
  const wrap = (i, n) => (i + n) % n;
  function cupCard(i, main) {
    const cup = TG.CUPS[i], locked = i >= S().unlocked;
    const w = main ? 640 : 320, h = main ? 280 : 150;
    return '<div class="tcard ' + (main ? 'main' : 'side') + (locked ? ' locked' : '') + '" data-step="' + (main ? 0 : '') + '">' +
      '<canvas class="pv" width="' + w + '" height="' + h + '" data-theme="' + cup.tracks[0].theme + '"></canvas>' +
      (locked ? '<div class="tc-lock">Locked</div>' : '') +
      '<div class="n"><span class="flag-slot" data-flag="' + cup.flag + '"></span>' + esc(cup.name) + '</div>' +
      (main ? '<div class="tc-meta">' + (locked ? 'Podium in the ' + esc(TG.CUPS[i - 1].name) + ' to unlock' : cup.tracks.length + ' tracks · 1st prize ' + money(cup.prize)) + '</div>' : '') + '</div>';
  }
  function trackCard(t, main) {
    const th = TG.THEMES[t.theme];
    const w = main ? 640 : 320, h = main ? 280 : 150;
    return '<div class="tcard ' + (main ? 'main' : 'side') + '">' +
      '<canvas class="pv" width="' + w + '" height="' + h + '" data-theme="' + t.theme + '"></canvas>' +
      '<div class="n">' + esc(t.name) + '</div>' +
      (main ? '<div class="tc-meta">' + TG.TIME_LABEL[th.time] + ' · ' + TG.WEATHER_LABEL[th.weather] + '</div>' + lvlBar(t) : '') + '</div>';
  }
  // three cards (previous, current, next) inside one focusable row; ←→ or the side cards change the pick
  function carousel(key, prev, cur, next, dots) {
    return '<div class="car3" data-nav data-key="' + key + '" data-adj="1"><i class="arr" data-arrow="-1">◀</i>' +
      prev + cur + next + '<i class="arr" data-arrow="1">▶</i></div><div class="dots2">' + dots + '</div>';
  }
  function wireCarousel(ctx, key, adjust, onEnter) {
    const el = $('[data-key="' + key + '"]', ctx.el);
    el._adjust = adjust;
    el._silent = true;
    const sides = $$('.tcard.side', el);
    sides.forEach((c, k) => c.addEventListener('click', (e) => { e.stopPropagation(); adjust(k === 0 ? -1 : 1); TG.Audio.play('nav'); }));
    el.addEventListener('click', onEnter);
  }

  // Shared setup screen. o: { state, title, rows(q), extra(q), goLabel, go(q), backFocus }
  function setupScreen(ctx, o) {
    ctx.linear = true;
    const q = o.state();
    ensureTrack(q);
    const t = TG.TRACKS[q.track];
    if (!ctx.stage) ctx.stage = ctx.params.stage || 'cup';
    if (ctx.cupSel == null) ctx.cupSel = t.cup;
    const n = TG.CUPS.length;
    if (ctx.stage === 'cup') {
      const i = ctx.cupSel, locked = i >= S().unlocked;
      const dots = TG.CUPS.map((c, k) => '<i class="' + (k === i ? 'on' : k >= S().unlocked ? 'locked' : '') + '"></i>').join('');
      ctx.el.innerHTML = header(o.title, 'Step 1 of 2 · Choose a cup') +
        '<div class="pick">' + carousel('cups', cupCard(wrap(i - 1, n), false), cupCard(i, true), cupCard(wrap(i + 1, n), false), dots) +
        '<button class="btn primary big pick-go" data-nav data-key="next"' + (locked ? ' data-off' : '') + '>' + (locked ? 'Locked' : 'Choose cup') + '</button></div>' +
        hints([['←→', 'Change cup'], ['Enter', 'Choose'], ['Backspace', 'Back']]);
      const choose = () => {
        if (i >= S().unlocked) { TG.Audio.play('error'); UI.toast('Cup locked: finish on the podium in the ' + TG.CUPS[i - 1].name + '.', 'warn'); return; }
        if (TG.TRACKS[q.track].cup !== i) q.track = TG.CUPS[i].tracks[0].id;
        TG.Save.save();
        ctx.stage = 'track';
        UI.refresh('[data-key="track"]');
      };
      wireCarousel(ctx, 'cups', (d) => { ctx.cupSel = wrap(ctx.cupSel + d, n); UI.refresh('[data-key="cups"]'); }, choose);
      $('[data-key="next"]', ctx.el).addEventListener('click', choose);
      fillPreview(ctx.el);
      ctx.onBack = () => UI.show('main', { focus: o.backFocus });
      ctx.initial = '[data-key="cups"]';
      return;
    }
    const cup = TG.CUPS[t.cup], list = cup.tracks, ti = list.indexOf(t);
    const rows = o.rows(q);
    ctx.el.innerHTML = header(o.title, 'Step 2 of 2 · ' + cup.name) +
      '<div class="pick">' + carousel('track', trackCard(list[wrap(ti - 1, list.length)], false), trackCard(t, true), trackCard(list[wrap(ti + 1, list.length)], false),
        list.map((x) => '<i class="' + (x === t ? 'on' : '') + '"></i>').join('')) +
      '<div class="chips">' + rows.map((r) => r.html).join('') + '<button class="btn primary big" data-nav data-key="go">' + o.goLabel + '</button></div>' +
      (o.extra ? '<div class="pick-extra">' + o.extra(q, cup) + '</div>' : '') + '</div>' +
      hints([['↑↓', 'Select'], ['←→', 'Change'], ['Enter', 'Race'], ['Backspace', 'Cups']]);
    bindAdj(ctx.el, rows);
    const go = $('[data-key="go"]', ctx.el);
    wireCarousel(ctx, 'track', (d) => { q.track = list[wrap(ti + d, list.length)].id; TG.Save.save(); UI.refresh('[data-key="track"]'); }, () => UI.focus(go));
    go.addEventListener('click', () => o.go(q));
    fillPreview(ctx.el);
    ctx.onBack = () => { ctx.stage = 'cup'; ctx.cupSel = t.cup; UI.refresh('[data-key="cups"]'); };
    ctx.initial = ctx.initial || '[data-key="track"]';
  }

  SCREENS.quick = {
    render(ctx) {
      setupScreen(ctx, {
        state: () => S().quick, title: 'Arcade Race', backFocus: 'quick', goLabel: 'Race!',
        rows: (q) => [
          adjRow('laps', 'Laps', q.laps, (d) => { q.laps = U.clamp(q.laps + d, 1, 6); TG.Save.save(); UI.refresh(); }),
          adjRow('rivals', 'Rivals', q.rivals, (d) => { const o = [0, 3, 5, 7, 9, 11, 15]; let i = o.indexOf(q.rivals); i = U.clamp((i < 0 ? 5 : i) + d, 0, o.length - 1); q.rivals = o[i]; TG.Save.save(); UI.refresh(); }),
          carPicker(ctx, 'car', 'Car', () => S().active, (id) => { S().active = id; }),
        ],
        extra: (q, cup) => '<p class="small muted">Arcade race prize: 75% of the ' + esc(cup.name) + ' prize (1st: ' + money(Math.round((cup.prize * 0.75) / 50) * 50) + ') plus any coins you collect.</p>',
        go: (q) => TG.Game.startRace({ mode: 'quick', trackId: q.track, laps: q.laps, rivals: q.rivals, players: [carCfg(S().active, 'solo', 'You')] }),
      });
    },
  };

  SCREENS.time = {
    render(ctx) {
      setupScreen(ctx, {
        state: () => S().quick, title: 'Time Attack', backFocus: 'time', goLabel: 'Hit the track',
        rows: () => [carPicker(ctx, 'car', 'Car', () => S().active, (id) => { S().active = id; })],
        extra: (q) => {
          const rec = S().records[q.track] || {};
          return '<div class="card records"><div class="card-eyebrow">Track records</div><div class="rec"><span>Best lap</span><b>' + U.time(rec.lap) + '</b></div>' +
            '<div class="rec"><span>Best race (3 laps)</span><b>' + U.time(rec.race) + '</b></div>' +
            (rec.lapCar && TG.CAR[rec.lapCar] ? '<div class="rec"><span>Record car</span><b>' + esc(TG.CAR[rec.lapCar].brand + ' ' + TG.CAR[rec.lapCar].name) + '</b></div>' : '') +
            '<div class="rec"><span>Ghost car</span><b>' + (S().ghosts[q.track] ? U.timeShort(S().ghosts[q.track].time) : 'None yet') + '</b></div></div>';
        },
        go: (q) => TG.Game.startRace({ mode: 'time', trackId: q.track, laps: 3, rivals: 0, players: [carCfg(S().active, 'solo', 'You')] }),
      });
    },
  };

  SCREENS.versus = {
    render(ctx) {
      const k = S().keys, kn = TG.Input.keyName;
      const keysTxt = (p) => kn(k[p].accel[0]) + ' ' + kn(k[p].left[0]) + ' ' + kn(k[p].brake[0]) + ' ' + kn(k[p].right[0]) + ' · nitro ' + kn(k[p].nitro[0]);
      setupScreen(ctx, {
        state: () => { const q = S().versus; if (!S().cars[q.car2]) q.car2 = S().active; return q; },
        title: 'Head to Head', backFocus: 'versus', goLabel: 'Start duel!',
        rows: (q) => [
          adjRow('laps', 'Laps', q.laps, (d) => { q.laps = U.clamp(q.laps + d, 1, 6); TG.Save.save(); UI.refresh(); }),
          adjRow('rivals', 'CPU rivals', q.rivals, (d) => { q.rivals = U.clamp(q.rivals + d, 0, 9); TG.Save.save(); UI.refresh(); }),
          carPicker(ctx, 'car1', 'P1 car', () => S().active, (id) => { S().active = id; }),
          carPicker(ctx, 'car2', 'P2 car', () => q.car2, (id) => { q.car2 = id; }),
        ],
        extra: () => '<div class="card keys2"><div><span class="pl p1">P1 · top</span><b>' + esc(keysTxt('p1')) + '</b></div><div><span class="pl p2">P2 · bottom</span><b>' + esc(keysTxt('p2')) + '</b></div></div>',
        go: (q) => {
          const p1 = carCfg(S().active, 'p1', 'Player 1');
          const p2 = carCfg(q.car2, 'p2', 'Player 2');
          if (p2.carId === p1.carId && p2.color === p1.color) {
            const alt = TG.PAINTS.find((pp) => pp.c !== p1.color && U.lum(pp.c) > 0.2);
            p2.color = alt ? alt.c : '#e0558c';
          }
          TG.Game.startRace({ mode: 'versus', trackId: q.track, laps: q.laps, rivals: q.rivals, players: [p1, p2] });
        },
      });
    },
  };

  /* ---------- Garage ---------- */
  // Hangar layout (Garage / Showroom): car banner, then Specs / About / Actions panels
  function specPanel(st, extra) {
    const grip = Math.round(U.clamp((st.grip - 0.9) / 0.65, 0, 1) * 100);
    return '<div class="hg-box hg-specs">' + [['Top speed', speedTxt(st.top)], ['0-100', st.t0100.toFixed(1) + ' s'], ['Handling', grip + '/100'], ['Nitro', st.nitroTank.toFixed(1) + ' s drift tank']]
      .map((x) => '<div><span>' + x[0] + '</span><b>' + x[1] + '</b></div>').join('') + (extra || '') + '</div>';
  }
  function hangar(ctx, o) {
    const ids = o.ids, i = ids.indexOf(o.model.id), n = ids.length;
    ctx.el.innerHTML = studioHeader(o.title, (i + 1) + ' / ' + n) +
      '<div class="hg"><div class="hg-ban" data-nav data-key="car" data-adj="1"><canvas class="hg-car"></canvas>' +
      (n > 1 ? '<i class="arr hg-l" data-arrow="-1">◀</i><i class="arr hg-r" data-arrow="1">▶</i>' : '') +
      '<div class="hg-name"><span>' + esc(o.model.brand) + ' · No. ' + (TG.CARS.indexOf(o.model) + 1) + '</span><b>' + esc(o.model.name) + '</b></div></div>' +
      '<div class="hg-row">' + o.specs + '<div class="hg-box hg-about"><span>About</span><p>' + esc(o.model.desc) + '</p></div><div class="hg-box hg-act">' + o.actions + '</div></div></div>' +
      hints([['←→', 'Change car'], ['↑↓', 'Navigate'], ['Enter', 'Select'], ['Backspace', 'Back']]);
    const ban = $('[data-key="car"]', ctx.el);
    ban._silent = true;
    ban._adjust = (d) => { if (n > 1) { o.pick(ids[(i + d + n) % n]); UI.refresh('[data-key="car"]'); } };
    ctx.onKey = (code) => {
      if (ctx.modal) return false;
      const d = code === 'ArrowLeft' || code === 'KeyA' ? -1 : code === 'ArrowRight' || code === 'KeyD' ? 1 : 0;
      if (d) { ban._adjust(d); TG.Audio.play('nav'); return true; }
      return false;
    };
    showroomInto($('.hg-car', ctx.el), o.model, o.color, o.det);
    ctx.initial = ctx.initial || '[data-key="car"]';
  }
  SCREENS.garage = {
    studio: true,
    render(ctx) {
      ctx.linear = true;
      const ids = ownedIds();
      if (ctx.sel == null || ids.indexOf(ctx.sel) < 0) ctx.sel = ctx.params.car && ids.indexOf(ctx.params.car) >= 0 ? ctx.params.car : S().active;
      const id = ctx.sel, model = TG.CAR[id], car = S().cars[id];
      const lv = TG.UPGRADES.reduce((a, u) => a + (car.up[u.id] || 0), 0);
      const maxLv = TG.UPGRADES.reduce((a, u) => a + u.max, 0);
      const active = S().active === id;
      hangar(ctx, {
        title: 'Garage', ids, model, color: car.color, det: car.det, pick: (x) => { ctx.sel = x; },
        specs: specPanel(TG.carStats(model, car.up), '<div class="hg-wide"><span>Upgrades</span><b>' + lv + '/' + maxLv + '</b></div>'),
        actions: (active ? '<div class="hg-badge">Your racing car</div>' : '<button class="btn primary" data-nav data-key="use">Use this car</button>') +
          '<div class="hg-btns">' + [['shop', 'shop', 'Tuning', lv + '/' + maxLv], ['paint', 'paint', 'Detailing', car.det ? 'Custom' : 'Factory'], ['dealer', 'dealer', 'Showroom', ownedIds().length + '/' + TG.CARS.length]]
            .map((t) => '<button class="hg-tile" data-nav data-key="' + t[0] + '">' + icon(t[1]) + '<b>' + t[2] + '</b><small>' + t[3] + '</small></button>').join('') + '</div>',
      });
      const use = $('[data-key="use"]', ctx.el);
      if (use) use.addEventListener('click', () => { S().active = id; TG.Save.save(); UI.toast(model.brand + ' ' + model.name + ' ready to race', 'ok'); UI.refresh('[data-key="shop"]'); });
      $('[data-key="shop"]', ctx.el).addEventListener('click', () => UI.show('shop', { car: id, back: ctx.params.from }));
      $('[data-key="paint"]', ctx.el).addEventListener('click', () => UI.show('paint', { car: id, back: ctx.params.from }));
      $('[data-key="dealer"]', ctx.el).addEventListener('click', () => UI.show('dealer'));
      ctx.onBack = () => (ctx.params.from ? UI.show(ctx.params.from.name, ctx.params.from.params) : UI.show('main', { focus: 'garage' }));
    },
  };

  /* ---------- Tuning shop: car banner + part tiles + selected-part panel ---------- */
  SCREENS.shop = {
    studio: true,
    render(ctx) {
      const id = S().cars[ctx.params.car] ? ctx.params.car : S().active, model = TG.CAR[id], car = S().cars[id];
      const UPS = TG.UPGRADES;
      const lvTot = UPS.reduce((a, u) => a + (car.up[u.id] || 0), 0), maxTot = UPS.reduce((a, u) => a + u.max, 0);
      const segs = (l, max) => { let h = ''; for (let k = 0; k < max; k++) h += '<i class="' + (k < l ? 'on' : '') + '"></i>'; return h; };
      const tile = (u) => {
        const l = car.up[u.id] || 0, maxed = l >= u.max;
        const cost = maxed ? 0 : TG.upgradeCost(model, u, l);
        return '<button class="tn-part' + (maxed ? ' maxed' : S().money < cost ? ' poor' : '') + '" data-nav data-key="' + u.id + '"><span class="tn-pn">' + esc(u.name) + '</span>' +
          '<span class="tn-segs">' + segs(l, u.max) + '</span><b class="tn-pc">' + (maxed ? 'Maxed' : money(cost)) + '</b></button>';
      };
      // selected part: description, before/after stats and the price of the next level
      const info = (u) => {
        const l = car.up[u.id] || 0, maxed = l >= u.max;
        const st = TG.carStats(model, car.up);
        let st2 = null;
        if (!maxed) { const up2 = Object.assign({}, car.up); up2[u.id] = l + 1; st2 = TG.carStats(model, up2); }
        const pct = (v) => Math.round(v * 100) + '%';
        const extra = [];
        if (u.id === 'tank') extra.push(['Fuel use', pct(st.fuelUse), st2 && pct(st2.fuelUse)]);
        if (u.id === 'chassis') extra.push(['Impact loss', pct(st.crash), st2 && pct(st2.crash)]);
        if (u.id === 'trans') extra.push(['Gears', st.gears + '', st2 && st2.gears + '']);
        if (u.id === 'tires') extra.push(['Tire grade', st.tires + '/' + u.max, st2 && st2.tires + '/' + u.max]);
        const cost = maxed ? 0 : TG.upgradeCost(model, u, l);
        return '<span>' + (maxed ? 'Fully tuned' : 'Level ' + (l + 1) + ' of ' + u.max) + '</span><b class="tn-title">' + esc(u.name) + '</b><p class="tn-desc">' + esc(u.desc) + '</p>' +
          statBlock(st, st2) +
          extra.map((x) => '<div class="tn-x"><span>' + x[0] + '</span><b>' + x[1] + (x[2] && x[2] !== x[1] ? ' <em><i class="ar">→</i> ' + x[2] + '</em>' : '') + '</b></div>').join('') +
          '<div class="tn-buy">' + (maxed ? '<b class="max">Maxed out</b>' : '<span>Enter to install</span><b class="' + (S().money < cost ? 'poor' : '') + '">' + money(cost) + '</b>') + '</div>';
      };
      const foc = UPS.find((u) => u.id === ctx.focusUp) || UPS[0];
      ctx.el.innerHTML = studioHeader('Tuning', model.brand + ' ' + model.name) +
        '<div class="tn"><div class="hg-ban tn-ban"><canvas class="hg-car"></canvas><div class="hg-name"><span>' + esc(model.brand) + '</span><b>' + esc(model.name) + '</b></div>' +
        '<div class="tn-total"><span>Upgrades</span><b>' + lvTot + '/' + maxTot + '</b></div></div>' +
        '<div class="tn-row"><div class="tn-parts">' + UPS.map(tile).join('') + '</div><div class="hg-box tn-info">' + info(foc) + '</div></div></div>' +
        hints([['↑↓←→', 'Choose part'], ['Enter', 'Install'], ['Backspace', 'Back']]);
      showroomInto($('.hg-car', ctx.el), model, car.color, car.det);
      UPS.forEach((u) => {
        const b = $('[data-key="' + u.id + '"]', ctx.el);
        b._silent = true;
        b.addEventListener('click', () => {
          const l = car.up[u.id] || 0;
          if (l >= u.max) { TG.Audio.play('error'); UI.toast(u.name + ': already maxed out.'); return; }
          const cost = TG.upgradeCost(model, u, l);
          if (S().money < cost) { TG.Audio.play('error'); UI.toast('You need ' + money(cost - S().money) + ' more for ' + u.name.toLowerCase() + ' level ' + (l + 1) + '.', 'warn'); return; }
          S().money -= cost;
          car.up[u.id] = l + 1;
          TG.Save.save();
          TG.Audio.play('upgrade');
          UI.toast(u.name + ' level ' + (l + 1) + ' installed', 'ok');
          ctx.focusUp = u.id;
          UI.refresh('[data-key="' + u.id + '"]');
        });
      });
      ctx.onFocus = (el) => {
        const u = UPS.find((x) => x.id === el.dataset.key);
        if (u && u.id !== ctx.focusUp) { ctx.focusUp = u.id; $('.tn-info', ctx.el).innerHTML = info(u); }
      };
      ctx.focusUp = foc.id;
      ctx.initial = '[data-key="' + foc.id + '"]';
      ctx.onBack = () => UI.show('garage', { car: id, from: ctx.params.back });
    },
  };

  /* ---------- Detailing studio: body, accent, wheels, calipers, finish, window tint (all live on the WebGL car) ---------- */
  SCREENS.paint = {
    studio: true,
    render(ctx) {
      ctx.linear = true;
      const id = S().cars[ctx.params.car] ? ctx.params.car : S().active, model = TG.CAR[id], car = S().cars[id];
      const D = TG.DETAIL;
      if (!ctx.draft) ctx.draft = { color: car.color, det: Object.assign({}, car.det || {}) };
      const dr = ctx.draft;
      const back = () => UI.show('garage', { car: id, from: ctx.params.back });
      const CG = TG.CarGL;
      const f = CG.colors(model, dr.color, dr.det);
      const chip = (c) => '<i class="det-chip" style="background:' + c + '"></i>';
      const opt = (list) => [{ name: 'Factory', c: null }].concat(list);
      // one ←→ row per zone; det fields left empty mean "factory"
      const row = (key, label, list, cur, set, shown) => {
        const i = Math.max(0, list.findIndex((o) => o.c === cur));
        return adjRow(key, label, (shown ? chip(shown) : '') + esc(list[i].name), (d) => { set(list[(i + d + list.length) % list.length].c); UI.refresh(); });
      };
      const setDet = (k) => (v) => { if (v == null) delete dr.det[k]; else dr.det[k] = v; };
      const colours = [row('body', 'Body', [{ name: 'Factory', c: model.color }].concat(TG.PAINTS), dr.color, (v) => { dr.color = v; }, f.paint)];
      if (CG.hasMat(id, 'sec')) colours.push(row('sec', 'Accent', opt(D.accents.concat(TG.PAINTS)), dr.det.sec || null, setDet('sec'), f.sec));
      colours.push(row('rim', 'Wheels', opt(D.rims), dr.det.rim || null, setDet('rim'), f.rim));
      colours.push(row('caliper', 'Calipers', opt(D.calipers), dr.det.caliper || null, setDet('caliper'), f.caliper));
      const finish = [
        row('finish', 'Finish', [{ name: 'Gloss', c: null }].concat(D.finishes.map((x) => ({ name: x.name, c: x.id }))), dr.det.finish || null, setDet('finish')),
        row('tint', 'Windows', [{ name: 'Clear', c: null }].concat(D.tints.map((x) => ({ name: x.name, c: x.id }))), dr.det.tint || null, setDet('tint')),
      ];
      ctx.el.innerHTML = studioHeader('Detailing', model.brand + ' ' + model.name) +
        '<div class="hg"><div class="hg-ban"><canvas class="hg-car"></canvas><div class="hg-name"><span>' + esc(model.brand) + '</span><b>' + esc(model.name) + '</b></div></div>' +
        '<div class="hg-row"><div class="hg-box det-box"><span>Colours</span>' + colours.map((r) => r.html).join('') + '</div>' +
        '<div class="hg-box det-box"><span>Finish</span>' + finish.map((r) => r.html).join('') + '<p class="small muted">Detailing is free. Every change shows live on the car.</p></div>' +
        '<div class="hg-box hg-act"><button class="btn primary big" data-nav data-key="apply">Apply</button>' +
        '<button class="btn ghost" data-nav data-key="reset">Reset to factory</button><button class="btn ghost" data-nav data-key="cancel">Cancel</button></div></div></div>' +
        hints([['↑↓', 'Select'], ['←→', 'Change'], ['Enter', 'Confirm'], ['Backspace', 'Cancel']]);
      bindAdj(ctx.el, colours.concat(finish));
      showroomInto($('.hg-car', ctx.el), model, dr.color, dr.det);
      $('[data-key="apply"]', ctx.el).addEventListener('click', () => {
        car.color = dr.color;
        if (Object.keys(dr.det).length) car.det = Object.assign({}, dr.det); else delete car.det;
        TG.Save.save();
        TG.Audio.play('buy');
        UI.toast('Detailing applied', 'ok');
        back();
      });
      $('[data-key="reset"]', ctx.el).addEventListener('click', () => { dr.color = model.color; dr.det = {}; UI.refresh(); });
      $('[data-key="cancel"]', ctx.el).addEventListener('click', back);
      ctx.initial = ctx.initial || '[data-key="body"]';
      ctx.onBack = back;
    },
  };

  /* ---------- Showroom ---------- */
  SCREENS.dealer = {
    studio: true,
    render(ctx) {
      ctx.linear = true;
      if (ctx.sel == null) {
        const firstNew = byPrice().find((c) => !S().cars[c.id]);
        ctx.sel = ctx.params.car || (firstNew ? firstNew.id : byPrice()[0].id);
      }
      const model = TG.CAR[ctx.sel];
      const owned = !!S().cars[model.id];
      const can = S().money >= model.price;
      const list = byPrice();
      hangar(ctx, {
        title: 'Showroom', ids: list.map((c) => c.id), model, color: model.color, pick: (x) => { ctx.sel = x; },
        specs: specPanel(TG.carStats(model, {})),
        actions: '<span class="hg-lbl">' + (owned ? 'In your garage' : 'Price') + '</span><b class="hg-price' + (owned ? ' own' : can ? '' : ' poor') + '">' + (owned ? 'Owned' : model.price === 0 ? 'Free' : money(model.price)) + '</b>' +
          (owned ? '<button class="btn" data-nav data-key="garage">View in garage</button>' : '<button class="btn primary" data-nav data-key="buy">Buy</button>') +
          (!owned && !can ? '<p class="warn-txt">You need ' + money(model.price - S().money) + ' more.</p>' : ''),
      });
      const buy = $('[data-key="buy"]', ctx.el);
      if (buy) {
        buy._silent = true;
        buy.addEventListener('click', () => {
          if (S().money < model.price) { TG.Audio.play('error'); UI.toast('You need ' + money(model.price - S().money) + ' more for the ' + model.name + '.', 'warn'); return; }
          TG.Audio.play('select');
          UI.modal('<h2>' + esc(model.brand + ' ' + model.name) + '</h2><p>Buy it for <b>' + money(model.price) + '</b>? You will have ' + money(S().money - model.price) + ' left.</p>', [
            { label: 'Buy', cls: 'primary', fn: () => {
              S().money -= model.price;
              S().cars[model.id] = { color: model.color, up: {} };
              S().active = model.id;
              TG.Save.save();
              TG.Audio.play('buy');
              UI.toast('Congratulations! The ' + model.brand + ' ' + model.name + ' is yours', 'ok');
              UI.refresh('[data-key="car"]');
            } },
            { label: 'Cancel', cls: 'ghost' },
          ]);
        });
      }
      const gar = $('[data-key="garage"]', ctx.el);
      if (gar) gar.addEventListener('click', () => UI.show('garage', { car: model.id }));
      ctx.onBack = () => UI.show('main', { focus: 'dealer' });
    },
  };

  /* ---------- Settings ---------- */
  // Subtle "Game saved" indicator
  UI.saved = function () {
    let el = document.getElementById('saveBadge');
    if (!el) { el = U.el('div', 'save-badge', '<i></i>Game saved'); el.id = 'saveBadge'; document.body.appendChild(el); }
    el.classList.remove('on'); void el.offsetWidth; el.classList.add('on');
    clearTimeout(UI._sbT); UI._sbT = setTimeout(() => el.classList.remove('on'), 1600);
  };
  function exportSave() {
    const text = TG.Save.exportText();
    try {
      if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.tgApp) { window.webkit.messageHandlers.tgApp.postMessage('export:' + text); return; }
    } catch (e) { /* browser */ }
    const a = document.createElement('a');
    const d = new Date();
    a.download = 'Chromewave-save-' +d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + '.json';
    a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    UI.toast('Save exported: keep the file to restore your progress any time.', 'ok');
  }
  function importSave() {
    try {
      if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.tgApp) { window.webkit.messageHandlers.tgApp.postMessage('import'); return; }
    } catch (e) { /* browser */ }
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = '.json,application/json';
    inp.onchange = () => {
      const f = inp.files && inp.files[0];
      if (!f) return;
      const r = new FileReader();
      r.onload = () => UI.importDone(TG.Save.importText(String(r.result)));
      r.readAsText(f);
    };
    inp.click();
  }
  UI.importDone = function (ok) {
    if (ok) { UI.toast('Save imported successfully.', 'ok'); UI.refresh(); }
    else UI.toast('That file is not a valid Chromewave save.', 'warn');
  };

  /* ---------- Settings: Sound / Display / Race panels, a tip line for the focused item, action tiles ---------- */
  SCREENS.options = {
    render(ctx) {
      ctx.linear = true;
      const st = S().settings;
      const cyc = (key, list, d) => { const i = list.indexOf(st[key]); st[key] = list[(i + d + list.length) % list.length]; };
      const QL = { low: 'Low', medium: 'Medium', high: 'High', ultra: 'Ultra' };
      const vol = (v) => '<span class="vol">' + bars(v, 0) + '</span>' + Math.round(v * 10);
      const rows = [
        adjRow('music', 'Music', vol(st.music), (d) => { st.music = U.clamp(Math.round((st.music + d * 0.1) * 10) / 10, 0, 1); TG.Audio.apply(); TG.Save.save(); UI.refresh(); }),
        adjRow('sfx', 'Effects', vol(st.sfx), (d) => { st.sfx = U.clamp(Math.round((st.sfx + d * 0.1) * 10) / 10, 0, 1); TG.Audio.apply(); TG.Audio.play('coin'); TG.Save.save(); UI.refresh(); }),
        adjRow('quality', 'Quality', QL[st.quality], (d) => { cyc('quality', ['low', 'medium', 'high', 'ultra'], d); TG.Save.save(); TG.Render.resize(); TG.Game.qualityChanged(); UI.refresh(); }),
        adjRow('camera', 'Camera', st.camera === 'far' ? 'Far' : 'Near', (d) => { cyc('camera', ['near', 'far'], d); TG.Save.save(); UI.refresh(); }),
        adjRow('units', 'Units', st.units === 'mph' ? 'mph' : 'km/h', (d) => { cyc('units', ['kmh', 'mph'], d); TG.Save.save(); UI.refresh(); }),
        adjRow('fps', 'Show FPS', st.fps ? 'Yes' : 'No', () => { st.fps = !st.fps; TG.Save.save(); UI.refresh(); }),
        adjRow('difficulty', 'Rivals', (TG.DIFFICULTY[st.difficulty] || TG.DIFFICULTY.normal).name, (d) => { cyc('difficulty', ['easy', 'normal', 'hard'], d); TG.Save.save(); UI.refresh(); }),
        adjRow('trans', 'Gearbox', st.trans === 'manual' ? 'Manual' : 'Automatic', (d) => { cyc('trans', ['auto', 'manual'], d); TG.Save.save(); UI.refresh(); }),
      ];
      const TIPS = {
        music: 'Press M at any time to mute the music.',
        sfx: 'Engines, tires, coins and menu sounds.',
        quality: 'If the game stutters, lower it to Medium or Low.',
        camera: 'Far camera: see the upcoming corners better.',
        units: 'Speeds everywhere in km/h or mph.',
        fps: 'Shows frames per second in a corner during races.',
        difficulty: 'Rivals get a little better with every World Tour race; this sets where they start.',
        trans: 'Manual: shift up near the rev limiter (the gear flashes) to gain acceleration.',
        controls: 'Change the keys for solo play and for both Head to Head players.',
        export: 'Progress saves automatically. Export a copy to move it to another browser or computer.',
        import: 'Load a save file you exported earlier. It replaces your current progress.',
        reset: 'Deletes your money, cars, upgrades, cups and records. This cannot be undone.',
      };
      const R = {};
      rows.forEach((r) => { R[r.key] = r.html; });
      const box = (title, keys) => '<div class="hg-box set-box"><span>' + title + '</span>' + keys.map((k) => R[k]).join('') + '</div>';
      const tiles = [['controls', 'keys', 'Controls'], ['export', 'export', 'Export save'], ['import', 'import', 'Import save'], ['reset', 'trash', 'Delete save']];
      ctx.el.innerHTML = header('Settings', 'Sound · display · race · save') +
        '<div class="setv"><div class="set-cols">' + box('Sound', ['music', 'sfx']) + box('Display', ['quality', 'camera', 'units', 'fps']) + box('Race', ['difficulty', 'trans']) + '</div>' +
        '<div class="set-tip"><span>Tip</span><p>' + TIPS.music + '</p></div>' +
        '<div class="set-tiles">' + tiles.map((t) => '<button class="hg-tile' + (t[0] === 'reset' ? ' danger' : '') + '" data-nav data-key="' + t[0] + '">' + icon(t[1]) + '<b>' + t[2] + '</b></button>').join('') + '</div></div>' +
        hints([['↑↓', 'Navigate'], ['←→', 'Change'], ['Enter', 'Select'], ['Backspace', 'Back']]);
      bindAdj(ctx.el, rows);
      ctx.onFocus = (el) => { const tip = TIPS[el.dataset.key]; if (tip) $('.set-tip p', ctx.el).textContent = tip; };
      $('[data-key="controls"]', ctx.el).addEventListener('click', () => UI.show('controls', { back: ctx.params.back }));
      $('[data-key="export"]', ctx.el).addEventListener('click', exportSave);
      $('[data-key="import"]', ctx.el).addEventListener('click', importSave);
      $('[data-key="reset"]', ctx.el).addEventListener('click', () => UI.modal('<h2>Delete all progress?</h2><p>You will lose your money, cars, upgrades, cups and records. This cannot be undone.</p>', [
        { label: 'Delete everything', cls: 'danger', fn: () => { TG.Save.reset(); UI.toast('Save deleted. Starting fresh!', 'ok'); UI.refresh(); } },
        { label: 'Cancel', cls: 'ghost' },
      ], { focus: 1 }));
      ctx.onBack = () => (ctx.params.back ? ctx.params.back() : UI.show('main', { focus: 'options' }));
    },
  };

  /* ---------- Controls: profile tabs, key table panel, fixed keys + defaults panel ---------- */
  SCREENS.controls = {
    render(ctx) {
      const I = TG.Input;
      if (!ctx.prof) ctx.prof = 'solo';
      const keys = S().keys[ctx.prof];
      const slots = ctx.prof === 'solo' ? 2 : 1;
      ctx.el.innerHTML = header('Controls', 'Keyboard · ' + I.PROFILE_LABEL[ctx.prof]) +
        '<div class="ctl"><div class="ctl-tabs">' + I.PROFILES.map((p) => '<button class="tab ' + (p === ctx.prof ? 'on' : '') + '" data-nav data-key="tab_' + p + '">' + I.PROFILE_LABEL[p] + '</button>').join('') + '</div>' +
        '<div class="ctl-row"><div class="hg-box ctl-keys"><span>Drive keys' + (slots > 1 ? ' · main / alternate' : '') + '</span>' + I.ACTIONS.map((a) => {
          let cells = '';
          for (let k = 0; k < slots; k++) cells += '<button class="keycap" data-nav data-key="k_' + a + '_' + k + '" data-a="' + a + '" data-s="' + k + '">' + esc(I.keyName(keys[a][k])) + '</button>';
          return '<div class="krow"><span>' + I.ACTION_LABEL[a] + '</span><div class="kcells">' + cells + '</div></div>';
        }).join('') + '</div>' +
        '<div class="hg-box ctl-side"><span>Always</span>' +
        '<div class="krow fixed"><span>Pause</span><div class="kcells"><span class="keycap static">P</span></div></div>' +
        '<div class="krow fixed"><span>Mute music</span><div class="kcells"><span class="keycap static">M</span></div></div>' +
        '<p class="small muted">' + (slots > 1 ? 'Solo play has two keys per action, so you can drive with the arrows or with WASD.' : 'In Head to Head each player has one key per action. Keys can\'t be shared between players.') + '</p>' +
        '<button class="btn ghost" data-nav data-key="defaults">Restore default keys</button></div></div></div>' +
        hints([['↑↓←→', 'Navigate'], ['Enter', 'Change key'], ['Backspace', 'Back']]);
      I.PROFILES.forEach((p) => $('[data-key="tab_' + p + '"]', ctx.el).addEventListener('click', () => { ctx.prof = p; UI.refresh('[data-key="tab_' + p + '"]'); }));
      $$('.keycap[data-a]', ctx.el).forEach((b) => b.addEventListener('click', () => {
        const a = b.dataset.a, s = +b.dataset.s;
        b.classList.add('listening');
        b.textContent = 'Press a key…';
        UI.capture = (code) => {
          UI.capture = null;
          if (code === 'Backspace') { TG.Audio.play('back'); UI.refresh('[data-key="k_' + a + '_' + s + '"]'); return true; }
          if (I.RESERVED.has(code) && code !== 'Enter') { TG.Audio.play('error'); UI.toast('That key is reserved (pause or music).', 'warn'); UI.refresh('[data-key="k_' + a + '_' + s + '"]'); return true; }
          const prof = S().keys[ctx.prof];
          I.ACTIONS.forEach((a2) => prof[a2].forEach((kk, j) => { if (kk === code) prof[a2][j] = ''; }));
          prof[a][s] = code;
          TG.Save.save();
          TG.Audio.play('select');
          UI.refresh('[data-key="k_' + a + '_' + s + '"]');
          return true;
        };
      }));
      $('[data-key="defaults"]', ctx.el).addEventListener('click', () => { S().keys = I.defaultKeys(); TG.Save.save(); UI.toast('Keys restored', 'ok'); UI.refresh('[data-key="defaults"]'); });
      const grid = [I.PROFILES.map((p) => $('[data-key="tab_' + p + '"]', ctx.el))];
      I.ACTIONS.forEach((a) => { const row = []; for (let k = 0; k < slots; k++) row.push($('[data-key="k_' + a + '_' + k + '"]', ctx.el)); grid.push(row); });
      grid.push([$('[data-key="defaults"]', ctx.el)]);
      ctx.onKey = (code) => {
        if (ctx.modal) return false;
        const dir = { ArrowUp: [-1, 0], KeyW: [-1, 0], ArrowDown: [1, 0], KeyS: [1, 0], ArrowLeft: [0, -1], KeyA: [0, -1], ArrowRight: [0, 1], KeyD: [0, 1] }[code];
        if (!dir) return false;
        let r = 0, c = 0;
        grid.forEach((row, ri) => row.forEach((el, ci) => { if (el === ctx.focused) { r = ri; c = ci; } }));
        if (dir[0]) { r = (r + dir[0] + grid.length) % grid.length; c = Math.min(c, grid[r].length - 1); }
        else c = U.clamp(c + dir[1], 0, grid[r].length - 1);
        UI.focus(grid[r][c]);
        TG.Audio.play('nav');
        return true;
      };
      ctx.initial = ctx.initial || '[data-key="k_accel_0"]';
      ctx.onBack = () => UI.show('options', { back: ctx.params.back });
    },
  };

  /* ---------- Loading: race ticket (track preview, cup, conditions, segmented bar, tip) ---------- */
  SCREENS.loading = {
    overlay: true, dim: false,
    render(ctx) {
      const cfg = ctx.params.cfg;
      const t = TG.TRACKS[cfg.trackId], th = TG.THEMES[t.theme], cup = TG.CUPS[t.cup];
      const chips = [TG.TIME_LABEL[th.time], TG.WEATHER_LABEL[th.weather], (cfg.laps || 3) + ' laps'].concat(cfg.rivals ? [cfg.rivals + ' rivals'] : []);
      let segs = '';
      for (let k = 0; k < 16; k++) segs += '<i style="animation-delay:' + (k * 0.07).toFixed(2) + 's"></i>';
      ctx.el.innerHTML = '<div class="ldv"><div class="ld-card"><canvas class="ld-pv" width="960" height="400"></canvas>' +
        '<div class="ld-body"><div class="ld-cup"><span class="flag-slot"></span>' + esc(cup.name) + '</div><h1>' + esc(t.name) + '</h1>' +
        '<div class="ld-chips">' + chips.map((c) => '<b>' + esc(c) + '</b>').join('') + '</div>' +
        '<div class="ld-segs">' + segs + '</div>' +
        '<div class="ld-tip"><span>Tip</span><p>' + esc(U.pick(TG.TIPS)) + '</p></div></div></div></div>';
      thumbInto($('.ld-pv', ctx.el), t.theme);
      $('.flag-slot', ctx.el).appendChild(flagCanvas(cup.flag, 24, 16));
    },
  };

  /* ---------- Pause: race facts + pixel menu ---------- */
  SCREENS.pause = {
    overlay: true,
    render(ctx) {
      ctx.linear = true;
      const race = TG.Game.race, p = race && race.players[0];
      const facts = [];
      if (race && p) {
        if (race.mode !== 'time') facts.push(['Position', U.ord(p.pos || 1) + ' / ' + race.cars.length]);
        facts.push(['Lap', U.clamp(p.lapsDone + 1, 1, race.laps) + ' / ' + race.laps]);
        facts.push(['Time', U.time(Math.max(0, race.time || 0))]);
        facts.push(['Best lap', p.bestLap ? U.time(p.bestLap) : '--']);
      }
      const items = [['resume', 'Continue'], ['restart', 'Restart race'], ['opts', 'Settings'], ['quit', 'Quit race']];
      ctx.el.innerHTML = '<div class="pz"><div class="pz-head"><span>' + esc(race ? race.def.name : '') + '</span><h1>Paused</h1></div>' +
        (facts.length ? '<div class="pz-facts">' + facts.map((f) => '<div><span>' + f[0] + '</span><b>' + f[1] + '</b></div>').join('') + '</div>' : '') +
        '<div class="pz-menu">' + items.map((it) => '<button class="pz-btn' + (it[0] === 'quit' ? ' quit' : '') + '" data-nav data-key="' + it[0] + '">' + it[1] + '</button>').join('') + '</div>' +
        '<div class="pz-keys"><kbd>P</kbd> resume · <kbd>M</kbd> music</div></div>';
      $('[data-key="resume"]', ctx.el).addEventListener('click', () => TG.Game.resume());
      $('[data-key="restart"]', ctx.el).addEventListener('click', () => TG.Game.restart());
      $('[data-key="opts"]', ctx.el).addEventListener('click', () => UI.show('options', { back: () => UI.show('pause') }));
      $('[data-key="quit"]', ctx.el).addEventListener('click', () => UI.modal('<h2>Quit the race?</h2><p>You will not earn a prize for this race. On the World Tour you can race it again.</p>', [
        { label: 'Quit', cls: 'danger', fn: () => TG.Game.quitRace() }, { label: 'Keep racing', cls: 'ghost' },
      ], { focus: 1 }));
      ctx.onBack = () => TG.Game.resume();
    },
  };

  // podium: 2nd, 1st, 3rd as pixel steps. items: [{ name, car, val, me, cls }]
  function podium(items) {
    return '<div class="podium">' + [1, 0, 2].filter((k) => items[k]).map((k) => {
      const it = items[k];
      return '<div class="pd pd' + (k + 1) + (it.me ? ' me' : '') + (it.cls || '') + '"><div class="pd-name">' + esc(it.name) + '</div><div class="pd-car">' + esc(it.car) + '</div>' +
        '<div class="pd-step"><b>' + (k + 1) + '</b><span>' + it.val + '</span></div></div>';
    }).join('') + '</div>';
  }

  SCREENS.results = {
    overlay: true,
    render(ctx) {
      ctx.linear = true;
      const d = ctx.params;
      const res = d.res;
      const win = res[0].time;
      const mode = d.mode;
      const who = (r) => (r.isPlayer ? (mode === 'versus' ? r.name : 'You') : r.name);
      const tm = (r) => (r.pos === 1 ? U.time(r.time) : '+' + (r.time - win).toFixed(2) + ' s');
      const carTxt = (r) => r.model.brand + ' ' + r.model.name;
      const rows = res.map((r) => '<tr class="' + (r.isPlayer ? 'me p' + r.pIndex : '') + '"><td class="pos">' + r.pos + '</td><td>' + esc(who(r)) + '</td><td class="muted">' + esc(carTxt(r)) + '</td><td class="num">' +
        (r.finished ? tm(r) : '<span class="muted">' + tm(r) + '</span>') + '</td></tr>').join('');
      const e = d.earnings;
      const p = d.race.players[0];
      let top, boxes;
      if (mode === 'time') {
        top = '<div class="res-lap"><span>Best lap</span><b>' + U.time(p.bestLap) + '</b>' + (d.newRecord ? '<i>New track record</i>' : '') + '</div>';
        boxes = '<div class="hg-box earn"><span>Your laps</span>' +
          (p.laps.map((l, k) => '<div class="erow"><span>Lap ' + (k + 1) + '</span><b>' + U.time(l) + '</b></div>').join('') || '<p class="muted">No complete laps.</p>') +
          (d.newGhost ? '<div class="erow"><span>Ghost saved for next time</span><b>✓</b></div>' : '') + '</div>';
      } else {
        top = podium(res.slice(0, 3).map((r) => ({ name: who(r), car: carTxt(r), val: r.finished ? tm(r) : 'DNF', me: r.isPlayer, cls: r.isPlayer ? ' p' + r.pIndex : '' })));
        boxes = '<div class="hg-box res-class" data-scroll="res"><span>Classification</span><table class="tbl res"><tbody>' + rows + '</tbody></table></div>';
        if (e) {
          boxes += '<div class="hg-box earn"><span>Earnings</span>' +
            '<div class="erow"><span>' + U.ord(e.pos) + ' place prize</span><b data-count="' + e.prize + '">$0</b></div>' +
            '<div class="erow"><span>Coins collected</span><b data-count="' + e.coins + '">$0</b></div>' +
            (e.clean ? '<div class="erow"><span>Clean race bonus</span><b data-count="' + e.clean + '">$0</b></div>' : '') +
            (e.record ? '<div class="erow"><span>Lap record</span><b data-count="' + e.record + '">$0</b></div>' : '') +
            (e.repair ? '<div class="erow neg"><span>Damage repair (' + e.dmg + '%)</span><b>−' + money(e.repair) + '</b></div>' : '') +
            '<div class="erow total"><span>Total</span><b data-count="' + e.total + '">$0</b></div>' +
            '<div class="erow bal"><span>Balance</span><b>' + money(S().money) + '</b></div></div>';
        } else if (mode === 'versus') {
          const w = res.find((r) => r.isPlayer);
          boxes += '<div class="hg-box earn"><span>Duel</span><div class="winner p' + w.pIndex + '">' + esc(w.name) + ' wins!</div></div>';
        }
      }
      const cupInfo = d.cupRun ? '<p class="small muted">' + esc(d.cup.name) + ': race ' + d.cupRun.race + ' of 4 done · ' + (d.cupRun.points.player || 0) + ' points</p>' : '';
      const title = mode === 'time' ? 'Time Attack' : res.find((r) => r.isPlayer).pos === 1 ? 'Victory!' : 'Results';
      ctx.el.innerHTML = header(title, d.def.name + ' · ' + d.cup.name) +
        '<div class="resv">' + top + '<div class="hg-row' + (mode === 'time' ? ' two' : '') + '">' + boxes +
        '<div class="hg-box hg-act">' + cupInfo +
        (e && e.total > 0 && TG.Portal.on && !TG.Portal.noAds ? '<button class="btn primary" data-nav data-key="double">Watch an ad: double prize (+' + money(e.total) + ')</button>' : '') +
        '<button class="btn primary big" data-nav data-key="next">' + (d.cupEnd ? 'Final standings' : d.cupRun ? 'Next race' : 'Continue') + '</button>' +
        (!d.cupRun && !d.cupEnd ? '<button class="btn ghost" data-nav data-key="again">Race again</button>' : '') +
        '<button class="btn ghost" data-nav data-key="menu">Main menu</button></div></div></div>';
      // animated counter
      const counters = $$('[data-count]', ctx.el);
      const t0 = performance.now();
      const anim = (now) => {
        const k = U.clamp((now - t0) / 1100, 0, 1);
        counters.forEach((c) => { c.textContent = money(+c.dataset.count * U.easeOutCubic(k)); });
        if (k < 1 && UI.cur === ctx) requestAnimationFrame(anim);
      };
      requestAnimationFrame(anim);
      $('[data-key="next"]', ctx.el).addEventListener('click', () => {
        if (d.cupEnd) UI.show('cupEnd', d.cupEnd);
        else if (d.cupRun) { TG.Game.toDemo(); UI.show('cup', { i: d.cup.index }); }
        else TG.Game.backToMenu(mode);
      });
      const dbl = $('[data-key="double"]', ctx.el);
      if (dbl) dbl.addEventListener('click', () => {
        dbl.disabled = true;
        TG.Portal.ad('rewarded', (ok) => {
          if (!ok) { dbl.disabled = false; UI.toast('No ad available right now. Try again in a moment.'); return; }
          S().money += e.total;
          S().stats.earned += e.total;
          TG.Save.save();
          dbl.remove();
          $$('.erow.bal b, .wallet-val', ctx.el).forEach((b) => { b.textContent = money(S().money); });
          UI.toast('Prize doubled: +' + money(e.total));
          UI.focus($('[data-key="next"]', ctx.el), true);
        });
      });
      const ag = $('[data-key="again"]', ctx.el);
      if (ag) ag.addEventListener('click', () => TG.Game.startRace(d.race.cfg));
      $('[data-key="menu"]', ctx.el).addEventListener('click', () => TG.Game.backToMenu());
      ctx.onBack = () => {};
    },
  };
  SCREENS.cupEnd = {
    overlay: true,
    render(ctx) {
      ctx.linear = true;
      const d = ctx.params;
      const carTxt = (r) => r.car.brand + ' ' + r.car.name;
      const rows = d.table.map((r, k) => '<tr class="' + (r.me ? 'me' : '') + '"><td class="pos">' + (k + 1) + '</td><td>' + esc(r.name) + '</td><td class="muted">' + esc(carTxt(r)) + '</td><td class="num">' + r.pts + '</td></tr>').join('');
      ctx.el.innerHTML = header(d.rank === 1 ? 'Champion!' : d.rank <= 3 ? 'Podium!' : 'Cup complete', d.cup.name + ' · final standings') +
        '<div class="resv">' + podium(d.table.slice(0, 3).map((r) => ({ name: r.name, car: carTxt(r), val: r.pts + ' pts', me: r.me }))) +
        '<div class="hg-row"><div class="hg-box res-class" data-scroll="cupend"><span>Final standings</span><table class="tbl res"><tbody>' + rows + '</tbody></table></div>' +
        '<div class="hg-box earn"><span>Reward</span>' +
        '<div class="erow"><span>Final position</span><b>' + U.ord(d.rank) + '</b></div>' +
        '<div class="erow total"><span>Cup bonus</span><b>' + money(d.bonus) + '</b></div>' +
        '<div class="erow bal"><span>Balance</span><b>' + money(S().money) + '</b></div>' +
        (d.unlocked ? '<div class="unlock"><span>New cup unlocked</span><b>' + esc(d.unlocked) + '</b></div>' : '') +
        (d.done ? '<div class="unlock gold"><span>World Tour complete</span><b>Chromewave Legend!</b></div>' : '') + '</div>' +
        '<div class="hg-box hg-act">' + (d.rank > 3 ? '<p class="warn-txt">You need a top-3 finish to unlock the next cup. Upgrade your car and try again.</p>' : '') +
        '<button class="btn primary big" data-nav data-key="ok">Continue</button></div></div></div>';
      if (d.rank <= 3) TG.Audio.play('trophy');
      $('[data-key="ok"]', ctx.el).addEventListener('click', () => { TG.Game.toDemo(); UI.show('career', { i: d.cup.index }); });
      ctx.onBack = () => {};
    },
  };
})(window.TG);

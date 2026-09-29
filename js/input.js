'use strict';
/* ============================================================
   Keyboard: state, key presses and control profiles
   ============================================================ */
(function (TG) {
  const I = (TG.Input = { down: new Set(), queue: [], pressed: new Set(), listeners: [], labels: {} });
  // on-screen touch controls (js/touch.js) press actions by name for player 1 / solo
  I.tdown = new Set(); I.tqueue = []; I.tpressed = new Set();
  I.tpress = (act, on) => { if (on) { if (!I.tdown.has(act)) I.tqueue.push(act); I.tdown.add(act); } else I.tdown.delete(act); };
  I.tclear = () => { I.tdown.clear(); };

  I.ACTIONS = ['accel', 'brake', 'left', 'right', 'nitro', 'gearUp', 'gearDown'];
  I.ACTION_LABEL = { accel: 'Accelerate', brake: 'Brake', left: 'Steer left', right: 'Steer right', nitro: 'Nitro', gearUp: 'Shift up (manual)', gearDown: 'Shift down (manual)' };
  I.PROFILES = ['solo', 'p1', 'p2'];
  I.PROFILE_LABEL = { solo: '1 player', p1: 'Player 1 (2P)', p2: 'Player 2 (2P)' };

  I.defaultKeys = function () {
    return {
      solo: { accel: ['ArrowUp', 'KeyW'], brake: ['ArrowDown', 'KeyS'], left: ['ArrowLeft', 'KeyA'], right: ['ArrowRight', 'KeyD'], nitro: ['Space', 'ShiftLeft'], gearUp: ['KeyE', 'KeyX'], gearDown: ['KeyQ', 'KeyZ'] },
      p1: { accel: ['KeyW'], brake: ['KeyS'], left: ['KeyA'], right: ['KeyD'], nitro: ['ShiftLeft'], gearUp: ['KeyE'], gearDown: ['KeyQ'] },
      p2: { accel: ['ArrowUp'], brake: ['ArrowDown'], left: ['ArrowLeft'], right: ['ArrowRight'], nitro: ['ShiftRight'], gearUp: ['Period'], gearDown: ['Comma'] },
    };
  };
  I.mergeKeys = function (k) {
    const d = I.defaultKeys();
    if (!k || typeof k !== 'object') return d;
    I.PROFILES.forEach((p) => {
      if (!k[p]) return;
      I.ACTIONS.forEach((a) => {
        if (Array.isArray(k[p][a])) {
          const n = p === 'solo' ? 2 : 1;
          const arr = k[p][a].slice(0, n).map((x) => (typeof x === 'string' ? x : ''));
          while (arr.length < n) arr.push('');
          d[p][a] = arr;
        }
      });
    });
    return d;
  };

  I.init = function () {
    window.addEventListener('keydown', (e) => {
      const code = e.code || e.key;
      if (e.key && e.key.length === 1) I.labels[code] = e.key.toUpperCase();
      if (!e.repeat) I.queue.push(code);
      I.down.add(code);
      for (let i = I.listeners.length - 1; i >= 0; i--) {
        if (I.listeners[i](e, code) === true) { e.preventDefault(); return; }
      }
      const fkey = /^F\d+$/.test(code);
      if (!e.metaKey && !fkey && !(e.ctrlKey && !/^Control/.test(code))) e.preventDefault();
    });
    window.addEventListener('keyup', (e) => { I.down.delete(e.code || e.key); });
    window.addEventListener('blur', () => { I.down.clear(); I.tdown.clear(); });
  };
  I.on = (fn) => { I.listeners.push(fn); return () => { const i = I.listeners.indexOf(fn); if (i >= 0) I.listeners.splice(i, 1); }; };
  I.frame = function () {
    I.pressed = new Set(I.queue);
    I.queue.length = 0;
    I.tpressed = new Set(I.tqueue);
    I.tqueue.length = 0;
  };
  I.keysFor = (profile, act) => ((TG.Save.data.keys[profile] || {})[act] || []);
  I.action = function (profile, act) {
    const keys = I.keysFor(profile, act);
    for (let i = 0; i < keys.length; i++) if (keys[i] && I.down.has(keys[i])) return true;
    return profile !== 'p2' && I.tdown.has(act);
  };
  I.hit = function (profile, act) {
    const keys = I.keysFor(profile, act);
    for (let i = 0; i < keys.length; i++) if (keys[i] && I.pressed.has(keys[i])) return true;
    return profile !== 'p2' && I.tpressed.has(act);
  };

  const NAMES = {
    ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Space: 'Space', Enter: 'Enter', Escape: 'Esc',
    ShiftLeft: 'L Shift', ShiftRight: 'R Shift', ControlLeft: 'L Ctrl', ControlRight: 'R Ctrl',
    AltLeft: 'L Alt', AltRight: 'R Alt', MetaLeft: 'L Cmd', MetaRight: 'R Cmd', Tab: 'Tab', Backspace: 'Backspace',
    CapsLock: 'Caps Lock', Period: '.', Comma: ',', Slash: '/', Semicolon: ';', Quote: "'", BracketLeft: '[', BracketRight: ']',
    Backslash: '\\', Minus: '-', Equal: '=', IntlBackslash: '\\', Backquote: '`',
  };
  I.keyName = function (code) {
    if (!code) return '—';
    if (NAMES[code]) return NAMES[code];
    if (/^Key[A-Z]$/.test(code)) return code.slice(3);
    if (/^Digit\d$/.test(code)) return code.slice(5);
    if (/^Numpad/.test(code)) return 'Num ' + code.slice(6);
    if (I.labels[code]) return I.labels[code];
    return code;
  };
  I.RESERVED = new Set(['Escape', 'KeyP', 'KeyM', 'Enter']);
})(window.TG);

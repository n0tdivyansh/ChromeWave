'use strict';
/* ============================================================
   Saved game (localStorage + native app bridge)
   ============================================================ */
(function (TG) {
  const U = TG.U;
  const KEY = 'speedrush_v1', BAK = KEY + '_bak';
  const S = (TG.Save = { data: null, last: '', lastT: 0 });

  S.defaults = function () {
    return {
      v: 1,
      money: TG.ECON.start,
      cars: { kaito: { color: TG.CAR.kaito.color, up: {} } },
      active: 'kaito',
      unlocked: 1,
      cups: TG.CUPS.map(() => ({ trophy: 0, run: null })),
      records: {},
      ghosts: {},
      settings: { music: 0.6, sfx: 0.85, quality: 'high', units: 'kmh', trans: 'auto', camera: 'near', fps: false, difficulty: 'normal' },
      keys: TG.Input.defaultKeys(),
      stats: { races: 0, wins: 0, earned: 0 },
      quick: { track: 'vegas', laps: 3, rivals: 11 },
      versus: { track: 'vegas', laps: 3, rivals: 5, car2: 'kaito' },
    };
  };

  const parse = (raw) => {
    if (typeof raw !== 'string' || raw.length < 3) return null;
    try { const d = JSON.parse(raw); return d && typeof d === 'object' && d.cars ? d : null; } catch (e) { return null; }
  };
  // Loads the most recent valid save (app disk, browser or backups)
  S.load = function () {
    const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
    const nat = () => { try { return window.__TG_NATIVE_SAVE; } catch (e) { return null; } };
    const natB = () => { try { return window.__TG_NATIVE_BAK; } catch (e) { return null; } };
    const main = [parse(nat()), parse(get(KEY))].filter(Boolean);
    main.sort((a, b) => (b.savedAt || 0) - (a.savedAt || 0));
    let d = main[0] || null;
    if (!d) d = parse(natB()) || parse(get(BAK));
    S.data = S.migrate(d);
    S.last = JSON.stringify(Object.assign({}, S.data, { savedAt: 0 }));
    // ask the browser not to evict the game's data
    try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {}); } catch (e) { /* not available */ }
  };

  S.migrate = function (d) {
    const def = S.defaults();
    if (!d || typeof d !== 'object') return def;
    S.renameCars(d);
    const out = Object.assign({}, def, d);
    out.settings = Object.assign({}, def.settings, d.settings || {});
    out.cups = def.cups.map((c, i) => Object.assign({}, c, (Array.isArray(d.cups) && d.cups[i]) || {}));
    out.cars = {};
    if (d.cars && typeof d.cars === 'object') {
      Object.keys(d.cars).forEach((id) => {
        if (!TG.CAR[id]) return;
        const c = d.cars[id] || {};
        out.cars[id] = { color: typeof c.color === 'string' ? c.color : TG.CAR[id].color, up: Object.assign({}, c.up || {}) };
        TG.UPGRADES.forEach((u) => { out.cars[id].up[u.id] = U.clamp(out.cars[id].up[u.id] | 0, 0, u.max); });
        if (c.det && typeof c.det === 'object') {
          const hex = (v) => typeof v === 'string' && /^#[0-9a-f]{6}$/i.test(v);
          const D = TG.DETAIL, det = {};
          ['sec', 'rim', 'caliper'].forEach((k) => { if (hex(c.det[k])) det[k] = c.det[k]; });
          if (D.finishes.some((x) => x.id === c.det.finish)) det.finish = c.det.finish;
          if (D.tints.some((x) => x.id === c.det.tint)) det.tint = c.det.tint;
          if (Object.keys(det).length) out.cars[id].det = det;
        }
      });
    }
    if (!Object.keys(out.cars).length) out.cars = def.cars;
    if (!out.cars[out.active]) out.active = Object.keys(out.cars)[0];
    out.keys = TG.Input.mergeKeys(d.keys);
    out.records = d.records && typeof d.records === 'object' ? d.records : {};
    out.ghosts = d.ghosts && typeof d.ghosts === 'object' ? d.ghosts : {};
    out.stats = Object.assign({}, def.stats, d.stats || {});
    out.quick = Object.assign({}, def.quick, d.quick || {});
    out.versus = Object.assign({}, def.versus, d.versus || {});
    out.unlocked = U.clamp((d.unlocked | 0) || 1, 1, TG.CUPS.length);
    out.money = Math.max(0, Math.round(+d.money || 0));
    if (!isFinite(out.money)) out.money = def.money;
    return out;
  };

  // saves from before the 2026-10 car lineup: move every car id to its new name
  S.renameCars = function (d) {
    const R = TG.CAR_RENAME || {};
    const nid = (id) => R[id] || id;
    if (d.cars && typeof d.cars === 'object') {
      const cars = {};
      Object.keys(d.cars).forEach((id) => {
        const c = d.cars[id], n = nid(id);
        // still in the old factory paint: take the new design's own colour (custom paint jobs are kept)
        if (n !== id && c && TG.CAR_OLD_PAINT && c.color === TG.CAR_OLD_PAINT[n]) delete c.color;
        cars[n] = c;
      });
      d.cars = cars;
    }
    if (typeof d.active === 'string') d.active = nid(d.active);
    if (d.versus && typeof d.versus.car2 === 'string') d.versus.car2 = nid(d.versus.car2);
    Object.values(d.records || {}).forEach((r) => { if (r && typeof r.lapCar === 'string') r.lapCar = nid(r.lapCar); });
    Object.values(d.ghosts || {}).forEach((g) => { if (g && typeof g.car === 'string') g.car = nid(g.car); });
  };

  S.save = function (why) {
    if (!S.data) return;
    S.data.savedAt = Date.now();
    const s = JSON.stringify(S.data);
    try {
      // backup of the previous version (at most one per minute)
      const now = Date.now();
      if (now - S.lastT > 60000) { const prev = localStorage.getItem(KEY); if (prev) localStorage.setItem(BAK, prev); }
      localStorage.setItem(KEY, s);
    } catch (e) { /* storage not available */ }
    try {
      if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.tgSave) window.webkit.messageHandlers.tgSave.postMessage(s);
    } catch (e) { /* no native bridge */ }
    S.last = JSON.stringify(Object.assign({}, S.data, { savedAt: 0 }));
    S.lastT = Date.now();
    if (S.onSaved) S.onSaved(why);
  };
  // Autosave: saves if anything changed since last time
  S.autosave = function (why) {
    if (!S.data) return false;
    const cur = JSON.stringify(Object.assign({}, S.data, { savedAt: 0 }));
    if (cur === S.last) return false;
    S.save(why || 'auto');
    return true;
  };
  // Export / import the save (to copy it to another browser or computer)
  S.exportText = () => JSON.stringify(Object.assign({ game: 'Speed Rush' }, S.data), null, 1);
  S.importText = function (text) {
    const d = parse(text);
    if (!d) return false;
    S.data = S.migrate(d);
    S.save('import');
    return true;
  };

  S.reset = function () {
    const keys = S.data ? S.data.keys : null;
    const settings = S.data ? S.data.settings : null;
    S.data = S.defaults();
    if (keys) S.data.keys = keys;
    if (settings) S.data.settings = settings;
    S.save();
  };

  S.car = (id) => S.data.cars[id || S.data.active];
  S.activeModel = () => TG.CAR[S.data.active];
})(window.TG);

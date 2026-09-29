'use strict';
/* ============================================================
   Race HUD: retro digital dash
   - top center: race strip (position, lap, lap time, total, best, ghost)
   - bottom center: segmented LED rev bar, digital speed and gear
   - bottom left: nitro bottles, fuel gauge and damage
   - bottom right: neon minimap
   ============================================================ */
(function (TG) {
  const U = TG.U, C = TG.C;
  const HUD = (TG.HUD = {});
  const F_DATA = '"Silkscreen", "Courier New", monospace';
  const F_DISP = '"Press Start 2P", "Courier New", monospace';
  const F_BODY = '"VT323", "Courier New", monospace';
  const F_LOGO = F_DISP;
  const HOT = '#e0558c', NEON = '#7cc9d9', CHALK = '#f3f5f8', SIGNAL = '#ff3b3b', GOLD = '#ffd23f', OK = '#46d98a';
  const MUTE = 'rgba(243,245,248,0.55)';

  const font = (w, px, fam, it) => (it ? 'italic ' : '') + (fam === F_DISP ? 400 : w) + ' ' + Math.round(px) + 'px ' + fam;
  const R_t = () => (TG.Render ? TG.Render.t : 0);
  // color by damage: green → yellow → orange → red
  const dmgCol = (v) => (v < 0.15 ? OK : v < 0.4 ? GOLD : v < 0.7 ? '#ff8a2a' : SIGNAL);

  function txt(ctx, t, x, y, f, col, align, base) {
    ctx.font = f;
    ctx.fillStyle = col;
    ctx.textAlign = align || 'left';
    ctx.textBaseline = base || 'alphabetic';
    ctx.fillText(t, x, y);
  }
  // translucent night-purple plate
  function plate(ctx, x, y, w, h, s) {
    ctx.fillStyle = 'rgba(14,16,22,0.74)';
    U.rr(ctx, x, y, w, h, 12 * s); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.09)'; ctx.lineWidth = Math.max(1, s); ctx.stroke();
  }
  // slanted LED segment
  function seg(ctx, x, y, w, h, sk) {
    ctx.beginPath(); ctx.moveTo(x + sk, y); ctx.lineTo(x + w + sk, y); ctx.lineTo(x + w, y + h); ctx.lineTo(x, y + h); ctx.closePath();
  }
  function glow() { /* the calm look has no glows */ }

  HUD.msg = function (v, text, o) {
    o = o || {};
    v.msgs = v.msgs.filter((m) => m.slot !== (o.slot || 'main'));
    v.msgs.push({ text, sub: o.sub || '', t: 0, dur: o.dur || 1.6, col: o.col || CHALK, slot: o.slot || 'main', big: o.big || 1 });
  };
  HUD.float = function (v, text, col) {
    v.floats = v.floats || [];
    v.floats.push({ text, col: col || GOLD, t: 0 });
  };

  HUD.mapImage = function (race, size) {
    const key = size;
    if (race._map && race._map.key === key) return race._map.img;
    const cv = U.canvas(size, size);
    const c = cv.getContext('2d');
    const pts = race.track.map.pts, N = race.track.N;
    const pad = size * 0.12, S = size - pad * 2;
    c.lineJoin = 'round'; c.lineCap = 'round';
    const path = () => {
      c.beginPath();
      for (let i = 0; i < N; i += 2) {
        const x = pad + (pts[i * 2] + 0.5) * S, y = pad + (pts[i * 2 + 1] + 0.5) * S;
        if (i === 0) c.moveTo(x, y); else c.lineTo(x, y);
      }
      c.closePath();
    };
    path(); c.strokeStyle = 'rgba(124,201,217,0.14)'; c.lineWidth = size * 0.07; c.stroke();
    path(); c.strokeStyle = NEON; c.lineWidth = size * 0.018; c.stroke();
    c.shadowBlur = 0;
    const sx = pad + (pts[0] + 0.5) * S, sy = pad + (pts[1] + 0.5) * S;
    c.fillStyle = HOT; c.fillRect(sx - size * 0.035, sy - size * 0.014, size * 0.07, size * 0.028);
    race._map = { key, img: cv, pad, S };
    return cv;
  };

  /* ---------------- Top: race strip ---------------- */
  function strip(ctx, race, v, p, vw, s, m) {
    const lapN = U.clamp(p.lapsDone + 1, 1, race.laps);
    const cur = p.finished ? p.lastLap : race.phase === 'race' || race.phase === 'done' ? race.time - p.lapStart : 0;
    const cells = [
      { w: 150, label: 'POSITION', pos: true },
      { w: 84, label: 'LAP', val: lapN + '/' + race.laps, col: p.finished ? HOT : CHALK },
      { w: 116, label: 'LAP TIME', val: U.timeShort(p.lapsDone < 0 && race.phase !== 'race' ? 0 : cur), col: CHALK },
      { w: 116, label: 'TOTAL', val: U.timeShort(p.finished ? p.finishTime : race.time), col: CHALK },
      { w: 116, label: 'BEST', val: U.timeShort(p.bestLap), col: NEON },
    ];
    if (race.mode === 'time' && race.ghostData) {
      cells.push({ w: 116, label: 'GHOST', val: U.timeShort(race.ghostData.time), col: race.ghostCar && race.ghostCar.visible ? HOT : MUTE });
    }
    const h = 64 * s, w = cells.reduce((a, c) => a + c.w * s, 0) + 16 * s;
    const x0 = (vw - w) / 2, y = m;
    plate(ctx, x0, y, w, h, s);
    let x = x0 + 8 * s;
    cells.forEach((c, i) => {
      const cw = c.w * s;
      if (i) { ctx.fillStyle = 'rgba(255,255,255,0.08)'; ctx.fillRect(x, y + 14 * s, Math.max(1, s), h - 24 * s); }
      txt(ctx, c.label, x + 14 * s, y + 24 * s, font(700, 11 * s, F_DATA), MUTE);
      if (c.pos) {
        const t = U.ord(p.pos).toUpperCase();
        txt(ctx, t, x + 14 * s, y + 55 * s, font(800, 24 * s, F_LOGO), p.pos === 1 ? GOLD : CHALK);
        ctx.font = font(800, 24 * s, F_LOGO);
        const tw = ctx.measureText(t).width;
        txt(ctx, '/' + race.cars.length, x + 20 * s + tw, y + 55 * s, font(700, 16 * s, F_DATA), MUTE);
      } else {
        txt(ctx, c.val, x + 14 * s, y + 51 * s, font(700, 17 * s, F_DATA), c.col);
      }
      x += cw;
    });
    // position-change arrows next to the strip
    (v.msgs || []).forEach((mm) => {
      if (mm.slot !== 'pos') return;
      const k = 1 - mm.t / mm.dur;
      ctx.globalAlpha = Math.min(1, k * 3);
      txt(ctx, mm.text, x0 - 12 * s, y + 44 * s - (1 - k) * 10 * s, font(700, 24 * s, F_DATA), mm.col, 'right');
      ctx.globalAlpha = 1;
    });
    // slipstream pill under the strip
    if (p.draft > 0.5 && !p.finished) {
      const pw = 132 * s, ph = 24 * s, px = vw / 2 - pw / 2, py = y + h + 8 * s;
      ctx.fillStyle = 'rgba(124,201,217,0.14)'; U.rr(ctx, px, py, pw, ph, ph / 2); ctx.fill();
      ctx.strokeStyle = NEON; ctx.lineWidth = Math.max(1, 1.5 * s); ctx.stroke();
      txt(ctx, 'SLIPSTREAM', vw / 2, py + ph / 2 + 1 * s, font(700, 12 * s, F_DATA), NEON, 'center', 'middle');
    }
  }

  /* ---------------- Bottom center: digital dash ---------------- */
  function dash(ctx, race, p, cx, bottom, s) {
    const w = 390 * s, h = 116 * s, x = cx - w / 2, y = bottom - h;
    plate(ctx, x, y, w, h, s);
    const red = p.model.eng.red, maxR = red * 1.08;
    const rpm = U.clamp(p.rpm / maxR, 0, 1);
    const counting = race.phase === 'count' || race.phase === 'intro';
    // segmented rev bar: taller toward the redline, cyan → pink → red
    const N = 28, gap = 3 * s, sx = x + 18 * s, sw = w - 36 * s, top = y + 14 * s, sh = 22 * s;
    const segW = (sw - gap * (N - 1)) / N;
    for (let i = 0; i < N; i++) {
      const f0 = i / N, f1 = (i + 1) / N, r = ((f0 + f1) / 2) * maxR;
      const hgt = sh * (0.45 + 0.55 * f1);
      const lit = rpm > f0;
      const col = r >= red * 0.94 ? SIGNAL : r >= red * 0.7 ? HOT : NEON;
      const zone = counting && !p.autopilot && r >= red * 0.55 && r <= red * 0.84;
      seg(ctx, sx + i * (segW + gap), top + sh - hgt, segW, hgt, 3 * s);
      if (lit) { ctx.fillStyle = col; glow(ctx, col, 8 * s); } else ctx.fillStyle = zone ? 'rgba(70,217,138,0.5)' : 'rgba(255,255,255,0.08)';
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    const base = y + h - 20 * s;
    // rpm readout (thousands)
    txt(ctx, 'RPM', x + 18 * s, base - 28 * s, font(700, 11 * s, F_DATA), MUTE);
    txt(ctx, (p.rpm / 1000).toFixed(1), x + 18 * s, base, font(700, 24 * s, F_DATA), CHALK);
    // digital speed
    const units = TG.Save.data.settings.units;
    const kmh = p.speed / C.KMH;
    const val = Math.round(units === 'mph' ? kmh * 0.6214 : kmh);
    glow(ctx, 'rgba(61,224,255,0.45)', 12 * s);
    txt(ctx, String(val), cx + 44 * s, base + 2 * s, font(400, 40 * s, F_DISP), CHALK, 'right');
    ctx.shadowBlur = 0;
    txt(ctx, units === 'mph' ? 'MPH' : 'KM/H', cx + 52 * s, base, font(700, 13 * s, F_DATA), NEON);
    // gear box
    const gs = 54 * s, gx = x + w - 18 * s - gs, gy = base - gs + 8 * s;
    const shiftNow = p.manual && p.rpm > red * 0.93;
    const flash = shiftNow && Math.floor(R_t() * 10) % 2;
    ctx.fillStyle = flash ? HOT : 'rgba(224,85,140,0.14)';
    U.rr(ctx, gx, gy, gs, gs, 10 * s); ctx.fill();
    glow(ctx, HOT, 10 * s);
    ctx.strokeStyle = HOT; ctx.lineWidth = 2 * s; ctx.stroke();
    ctx.shadowBlur = 0;
    const gtxt = race.phase === 'race' || race.phase === 'done' ? String(p.gear) : 'N';
    txt(ctx, gtxt, gx + gs / 2, gy + gs / 2 + (p.manual ? -4 : 1) * s, font(800, 24 * s, F_LOGO), flash ? '#1a0a2a' : CHALK, 'center', 'middle');
    if (p.manual) txt(ctx, 'MAN', gx + gs / 2, gy + gs - 9 * s, font(700, 10 * s, F_DATA), flash ? '#1a0a2a' : NEON, 'center', 'middle');
  }

  /* ---------------- Bottom left: nitro, fuel, damage ---------------- */
  function tank(ctx, race, p, x, bottom, s, split) {
    const w = 230 * s, h = (race.demo ? 52 : 92) * s, y = bottom - h;
    plate(ctx, x, y, w, h, s);
    // nitro bottles
    txt(ctx, 'NITRO', x + 16 * s, y + 30 * s, font(700, 11 * s, F_DATA), MUTE);
    const maxN = Math.max(p.st.nitroN, p.nitroN);
    const bw = Math.min(16 * s, (w - 96 * s) / Math.max(1, maxN) - 5 * s), bh = 22 * s;
    for (let i = 0; i < maxN; i++) {
      const bx = x + 76 * s + i * (bw + 5 * s), by = y + 13 * s;
      const full = i < p.nitroN;
      ctx.fillStyle = full ? U.lin(ctx, 0, by, 0, by + bh, [0, NEON, 1, '#5a9fb0']) : 'rgba(255,255,255,0.1)';
      if (full) glow(ctx, NEON, 6 * s);
      U.rr(ctx, bx, by + 4 * s, bw, bh - 4 * s, 4 * s); ctx.fill();
      ctx.fillRect(bx + bw * 0.3, by, bw * 0.4, 5 * s);
      ctx.shadowBlur = 0;
    }
    if (p.nitroT > 0) {
      const k = U.clamp(p.nitroT / p.st.nitroDur, 0, 1);
      ctx.fillStyle = 'rgba(124,201,217,0.2)'; ctx.fillRect(x + 16 * s, y + 40 * s, w - 32 * s, 4 * s);
      ctx.fillStyle = NEON; ctx.fillRect(x + 16 * s, y + 40 * s, (w - 32 * s) * k, 4 * s);
    }
    if (race.demo) return y;
    // segmented fuel gauge
    const low = p.fuel < 20;
    txt(ctx, 'FUEL', x + 16 * s, y + 74 * s, font(700, 11 * s, F_DATA), low && Math.floor(R_t() * 3) % 2 ? SIGNAL : MUTE);
    const N = 12, fx = x + 76 * s, fw = w - 92 * s, gap = 3 * s, sw2 = (fw - gap * (N - 1)) / N;
    const col = low ? SIGNAL : p.fuel < 45 ? GOLD : OK;
    for (let i = 0; i < N; i++) {
      const on = p.fuel / 100 > i / N;
      seg(ctx, fx + i * (sw2 + gap), y + 60 * s, sw2, 16 * s, 3 * s);
      ctx.fillStyle = on ? col : 'rgba(255,255,255,0.08)';
      ctx.fill();
    }
    void split;
    return y;
  }
  function damage(ctx, p, x, bottom, s) {
    const w = 230 * s, h = 44 * s, y = bottom - h;
    plate(ctx, x, y, w, h, s);
    txt(ctx, 'DAMAGE', x + 16 * s, y + h / 2 + 5 * s, font(700, 11 * s, F_DATA), MUTE);
    txt(ctx, Math.round(p.dmgT * 100) + '%', x + w - 16 * s, y + h / 2 + 7 * s, font(700, 20 * s, F_DATA), dmgCol(p.dmgT), 'right');
    // top-down car (nose pointing up), each zone colored by its damage
    const cw = 16 * s, chh = h - 12 * s, ccx = x + 100 * s, ccy = y + 6 * s, d = p.dmg;
    ctx.fillStyle = 'rgba(255,255,255,0.1)'; U.rr(ctx, ccx - cw / 2, ccy, cw, chh, 5 * s); ctx.fill();
    ctx.fillStyle = dmgCol(d.f); U.rr(ctx, ccx - cw / 2 + 2 * s, ccy + 1 * s, cw - 4 * s, chh * 0.22, 3 * s); ctx.fill();
    ctx.fillStyle = dmgCol(d.r); U.rr(ctx, ccx - cw / 2 + 2 * s, ccy + chh * 0.77, cw - 4 * s, chh * 0.22, 3 * s); ctx.fill();
    ctx.fillStyle = dmgCol(d.l); ctx.fillRect(ccx - cw / 2 - 1 * s, ccy + chh * 0.26, 3 * s, chh * 0.48);
    ctx.fillStyle = dmgCol(d.rt); ctx.fillRect(ccx + cw / 2 - 2 * s, ccy + chh * 0.26, 3 * s, chh * 0.48);
    ctx.fillStyle = dmgCol(d.roof); U.rr(ctx, ccx - cw * 0.28, ccy + chh * 0.34, cw * 0.56, chh * 0.32, 2 * s); ctx.fill();
  }

  /* ---------------- Bottom right: minimap ---------------- */
  function minimap(ctx, race, p, x, y, ms, s) {
    plate(ctx, x, y, ms, ms, s);
    const size = Math.round(ms);
    const img = HUD.mapImage(race, size);
    ctx.drawImage(img, x, y, ms, ms);
    const mp = race._map, pts = race.track.map.pts, sc = ms / size;
    const dot = (car, rad, col) => {
      const i = Math.floor(car.z / C.SEG) % race.track.N;
      const dx = x + (mp.pad + (pts[i * 2] + 0.5) * mp.S) * sc, dy = y + (mp.pad + (pts[i * 2 + 1] + 0.5) * mp.S) * sc;
      ctx.fillStyle = col; ctx.beginPath(); ctx.arc(dx, dy, rad, 0, Math.PI * 2); ctx.fill();
    };
    race.cars.forEach((c) => { if (!c.isPlayer) dot(c, 3 * s, c.pos === 1 ? GOLD : 'rgba(243,245,248,0.8)'); });
    race.players.forEach((c) => {
      const col = c.pIndex === 0 ? HOT : NEON;
      glow(ctx, col, 10 * s);
      if (c === p) { ctx.globalAlpha = 0.35 + 0.25 * Math.sin(R_t() * 6); dot(c, 9 * s, col); ctx.globalAlpha = 1; }
      dot(c, 5 * s, col);
      ctx.shadowBlur = 0;
    });
  }

  HUD.draw = function (ctx, race, v, vw, vh, dt) {
    const p = v.player;
    const split = race.views.length > 1;
    const s = Math.min(vh / 720, vw / 1280) * (split ? 1.3 : 1);
    const m = 22 * s;
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';

    if (race.phase !== 'intro') {
      strip(ctx, race, v, p, vw, s, m);
      // coins chip, top right
      if (race.track.coins) {
        const cw = 128 * s, ch = 38 * s, cx = vw - m - cw;
        plate(ctx, cx, m, cw, ch, s);
        ctx.fillStyle = GOLD; glow(ctx, GOLD, 8 * s);
        ctx.beginPath(); ctx.arc(cx + 22 * s, m + ch / 2, 10 * s, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
        txt(ctx, '$', cx + 22 * s, m + ch / 2 + 1 * s, font(900, 13 * s, F_DISP), '#6a3a00', 'center', 'middle');
        txt(ctx, U.money(p.coinMoney).replace('$', ''), cx + cw - 14 * s, m + ch / 2 + 1 * s, font(700, 20 * s, F_DATA), GOLD, 'right', 'middle');
      }
      const bottom = vh - m;
      dash(ctx, race, p, vw / 2, bottom, s);
      const ty = tank(ctx, race, p, m, bottom, s, split);
      if (!race.demo && p.dmgT > 0.005) damage(ctx, p, m, ty - 8 * s, s);
      const ms = (split ? 120 : 160) * s;
      minimap(ctx, race, p, vw - m - ms, bottom - ms, ms, s);
    }

    // --- start lights / countdown: neon rings
    if (race.phase === 'count') {
      const n = 3 - Math.floor(race.phaseT);
      const lx = vw / 2, ly = vh * 0.3;
      const lw = 320 * s, lh = 72 * s;
      plate(ctx, lx - lw / 2, ly - lh / 2, lw, lh, s);
      for (let i = 0; i < 5; i++) {
        const on = i < Math.round((race.phaseT / 3) * 5 + 0.49);
        const x = lx - lw / 2 + 40 * s + i * 60 * s;
        ctx.lineWidth = 5 * s;
        ctx.strokeStyle = on ? HOT : 'rgba(224,85,140,0.2)';
        if (on) glow(ctx, HOT, 20 * s);
        ctx.beginPath(); ctx.arc(x, ly, 18 * s, 0, Math.PI * 2); ctx.stroke();
        if (on) { ctx.fillStyle = 'rgba(224,85,140,0.35)'; ctx.fill(); }
        ctx.shadowBlur = 0;
      }
      const k = race.phaseT % 1;
      ctx.globalAlpha = 1 - k * 0.6;
      glow(ctx, HOT, 30 * s);
      txt(ctx, String(Math.max(1, n)), vw / 2, vh * 0.5, font(800, (96 + k * 30) * s, F_LOGO), CHALK, 'center', 'middle');
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
      if (!p.autopilot) txt(ctx, 'Keep the revs in the green zone', vw / 2, vh * 0.62, font(400, 24 * s, F_BODY), 'rgba(243,245,248,0.85)', 'center', 'middle');
    }
    if (race.phase === 'race' && race.phaseT < 1) {
      const k = race.phaseT;
      ctx.globalAlpha = 1 - k;
      glow(ctx, NEON, 30 * s);
      txt(ctx, 'GO!', vw / 2, vh * 0.46, font(800, (104 + k * 50) * s, F_LOGO), NEON, 'center', 'middle');
      ctx.shadowBlur = 0;
      ctx.globalAlpha = 1;
    }
    // --- track intro
    if (race.phase === 'intro') {
      const k = U.clamp(race.phaseT / 0.5, 0, 1) * U.clamp((2.6 - race.phaseT) / 0.4, 0, 1);
      ctx.globalAlpha = k;
      const y = vh * 0.72;
      ctx.fillStyle = 'rgba(14,16,22,0.8)';
      ctx.fillRect(0, y - 70 * s, vw, 140 * s);
      txt(ctx, race.cup.name.toUpperCase() + '  ·  ' + (race.mode === 'career' ? 'RACE ' + (race.def.index + 1) + ' OF 4' : race.mode === 'time' ? 'TIME ATTACK' : race.mode === 'versus' ? 'HEAD TO HEAD' : 'ARCADE RACE'), vw / 2, y - 34 * s, font(700, 16 * s, F_DATA), NEON, 'center', 'middle');
      glow(ctx, HOT, 18 * s);
      txt(ctx, race.def.name.toUpperCase(), vw / 2, y + 10 * s, font(800, 36 * s, F_LOGO), CHALK, 'center', 'middle');
      ctx.shadowBlur = 0;
      txt(ctx, race.laps + ' LAPS  ·  ' + TG.TIME_LABEL[race.theme.time].toUpperCase() + '  ·  ' + TG.WEATHER_LABEL[race.theme.weather].toUpperCase(), vw / 2, y + 48 * s, font(700, 15 * s, F_DATA), 'rgba(243,245,248,0.75)', 'center', 'middle');
      ctx.globalAlpha = 1;
    }

    // --- center messages
    v.msgs = (v.msgs || []).filter((mm) => (mm.t += dt) < mm.dur);
    v.msgs.forEach((mm) => {
      if (mm.slot === 'pos') return;
      const inK = U.clamp(mm.t / 0.18, 0, 1), outK = U.clamp((mm.dur - mm.t) / 0.3, 0, 1);
      ctx.globalAlpha = Math.min(inK, outK);
      const sc = (0.8 + 0.2 * U.easeOutCubic(inK)) * mm.big;
      const low = mm.slot === 'low';
      ctx.save();
      ctx.translate(vw / 2, low ? vh * 0.4 : vh * 0.3);
      ctx.scale(sc, sc);
      ctx.lineWidth = 6 * s; ctx.strokeStyle = 'rgba(10,4,20,0.6)'; ctx.lineJoin = 'round';
      ctx.font = low ? font(800, 20 * s, F_DISP) : font(800, 32 * s, F_LOGO);
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.strokeText(mm.text, 0, 0);
      glow(ctx, mm.col, 16 * s);
      ctx.fillStyle = mm.col; ctx.fillText(mm.text, 0, 0);
      ctx.shadowBlur = 0;
      if (mm.sub) {
        ctx.font = font(700, 18 * s, F_DATA);
        ctx.strokeText(mm.sub, 0, 36 * s);
        ctx.fillStyle = CHALK; ctx.fillText(mm.sub, 0, 36 * s);
      }
      ctx.restore();
      ctx.globalAlpha = 1;
    });
    // --- floating text (coins)
    if (v.floats && v.carScreen) {
      v.floats = v.floats.filter((f) => (f.t += dt) < 1);
      v.floats.forEach((f) => {
        ctx.globalAlpha = 1 - f.t;
        txt(ctx, f.text, v.carScreen.x, v.carScreen.y - v.carScreen.h * 0.9 - f.t * 60 * s, font(700, 24 * s, F_DATA), f.col, 'center', 'middle');
      });
      ctx.globalAlpha = 1;
    }
    // --- finish
    if (p.finished) {
      const k = U.clamp((race.time - p.finishTime) / 0.4, 0, 1);
      ctx.globalAlpha = k;
      const win = p.finishPos === 1 && race.mode !== 'time';
      glow(ctx, win ? GOLD : HOT, 24 * s);
      txt(ctx, win ? 'VICTORY!' : 'FINISH!', vw / 2, vh * 0.34, font(800, 48 * s, F_LOGO), win ? GOLD : CHALK, 'center', 'middle');
      ctx.shadowBlur = 0;
      if (race.mode !== 'time') txt(ctx, 'You finish ' + U.ord(p.pos), vw / 2, vh * 0.34 + 54 * s, font(700, 26 * s, F_DATA), CHALK, 'center', 'middle');
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  };
})(window.TG);

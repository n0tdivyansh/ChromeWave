/* ============================================================
   Chromewave · touch.js
   On-screen controls for phones and tablets: a steering pad, gas,
   brake, nitro, gear buttons (manual gearbox only), pause, and a
   skip button for the finish-line view. They feed TG.Input's touch
   actions (player 1 / solo), so the race code needs no changes.
   Menus: the "Backspace" key hint is tappable and goes back.
   ============================================================ */
(function (TG) {
  const T = (TG.Touch = { on: false });
  let root = null;

  function enable() {
    if (T.on) return;
    T.on = true;
    document.documentElement.classList.add('touch');
  }
  if (window.matchMedia && matchMedia('(pointer: coarse)').matches) enable();
  window.addEventListener('touchstart', enable, { once: true, passive: true });

  const capture = (el, id) => { try { el.setPointerCapture(id); } catch (err) { /* pointer already gone */ } };

  // a button that stays pressed while a finger is on it
  function hold(el, act) {
    const I = TG.Input;
    const up = () => { I.tpress(act, false); el.classList.remove('on'); };
    el.addEventListener('pointerdown', (e) => { e.preventDefault(); capture(el, e.pointerId); I.tpress(act, true); el.classList.add('on'); });
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
    el.addEventListener('lostpointercapture', up);
  }

  function build() {
    root = document.createElement('div');
    root.id = 'touch';
    root.innerHTML =
      '<button class="tc-pause" data-tc="pause" aria-label="Pause"><i></i><i></i></button>' +
      '<div class="tc-gears"><button data-act="gearDown">−</button><button data-act="gearUp">+</button></div>' +
      '<div class="tc-steer"><span class="tc-l">◀</span><span class="tc-r">▶</span></div>' +
      '<div class="tc-pedals"><button class="tc-nitro" data-act="nitro">NOS</button><button class="tc-brake" data-act="brake">Brake</button>' +
      '<button class="tc-gas" data-act="accel">Gas</button></div>' +
      '<button class="tc-skip" data-tc="skip">Skip</button>';
    document.body.appendChild(root);
    root.addEventListener('contextmenu', (e) => e.preventDefault());
    root.querySelectorAll('[data-act]').forEach((b) => hold(b, b.dataset.act));

    // steering pad: left or right half, following the finger as it slides across
    const I = TG.Input, pad = root.querySelector('.tc-steer');
    const steer = (e) => {
      const r = pad.getBoundingClientRect(), left = e.clientX < r.left + r.width / 2;
      I.tpress('left', left); I.tpress('right', !left);
      pad.dataset.side = left ? 'l' : 'r';
    };
    const release = () => { I.tpress('left', false); I.tpress('right', false); delete pad.dataset.side; };
    pad.addEventListener('pointerdown', (e) => { e.preventDefault(); capture(pad, e.pointerId); pad._id = e.pointerId; steer(e); });
    pad.addEventListener('pointermove', (e) => { if (pad.dataset.side && e.pointerId === pad._id) steer(e); });
    pad.addEventListener('pointerup', release);
    pad.addEventListener('pointercancel', release);
    pad.addEventListener('lostpointercapture', release);

    root.querySelector('[data-tc="pause"]').addEventListener('click', () => { const G = TG.Game; if (G.race && !G.paused) G.pause(); });
    root.querySelector('[data-tc="skip"]').addEventListener('click', () => { const r = TG.Game.race; if (r) r.skipFin = true; });
  }

  // shown only while the player is actually racing (not in menus, the demo race or the pause screen)
  function sync() {
    const G = TG.Game, race = G && G.race;
    const live = !!(T.on && race && !race.demo && !G.paused && !TG.UI.cur);
    root.classList.toggle('show', live);
    if (live) {
      root.dataset.phase = race.phase;
      root.classList.toggle('manual', !!(race.players[0] && race.players[0].manual));
    } else if (TG.Input.tdown.size) TG.Input.tclear();
    requestAnimationFrame(sync);
  }

  // menus: the "Backspace" hint works as a back button (touch or mouse)
  document.addEventListener('click', (e) => {
    const h = e.target.closest && e.target.closest('.hints [data-back]');
    if (h && TG.UI.cur) TG.UI.back();
  });

  window.addEventListener('load', () => { build(); requestAnimationFrame(sync); });
})(window.TG);

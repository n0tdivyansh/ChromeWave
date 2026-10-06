'use strict';
/* ============================================================
   CrazyGames SDK v3 bridge (https://docs.crazygames.com/sdk/intro/)
   ------------------------------------------------------------
   Off CrazyGames (other sites: environment 'disabled'), offline or with the
   SDK blocked, every call is a harmless no-op and the game runs as usual.
   ============================================================ */
(function (TG) {
  const P = (TG.Portal = { on: false, store: null, playing: false, lastAd: 0, noAds: false });
  const sdk = () => window.CrazyGames && window.CrazyGames.SDK;
  const AD_GAP = 180000; // CrazyGames: about 3 minutes between midgame ads

  P.init = async function () {
    try {
      if (!sdk()) return;
      await sdk().init();
      P.on = sdk().environment !== 'disabled';
      if (P.on && sdk().data) P.store = sdk().data; // progress linked to the player's CrazyGames account
    } catch (e) { P.on = false; }
  };
  const call = (fn) => { if (P.on) try { fn(sdk()); } catch (e) { /* the SDK refused the call */ } };

  P.loadingStart = () => call((s) => s.game.loadingStart());
  P.loadingStop = () => call((s) => s.game.loadingStop());
  // gameplay on/off: sent only on a change (race start / resume, and pause / menus / race end)
  P.gameplay = function (on) {
    if (on === P.playing) return;
    P.playing = on;
    call((s) => (on ? s.game.gameplayStart() : s.game.gameplayStop()));
  };
  P.happytime = () => call((s) => s.game.happytime());

  // Video ad ('midgame' between races, 'rewarded' on request). The sound is muted while it
  // runs; done(watched) is always called exactly once, also when no ad is available.
  P.ad = function (type, done) {
    if (!P.on || (type === 'midgame' && Date.now() - P.lastAd < AD_GAP)) { done(false); return; }
    let over = false;
    const end = (ok) => {
      if (over) return;
      over = true;
      TG.Audio.adMute(false);
      if (ok) P.lastAd = Date.now();
      done(ok);
    };
    try {
      sdk().ad.requestAd(type, { adStarted: () => TG.Audio.adMute(true), adFinished: () => end(true),
        // ads off for this player (Basic Launch, ad blocker): stop offering rewarded ads
        adError: (err) => { if (/adsDisabled|adblock/i.test(JSON.stringify(err || ''))) P.noAds = true; end(false); } });
    } catch (e) { end(false); }
  };
})(window.TG);

# Chromewave (Speed Rush) - Retro 80s Arcade Racer

A high-speed, retro 80s pseudo-3D arcade racer in the spirit of *OutRun* and *Top Gear*. Built in pure JavaScript and WebGL with zero runtime dependencies.

Features 39 original cars across 10 distinct brands, a drift-to-nitro mechanic, procedural tracks across multiple cups and weather themes, and full **CrazyGames SDK v3** integration.

---

## 🕹️ Controls

| Action | Keyboard | Touch / Mobile |
|---|---|---|
| **Steer** | `A` / `D` or Left / Right Arrows | Left / Right on-screen steer zones |
| **Accelerate** | `W` or Up Arrow | Auto-accelerate / Gas button |
| **Brake / Reverse** | `S` or Down Arrow | Brake button |
| **Nitro Boost** | `Space` (hold to burn drift charge) | Nitro button |
| **Pause** | `P` | Pause icon |
| **Menu Back** | `Backspace` | Back button |

---

## 🏎️ Features

- **39 Original Cars**: Hand-designed low-poly models across 10 fictional manufacturers (*Hoshida*, *Volkhar*, *Thornbury*, *Boone*, *Rovenza*, *Kova*, *Calder*, *Vireo*, *Arvane*, *Lindqvist*).
- **Drift Nitro**: Pushing hard into turns and sliding fills your nitro reserve. Hold `Space` to dump nitro for blistering straightaway bursts.
- **Dynamic Weather & Lighting**: Day, sunset, dusk, night city skylines, desert dunes, and mountain passes.
- **Garage & Customization**: Paint jobs, visual detailing, tuning upgrades (Top Speed, Acceleration, Handling, Nitro Tank/Fill).
- **Self-Contained Architecture**: Dual renderer — custom WebGL car rendering with automatic 2D canvas fallback.
- **CrazyGames SDK v3 Ready**: Gameplay lifecycle hooks, midgame interstitial ads, rewarded double prizes, and cloud save persistence.

---

## 🚀 Run & Build

### Local Development
Run any lightweight static server inside the `speedrush/` folder:

```bash
# Python 3
python -m http.server 5179

# Open in browser:
http://localhost:5179
```

### Production Build (Single-File HTML)
Packages the complete game, scripts, styles, and embedded fonts into one standalone file ready for web portals or local play:

```bash
node build.js dist/index.html
```

The resulting `dist/index.html` can be zipped and uploaded directly to the CrazyGames Developer Portal or any HTML5 game host.

# Speed Rush — notes for Claude

Retro 80s pseudo-3D arcade racer (OutRun / Top Gear style). Plain JS, no npm, no libraries: classic
scripts sharing `window.TG`, loaded in order by `index.html`. `node build.js dist/index.html` inlines
everything into one self-contained file for upload (zip it as `dist/SpeedRush-web.zip`).
Repo: github.com/n0tdivyansh/SpeedRush.

## Run and test

- Dev server: `.claude/launch.json` (in `games-clone/`) has `speedrush` = `python -m http.server 5179 -d speedrush`.
  Open http://localhost:5179. After code/model changes press **Ctrl+F5** (the browser caches the scripts).
- URL test hooks (`js/main.js` `G.testHook`): `?screen=garage|dealer|...`, `?money=9999999`, `?own=id,id`,
  `?race=vegas&car=kaito&skip=8&auto=1&freeze=1&rivals=11`, `?p2=<car>` (versus).
- Console checks: `Object.keys(TG.CarGL.cars).length` (39 = every model decoded), `TG.CarGL.hasMat(id, 'sec')`.
- PowerShell users: call Blender with `& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" ...`
  (bash-style `"/c/Program Files/..."` fails in PowerShell).

## Code map

| File | Role |
|---|---|
| `js/data.js` | constants `TG.C`, 39 cars `TG.CARS` (identity, balance stats, `side`/`rear` blocks for the 2D fallback — generated), `TG.CAR_RENAME` (old ids → new), upgrades, `TG.DETAIL` (detailing shop), economy, cups, themes |
| `js/track.js` | seeded track generator (segments, scenery, pickups, minimap) |
| `js/race.js` | `Race` class, fixed 120 Hz step: physics, AI, collisions, crashes, laps, ghost, drift nitro |
| `js/render.js` | pseudo-3D road renderer (2D canvas) |
| `js/car-gl.js` | WebGL cars: decodes `TG.CarModels` (lp2), renders each car offscreen and blits it; shader materials table `MAT` |
| `js/car-models.js` | **generated** car meshes (do not edit by hand) |
| `js/car3d.js`, `js/art-cars.js` | 2D-canvas fallback cars (no WebGL), driven by the generated `side`/`rear` blocks |
| `js/ui.js` | menus: garage, shop, paint, dealer (showroom), detailing |
| `js/save.js` | save key `speedrush_v1`; `S.renameCars` maps pre-2026-10 car ids via `TG.CAR_RENAME` |
| `js/finish.js`, `js/hud.js`, `js/audio.js`, `js/music.js`, `js/input.js`, `js/touch.js` | as named |

## Car models — original lineup (2026-10-01)

The game's first cars came from a friend's game. To keep them out of any copyright conversation, **the
whole car side is now our own**: the friend's generator, exporter and preview studio were deleted from
the repo (2026-10-01), and the lineup was redesigned — 39 invented cars, 10 invented brands
(Hoshida, Volkhar, Thornbury, Boone, Rovenza, Kova, Calder, Vireo, Arvane, Lindqvist), new ids,
names, blurbs, colours, liveries, proportions and body types. Only the balance stats per slot (price,
speed, acceleration, handling, gears, engine sound) were kept. Never reintroduce the old car names,
brands or ids (other than inside `TG.CAR_RENAME`, which exists only to migrate old saves).

Pipeline (Blender 5.2, headless, all our own Python in `speedrush/blender/`):

- `lowpoly.py` — builder: body loft (cross-section rings, quad-strip end caps, creases) → Subdivision
  Surface level 2 → boolean wheel arches → greenhouse loft (subdivided) → details laid onto the surface by
  ray-cast (`conform`, optional raised bezel walls) → finishing (`arch_lips`, `shut_lines`, `mirror_part`)
  → join → `shade()` (smooth, creases > 32° sharp). Wheels: `lp_wheel` (32-sided tyre, rim styles
  5/6/10/Y, lug nuts, disc, caliper).
- `lp_arch.py` — 7 archetypes (`mid`, `gt`, `notch`, `rear`, `hatch`, `lmp`, `beetle`): `make()` turns a
  car's size + wheel positions into body/cabin curves; detail kit: `front_lights`, `rear_lights`, `grille`,
  `splitter`, `diffuser`, `exhausts`, `wing` (duck/lip/wing/swan/roof), `side_intake`, `fender_vents`,
  `louvers`, `hood_vents`, `naca`, `roof_scoop`, `fin`, `side_band`, `roundel`, `blower`; `kit_base` adds
  mirrors, wipers, door lines and number plates. Kit functions record `tail_style`/`wing_style`/
  `exhaust_style`/`front_style`/`grille_style` on the spec for the 2D fallback data.
- `cars_lp/roster.py` — **the lineup**: `CARS` in slot order (`car(slot, id, brand, name, blurb, kind,
  (L, W, wheelbase, front overhang[, H]), paint, sec=…, rim=…, details=[…], …)`). Identity in `data.js`
  must match it. Race cars (details using `RACE`) get no number plates.
- `lp_export.py` — our "lp2" model format (see its docstring): AO bake (golden-spiral rays + smoothing),
  zlib-packed planes, glow/flame anchors, and the `side` / `rear` blocks for `data.js`.
- `lp_preview.py` — EEVEE studio renders → `out/preview/<id>.png`.
- `lp_build.py` — runner. Rebuild everything (~20 min):
  `blender -b --factory-startup -P speedrush/blender/lp_build.py -- all --export [--render]`
  Single cars: `-- kaito aster --export` (car-models.js is rewritten from every `out/<id>.json`, so do a
  full build first on a fresh checkout — `out/` is build output, not committed).

Builder material names must exist in `lp_export.BUILD_MATS` (or be `c_RRGGBB` liveries); game material
names in `lp_export.GAME_MATS` must exist in `car-gl.js` `MAT`.

### Detailing shop contract (`TG.DETAIL`, `CG.colors` in car-gl.js)

- Paint → `paint`/`wing_paint`; finish (metallic/pearl/satin/matte/chrome) → `paint`, `wingp`, `sec`, `wings`.
- Accent → `sec`. The shop only shows the Accent row if `CG.hasMat(id, 'sec')`, so **every car must have
  `sec` faces**: side skirts (body profile segment k=1) and mirror housings are `sec` on all cars.
- Rims → `rim` (spokes, lip, barrel), calipers → `caliper` (wheel mesh), window tint → `glass`.

## Drift nitro (2026-10-01)

Players no longer get 3 nitro charges. `car.nitroM` (0..1 tank, starts at 0.34) fills while drifting:
`race.js stepPlayer` adds `slip * st.nitroFill * dt` when `car.slip > 0.22`, speed > 35% and on the road;
a finished drift emits `drift` (HUD "DRIFT +x%"). Holding the nitro key (`inp.nitroHold`, `I.action`)
burns the tank (`st.nitroTank` seconds when full) by keeping `car.nitroT` > 0, so every existing
`nitroT > 0` effect (speed, flames, FOV, audio) still applies. Blue canisters add 0.34. Stats in
`TG.carStats`: `nitroTank`, `nitroFill` (nitro upgrade raises both). AI rivals still use timed charges
(`ai.nitroN`). Pushing hard through corners fills about one full tank per lap.

## Gotchas

- `car-gl.js` inflates models with `DecompressionStream`; never decode model data through a canvas
  (browsers with anti-fingerprinting noise corrupt it).
- `lp_export.py`, `lp_preview.py`, `lowpoly.py`, `lp_arch.py` and `roster.py` share one exec namespace in
  `lp_build.py`: never reuse a top-level name (a `_lin` clash once broke the colour helper).
- Body profile heights scale with the side height (never fold) — a folded profile makes the EXACT
  boolean delete the body; `apply_boolean` raises if it loses > 40% of faces.
- Light/exhaust/headlight anchors come from `lp_export.anchors` (grid-merged triangle centres).

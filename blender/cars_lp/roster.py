# Speed Rush — the car lineup (original designs). One entry per car, in the game's slot order
# (TG.CARS index: the slot keeps the game balance — price, speed, handling — nothing else).
# Each entry: identity (brand, name, blurb, colours), proportions, archetype and detail kit.
# Runs inside the lp_build.py namespace (lp_arch.py loaded first).

RACE = [splitter('carbon'), diffuser(3, 'carbon')]

# archetype defaults: height, tyre radius, front/rear tyre width, rim radius
KIND_DIMS = {
    'gt': (1.30, 0.345, 0.255, 0.285, 0.272), 'notch': (1.36, 0.34, 0.245, 0.275, 0.245), 'mid': (1.17, 0.335, 0.255, 0.31, 0.276),
    'rear': (1.29, 0.34, 0.255, 0.305, 0.27), 'hatch': (1.42, 0.315, 0.235, 0.235, 0.23), 'lmp': (1.05, 0.345, 0.29, 0.335, 0.258),
    'beetle': (1.30, 0.335, 0.245, 0.27, 0.22),
}


def car(slot, cid, brand, name, blurb, kind, size, paint, sec='#15171b', rim='5', caliper='#c41a1a', rim_color='#b9bec6', **o):
    '''size = (length, width, wheelbase, front overhang[, height]).'''
    L, W, wb, fo = size[:4]
    H, r, wf, wr, rimr = KIND_DIMS[kind]
    H = size[4] if len(size) > 4 else H
    yf = L - fo
    d = dict(id=cid, L=L, W=W, H=H, col=dict(paint=paint, sec=sec, stripe=o.pop('stripe', '#f2f2f2'), caliper=caliper, rim=rim_color),
             wh=dict(yf=yf, yr=yf - wb, tf=round(W - wf - 0.07, 3), tr=round(W - wr - 0.06, 3), rf=r, rr=r + 0.01, wf=wf, wr=wr,
                     rimf=rimr, rimr=rimr))
    return dict(slot=slot, brand=brand, name=name, blurb=blurb, kind=kind, d=d, rim=rim, o=o)


CARS = [
    car(0, 'kaito', 'Hoshida', 'Kaito', 'A light, rev-happy little coupe that teaches you every corner on the map.', 'gt', (4.28, 1.80, 2.52, 0.80),
        '#f2a516', rim='6', spokes=6, rim_color='#1b1c1f', tail_shape='kamm', details=[front_lights('slim'), grille('low', w=0.5), rear_lights('pill'),
        exhausts('dual'), wing('duck'), diffuser(1)]),
    car(1, 'velkor', 'Volkhar', 'Velkor', 'Four seats, all-wheel drive and a turbo six that never runs out of breath.', 'gt', (4.72, 1.90, 2.78, 0.92),
        '#b8bec6', sec='#a3141c', rim='Y', details=[front_lights('wide'), grille('hex'), rear_lights('stack', panel=True), exhausts('quad'),
        hood_vents(x=0.24), diffuser()]),
    car(2, 'arden', 'Thornbury', 'Arden', 'A hand-built British grand tourer with a long bonnet and a V8 that rumbles.', 'gt', (4.58, 1.93, 2.72, 0.86),
        '#1f4d7a', rim='10', spokes=10, rim_color='#c3c7cf', trim='chrome', tail_shape='taper', details=[front_lights('round2'), grille('wide', w=0.45, frame_mat='chrome'),
        rear_lights('round2'), exhausts('quad'), wing('lip'), diffuser()]),
    car(3, 'drover', 'Boone', 'Drover', 'A full-size American bruiser: cream racing band, wide hips and a big-block heart.', 'notch', (5.05, 1.98, 2.88, 0.98),
        '#8a1c1c', rim='5', rim_color='#c9ccd1', trim='chrome', tail_shape='kamm', details=[front_lights('round2'), grille('wide', w=0.82, frame_mat='chrome'),
        rear_lights('wide', panel=True), exhausts('dual'), hood_vents(x=0.22), side_band('c_e8e2d0', h=0.06), diffuser(1)]),
    car(4, 'nimbra', 'Volkhar', 'Nimbra', 'A compact mid-engine sports car, balanced like a dancer.', 'mid', (4.30, 1.88, 2.50, 1.02),
        '#2e8c6e', rim='Y', tail_shape='kamm', rear_mat='paint', details=[buttresses(), splitter(), diffuser(), side_intake(), front_lights('slim'), grille('mouth3'), rear_lights('c'),
        exhausts('center2', z=0.40), wing('lip')]),
    car(5, 'orsa', 'Rovenza', 'Orsa', 'A champagne front-mid V12 coupe for crossing Europe before lunch.', 'gt', (4.70, 1.96, 2.80, 0.90),
        '#c7b38a', rim='10', spokes=10, trim='chrome', tail_shape='drop', details=[front_lights('tear'), grille('hex', frame_mat='chrome'), rear_lights('halo'),
        exhausts('quad'), fender_vents(), diffuser()]),
    car(6, 'zentra', 'Kova', 'Zentra', 'Engine hung out the back, nose light as a feather: steer with your right foot.', 'rear', (4.42, 1.86, 2.44, 0.96),
        '#d94f8a', rim='5', tail_shape='drop', details=[hump(), front_lights('round', size=0.085), grille('low'), rear_lights('bar'), exhausts('center2'),
        wing('duck'), side_intake(k=0.6), diffuser()]),
    car(7, 'sable', 'Calder', 'Sable', 'A graphite mid-engine wedge with orange flashes and a screaming V8.', 'mid', (4.52, 1.94, 2.66, 1.05),
        '#2b2d33', sec='#ff7a1a', rim='10', spokes=10, lower='sec', tail_shape='taper', rear_mat='black', details=[spine(), splitter(), diffuser(), side_intake('sec'),
        front_lights('slim'), grille('low', w=0.6), rear_lights('x'), exhausts('center2', z=0.42), louvers(4), wing('lip')]),
    car(8, 'strale', 'Vireo', 'Strale', 'Bright white, blue below the waist, and sharper than anything else at its price.', 'mid', (4.58, 1.96, 2.68, 1.02),
        '#e4e6ea', sec='#1d5fd6', rim='5', lower='sec', tail_shape='drop', details=[hump(), splitter(), diffuser(), side_intake(), front_lights('tear'),
        grille('mouth3'), rear_lights('hook'), exhausts('quad'), wing('lip')]),
    car(9, 'tessar', 'Rovenza', 'Tessar', 'Long, low and yellow, with a fixed rear wing and a V12 behind your ears.', 'mid', (4.86, 2.04, 2.72, 1.10, 1.14),
        '#ffb21a', rim='Y', tail_shape='kamm', details=[splitter(), diffuser(), side_intake(), front_lights('slim'), grille('mouth3'), rear_lights('strip3'),
        exhausts('twin_high', z=0.60), louvers(5), wing('wing', y0=0.02, chord=0.30)]),
    car(10, 'kairo', 'Hoshida', 'Kairo', 'A hybrid with electric shove off every corner and a petrol howl on the straight.', 'mid', (4.66, 1.98, 2.66, 1.04),
        '#0f7bd8', rim='10', spokes=10, tail_shape='taper', rear_mat='paint', details=[spine(), splitter(), diffuser(), side_intake(), front_lights('blade'), grille('mouth3'),
        rear_lights('blade'), exhausts('hex', z=0.38), wing('lip')]),
    car(11, 'aster', 'Arvane', 'Aster', 'Graphite over copper: a 1,000 hp grand tourer that whispers at 400 km/h.', 'mid', (4.54, 2.00, 2.70, 0.98),
        '#3a3d44', sec='#b0673a', rim='10', spokes=10, lower='sec', trim='chrome', tail_shape='taper', details=[buttresses(), splitter(), diffuser(), side_intake('sec'),
        front_lights('quad'), grille('horseshoe'), rear_lights('split'), exhausts('center1', z=0.34, r=0.07), wing('lip')]),
    car(12, 'nordlys', 'Lindqvist', 'Nordlys', 'A road car shaped by a wind tunnel: fender pods, a slim tub and no wasted air.', 'lmp', (4.74, 1.95, 2.74, 0.96, 1.06),
        '#9fd6c9', sec='#111316', rim='10', spokes=10, roof=1.05, tail_shape='kamm', details=[front_lights('slim'), grille('lmp'), rear_lights('dots'),
        exhausts('center2', z=0.60), wing('lip'), side_band('sec', h=0.03)] + RACE),
    car(13, 'fjell', 'Lindqvist', 'Fjell', 'Twin-turbo V8, swan-neck wing and a top speed that needs its own postcode.', 'mid', (4.64, 2.04, 2.70, 1.06, 1.20),
        '#f2f2f2', sec='#d62828', rim='5', roof=1.19, tail_shape='kamm', details=[spine(), splitter(), diffuser(), side_intake('sec'), front_lights('slim'),
        grille('mouth3'), rear_lights('slim'), exhausts('center2', z=0.44), louvers(5), wing('swan', y0=-0.02, chord=0.32, z=1.27)]),
    car(14, 'solenne', 'Arvane', 'Solenne', 'Black and gold, sixteen cylinders, and nothing on earth goes faster.', 'mid', (4.82, 2.04, 2.72, 1.08),
        '#101318', sec='#c9a24a', rim='10', spokes=10, rim_color='#c9a24a', lower='sec', trim='chrome', tail_shape='drop', rear_mat='paint', details=[hump(), splitter(), diffuser(),
        side_intake('sec'), front_lights('quad'), grille('horseshoe'), rear_lights('quad'), exhausts('hex', z=0.30), wing('lip')]),
    car(15, 'rook', 'Calder', 'Rook', 'A forest-green track special with a big wing and no carpets.', 'gt', (4.50, 1.92, 2.62, 0.88, 1.28),
        '#3f7d3c', rim='10', spokes=10, rim_color='#c9a24a', roof=1.27, tail_shape='kamm', details=[spine(), front_lights('slim'), grille('low'), rear_lights('arrow'),
        exhausts('center2'), hood_vents(x=0.22), fender_vents(), wing('swan', y0=0.02, chord=0.30, z=1.30)] + RACE),
    car(16, 'rook_cup', 'Calder', 'Rook Cup', 'The one-make racer: white, blue-striped and built to trade paint.', 'gt', (4.52, 2.00, 2.62, 0.88, 1.28),
        '#f4f4f4', sec='#1e88e5', rim='10', spokes=10, rim_color='#1b1c1f', roof=1.27, lower='sec', tail_shape='drop', details=[hump(), front_lights('slim'),
        grille('low'), rear_lights('round'), exhausts('dual'), hood_vents(x=0.22), fender_vents(), wing('wing', y0=0.0, chord=0.32, z=1.32),
        roundel()] + RACE),
    car(17, 'rook_gt', 'Calder', 'Rook GT', 'Endurance-spec Rook in signal orange, lights taped and ready for the night stint.', 'gt', (4.52, 2.00, 2.62, 0.88, 1.28),
        '#ff6a13', sec='#16181c', rim='10', spokes=10, rim_color='#1b1c1f', roof=1.27, tail_shape='taper', details=[buttresses(), front_lights('slim'), grille('low'),
        rear_lights('ring'), exhausts('dual'), fender_vents(), wing('wing', y0=0.0, chord=0.32, z=1.30), side_band('sec', h=0.05),
        roundel('c_16181c')] + RACE),
    car(18, 'meteora', 'Vireo', 'Meteora', 'A cream-and-green endurance classic from the days of no speed limits on the long straight.', 'lmp', (4.40, 2.00, 2.40, 0.96, 0.98),
        '#f0e2b6', sec='#1f6b45', rim='10', spokes=10, roof=0.97, zscale=0.92, fb=-0.22, tail_shape='taper', details=[front_lights('round'), grille('lmp'),
        rear_lights('round2'), exhausts('dual'), side_band('sec', h=0.12), roundel()]),
    car(19, 'corvara', 'Rovenza', 'Corvara', 'A raw twin-turbo wedge: no driver aids, a fixed wing and a louvred rear screen.', 'mid', (4.38, 1.98, 2.46, 0.98, 1.12),
        '#2a6cc7', rim='5', roof=1.11, rear_mat='black', tail_shape='kamm', details=[splitter(), diffuser(), side_intake(), front_lights('pop'),
        grille('low', w=0.75), rear_lights('round'), exhausts('hex', z=0.36), naca(), wing('wing', y0=0.0, chord=0.28, z=1.08, posts=0.6)]),
    car(20, 'onda', 'Hoshida', 'Onda', 'Burnt-orange hybrid V6 with a black side flash and a light step.', 'mid', (4.56, 1.96, 2.62, 1.02),
        '#e86a2e', sec='#16181c', rim='10', spokes=10, tail_shape='taper', details=[buttresses(), splitter(), diffuser(), side_intake('sec'), front_lights('tear'),
        grille('mouth3'), rear_lights('vbar'), exhausts('center2', z=0.45), side_band('sec', h=0.05)]),
    car(21, 'onda_r', 'Hoshida', 'Onda R', 'The Onda race car: wider, lower, splitter, swan wing and a number on the door.', 'mid', (4.58, 2.04, 2.62, 1.02, 1.17),
        '#e86a2e', sec='#16181c', rim='10', spokes=10, rim_color='#1b1c1f', roof=1.16, lower='sec', tail_shape='kamm', details=[spine(), splitter(), diffuser(),
        side_intake('sec'), front_lights('tear'), grille('mouth3'), rear_lights('pill'), exhausts('center1', z=0.40), fender_vents(),
        wing('swan', y0=0.0, chord=0.32), roundel()] + RACE),
    car(22, 'luce', 'Rovenza', 'Luce', 'A pearl-white V12 targa with a louvred tail, built in a run of a few hundred.', 'mid', (4.70, 2.02, 2.66, 1.04),
        '#e8e1d4', sec='#16181c', rim='5', rim_color='#c9ccd1', roof_mat='black', rear_mat='black', trim='chrome', tail_shape='taper', details=[splitter(), diffuser(),
        side_intake('sec'), front_lights('slim'), grille('low', w=0.7), rear_lights('bar'), exhausts('center2', z=0.40), louvers(6)]),
    car(23, 'nadir', 'Vireo', 'Nadir', 'A hybrid endurance prototype in black with a neon slash down the side.', 'lmp', (5.00, 1.98, 3.00, 0.98, 1.06),
        '#1b1d22', sec='#c7ff2e', rim='10', spokes=10, rim_color='#1b1c1f', caliper='#c7ff2e', roof=1.04, details=[front_lights('blade'),
        grille('lmp'), rear_lights('split'), exhausts('center1', z=0.5), fin(), wing('wing', y0=-0.02, chord=0.30, z=1.02),
        side_band('sec', h=0.05), roundel('sec')] + RACE),
    car(24, 'gioia', 'Rovenza', 'Gioia', 'A curvy sage-green coupe from the golden age, round lamps and chrome wire wheels.', 'beetle', (4.26, 1.74, 2.40, 0.86, 1.24),
        '#6f8f6a', rim='10', spokes=16, rim_color='#d7dbe0', roof=1.23, trim='chrome', tail_shape='taper', details=[front_lights('round', xk=1.05), grille('wide', w=0.35,
        frame_mat='chrome'), rear_lights('round'), exhausts('dual')]),
    car(25, 'zentra_r', 'Kova', 'Zentra Roadster', 'The Zentra with a fabric roof and the sky for a headliner.', 'rear', (4.42, 1.86, 2.44, 0.96),
        '#2bb3a3', rim='5', roof_mat='matte', tail_shape='taper', details=[front_lights('round', size=0.085), grille('low'), rear_lights('ring'),
        exhausts('dual'), wing('duck'), side_intake(k=0.6), diffuser()]),
    car(26, 'zentra_cup', 'Kova', 'Zentra Cup', 'One-make racer: roof scoop, big wing and a yellow-and-black livery.', 'rear', (4.44, 1.96, 2.44, 0.96, 1.28),
        '#ffd23f', sec='#16181c', rim='10', spokes=10, rim_color='#1b1c1f', roof=1.27, lower='sec', tail_shape='kamm', details=[spine(), front_lights('round', size=0.085),
        grille('low'), rear_lights('strip3'), exhausts('center1', z=0.40), roof_scoop(), fender_vents(), wing('wing', y0=0.0, chord=0.32, z=1.31),
        roundel()] + RACE),
    car(27, 'brask', 'Kova', 'Brask', 'A boxy rally legend: short wheelbase, big arches and a five-cylinder warble.', 'hatch', (4.18, 1.84, 2.30, 0.92, 1.38),
        '#f5f5f0', sec='#c8102e', rim='6', spokes=6, rim_color='#eeeeee', roof=1.36, cab=(0.50, 0.90, 3.26 - 1.05, 3.26 - 0.55),
        tail_shape='kamm', details=[front_lights('round2'), grille('wide', w=0.55), rear_lights('wide'), exhausts('dual'), wing('wing', y0=0.02, chord=0.24, z=1.14),
        side_band('sec', h=0.05), side_band('c_1d3f8a', h=0.03, z0=0.42), roundel()]),
    car(28, 'mosk', 'Kova', 'Mosk', 'A sky-blue city hatch with a turbo, a roof spoiler and a lot of nerve.', 'hatch', (3.92, 1.76, 2.46, 0.78, 1.40),
        '#3bb0e0', sec='#16181c', rim='10', spokes=10, rim_color='#c0c4ca', roof=1.38, dna=False, cab=(0.16, 0.70, 3.14 - 0.72, 3.14 - 0.06), dome=0.6, xr=0.56, nose=0.14, tail=0.10, waist=0.03, hh=0.02, details=[front_lights('slim'), grille('wide', w=0.40),
        rear_lights('dots'), exhausts('dual'), wing('roof', y0=0.16, chord=0.22), side_band('sec', h=0.03)]),
    car(29, 'tarn', 'Thornbury', 'Tarn', 'A British-racing-green rally car with lamp pods and a gravel-spitting attitude.', 'hatch', (4.00, 1.86, 2.48, 0.80, 1.42),
        '#2f4f2f', sec='#e8c547', rim='6', spokes=6, rim_color='#e8c547', roof=1.39, dna=False, cab=(0.22, 0.50, 3.20 - 0.62, 3.20 - 0.05), dome=1.8, xr=0.68, nose=0.05, tail=0.04, waist=0.01, hh=0.05, zsh=(0.95, 0.97, 0.93, 0.92, 0.80), zd=(1.0, 1.02, 1.0, 0.98, 0.84), details=[front_lights('round2'), grille('wide', w=0.5),
        rear_lights('quad'), exhausts('dual'), hood_vents(x=0.2), wing('roof', y0=0.16, chord=0.30), side_band('sec', h=0.05), roundel()] + RACE),
    car(30, 'skerry', 'Lindqvist', 'Skerry', 'A silver-and-yellow rally hatch built for frozen lakes and forest stages.', 'hatch', (4.08, 1.86, 2.54, 0.80, 1.42),
        '#e0e4ea', sec='#f5c518', rim='6', spokes=6, rim_color='#16181c', roof=1.39, dna=False, cab=(0.10, 1.00, 3.28 - 0.88, 3.28 - 0.02), dome=0.75, xr=0.55, nose=0.17, tail=0.09, waist=0.04, hh=0.035, zsh=(0.86, 0.93, 0.88, 0.82, 0.58), zd=(0.92, 0.98, 0.95, 0.85, 0.62), details=[front_lights('slim'), grille('hex'),
        rear_lights('hook'), exhausts('center1', z=0.40), hood_vents(x=0.2), wing('roof', y0=0.16, chord=0.30), side_band('sec', h=0.08), roundel()] + RACE),
    car(31, 'pebble', 'Boone', 'Pebble', 'A round little sunshine-yellow coupe turned track toy, with a wing on its back.', 'beetle', (4.30, 1.92, 2.50, 0.88, 1.30),
        '#ffcf3f', sec='#2a2c31', rim='5', roof=1.28, tail_shape='kamm', details=[front_lights('round', xk=1.05), rear_lights('halo'), exhausts('dual'),
        wing('wing', y0=0.02, chord=0.26), side_band('sec', h=0.05), roundel()] + RACE),
    car(32, 'vexis', 'Arvane', 'Vexis', 'Track-only and barely street-shaped: a pink-red missile with a roof scoop and a fin.', 'lmp', (4.80, 2.00, 2.76, 1.00, 1.04),
        '#ff3d6e', sec='#16181c', rim='10', spokes=10, rim_color='#1b1c1f', roof=1.02, tail_shape='drop', details=[front_lights('blade'), grille('lmp'),
        rear_lights('x'), exhausts('center2', z=0.48), roof_scoop(), fin(), wing('lip'), side_band('sec', h=0.04)] + RACE),
    car(33, 'halcyon', 'Vireo', 'Halcyon', 'A deep-blue prototype with vertical light blades and a full-width wing.', 'lmp', (4.96, 1.98, 2.98, 0.98, 1.06),
        '#0d4f8b', sec='#e8e1d4', rim='10', spokes=10, rim_color='#e8e1d4', roof=1.04, tail_shape='kamm', details=[front_lights('blade'), grille('lmp'),
        rear_lights('vbar'), exhausts('center1', z=0.5), fin(), wing('wing', y0=-0.02, chord=0.30, z=1.02), side_band('sec', h=0.04),
        roundel('sec')] + RACE),
    car(34, 'zephra', 'Lindqvist', 'Zephra', 'Silver, needle-nosed and fighter-jet fast, with a fin to keep it pointed straight.', 'mid', (4.90, 2.08, 2.84, 1.10, 1.20),
        '#c9ccd1', sec='#16181c', rim='5', roof=1.19, lower='sec', tail_shape='drop', rear_mat='paint', details=[splitter(), diffuser(), side_intake('sec'), front_lights('slim'),
        grille('mouth3'), rear_lights('stack'), exhausts('hex', z=0.34), fin(), wing('lip')]),
    car(35, 'brute', 'Boone', 'Brute', 'A dark-gold muscle car with a shaker scoop through the hood and no apologies.', 'notch', (5.10, 2.00, 2.94, 1.00),
        '#8a6d1f', sec='#16181c', rim='5', rim_color='#c9ccd1', tail_shape='drop', details=[grille('wide', w=0.88, frame_mat='chrome'), front_lights('pop'),
        blower(), rear_lights('bar', panel=True), exhausts('quad'), side_band('sec', h=0.04), diffuser(1)]),
    car(36, 'marisol', 'Arvane', 'Marisol', 'An open GT racer in white with a blue stripe, built to win the long race.', 'gt', (4.86, 2.00, 2.70, 0.94, 1.14),
        '#f2efe9', sec='#1d4f9a', rim='10', spokes=10, rim_color='#c9ccd1', roof=1.12, zscale=0.92, roof_mat='black', tail_shape='taper', details=[
        front_lights('round2'), grille('wide', w=0.3), rear_lights('c'), exhausts('dual'), side_intake(), side_band('sec', h=0.05),
        wing('wing', y0=0.03, chord=0.28)] + RACE),
    car(37, 'tsubame', 'Hoshida', 'Tsubame', 'A green-and-white prototype with a wide mouth and a long tail.', 'lmp', (5.00, 1.98, 3.00, 0.98, 1.06),
        '#1aa37a', sec='#f2f3f5', rim='10', spokes=10, rim_color='#1b1c1f', roof=1.04, tail_shape='taper', details=[front_lights('wide'), grille('lmp'),
        rear_lights('blade'), exhausts('center2', z=0.42), wing('wing', y0=-0.02, chord=0.30, z=1.0), side_band('sec', h=0.06),
        roundel('c_16181c')] + RACE),
    car(38, 'stormo', 'Vireo', 'Stormo', 'A periwinkle-and-yellow group-C wedge with covered lamps and a rotary scream.', 'lmp', (4.80, 2.00, 2.68, 1.02, 1.06),
        '#5b6cff', sec='#ffd23f', rim='10', spokes=10, rim_color='#c9ccd1', roof=1.03, fb=-0.2, zscale=0.95, details=[front_lights('pop'),
        grille('lmp'), rear_lights('ring'), exhausts('dual'), wing('wing', y0=-0.05, chord=0.32, z=0.98), side_band('sec', h=0.14),
        roundel()] + RACE),
]
ROSTER = {c['d']['id']: c for c in CARS}


def spec(cid):
    c = ROSTER[cid]
    o = dict(c['o'])
    o.setdefault('plates', not any(fn in RACE for fn in o.get('details', ())))   # race cars carry no plates
    S = make(c['d'], c['kind'], rim=c['rim'], **o)
    S['brand'], S['name'] = c['brand'], c['name']
    return S

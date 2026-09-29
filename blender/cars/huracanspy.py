# Corvani Tempesta Spyder — 4.520 × 1.933 × 1.180 m, wheelbase 2.620 m
# The Tempesta body with a black fabric roof and two buttresses behind the seats.
import copy
P = inherit('huracan')
L = P['L']


def _side(ctx):
    P['_side'](ctx)
    # roof buttresses behind the seats
    for sd in (1, -1):
        prism(ctx['mb'], [(0.95, 0.90), (1.62, 0.93), (1.52, 1.05), (1.10, 1.00)], 'x', sd * 0.44 - 0.03, sd * 0.44 + 0.03, 'paint', smooth=True)


SPEC = copy.deepcopy(P['SPEC'])
SPEC.update(id='huracanspy', color='#1d8fd1', sec='#141518', details=[P['_rear'], _side, P['_front']])
SPEC['wheels'].update(style='Y', caliper='#e8c200', rim_color='#2b2d31')
SPEC['cabin']['zones'] = [(2.62, 9, 'glass', None), (1.62, 2.62, 'matte', None), (0, 1.62, 'louver', None)]
SPEC['cabin']['ys'] = (2.62, 1.62)

"""Three breath-played engines after Jaffedrone (https://github.com/mercurious/jaffedrone and its dev fork,
MIT, mercurious and sydilaxe): its struck/bowed bodies, its bowed strings and its wind voices, made to be played
by breath. No plucks or strikes: breath is the bow, the rub or the mouth, and blowing harder adds harmonics.

  Metal  - a resonant body from Jaffedrone's measured mode tables (gamelan gender and bonang, gong, singing bowl,
           handpan, steelpan, glass, the golden-ratio 'alien'), sung by breath: soft breath sounds the low modes,
           harder breath brings the upper ones in; the fundamental has a beating twin (ombak); breath noise rubs it.
  String - a bowed string: a waveguide kept ringing by a noise bow (Jaffedrone's), with its jawari bridge (past a
           threshold the swing is squashed: a loud note buzzes) and stiffness (inharmonic stretch). Breath is the
           bow: its pressure, and the brightness of the string.
  Wind   - a bore (a waveguide) driven at the mouthpiece (Jaffedrone's wind voices, after Cook and Smith): a single
           reed (clarinet: a half-length bore, odd harmonics), a double reed (oboe-like, all harmonics) or a free reed
           (harmonium). Breath is the mouth pressure: soft is near a sine, harder makes the reed beat - brighter,
           buzzier.

MPE: per-note pitch bend comes in the pitch, per-note breath in the level; per-note timbre (CC 74) brightens each."""
import math
from pdgen import Canvas
from gen_engines import frame, mul, add, chain, ex, softclip, finish, r, Ctl
from gen_hybrid import switched, modes
from sec_core import to, msg_to

SR = 44100


def ctl_float(c, recv, expr, x, y):
    return chain(c, c.obj(f"r {recv}", x, y), [f"expr {expr}"], x, y + 25)


# ================================================================== Metal
# mode ratios and levels (Jaffedrone's PercModel table; 6 modes each, padded with silent ones), the twin's split (Hz)
BODIES = [
    ("Gender", (1, 2.0, 2.756, 3.0, 5.404, 8.933), (1, .25, .55, .18, .3, .15), 6.0),
    ("Bonang", (1, 1.52, 2.0, 3.46, 3.92, 5.2), (1, .45, .3, .35, .25, .12), 4.0),
    ("Gong", (1, 1.47, 2.0, 2.5, 3.0, 3.6), (1, .35, .45, .25, .3, .15), 3.0),
    ("Bowl", (1, 2.9, 5.7, 9.1, 13.0, 1), (1, .5, .3, .18, .1, 0), 0.8),
    ("Handpan", (1, 2, 3, 4.9, 6.3, 1), (1, .6, .4, .08, .05, 0), 0.5),
    ("Steelpan", (1, 2, 3, 4, 5, 1), (1, .75, .45, .25, .12, 0), 0.3),
    ("Glass", (1, 2.32, 4.25, 6.63, 9.6, 1), (1, .35, .15, .08, .04, 0), 0.4),
    ("Alien", tuple(1.6180340 ** k for k in range(6)), (1, .7, .55, .4, .3, .2), 0.35),
]
NM = 6


def metal(path):
    e, pl, env, tb = frame("Metal - a resonant body after Jaffedrone's (gender, bonang, gong, bowl, handpan, steelpan, "
                           "glass, alien: knob 1), sung by breath. Soft breath sounds the low modes; harder breath brings "
                           "the upper ones in (Bloom: how far). The fundamental beats against its twin (Shimmer). "
                           "Breath noise rubs it; Tone brightens it. Knobs: Body, Bloom, Shimmer, Tone")
    p2, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in enumerate(("$1-p2~", "$1-p4~", "eng-bamt~")))
    eb = mul(e, env, bamt, 650, 80)
    c = Ctl(e, 300, 100)
    cs = c.s
    fi = c.freq(pl)
    f = c.f(fi)
    # the body: knob 1 picks a row; its ratios, levels (each / sqrt(ratio): higher modes quieter, levelled to the same
    # loudness) and twin split arrive as messages
    sel = chain(cs, cs.obj("r $1-p1", 900, 30), [f"expr int(min(max($f1, 0), 0.999) * {len(BODIES)})",
                                                  "sel " + " ".join(str(k) for k in range(len(BODIES)))], 900, 55)
    unp = cs.obj("unpack " + " ".join(["0"] * (2 * NM + 1)), 900, 200)
    for k, (nm, rr, gg, split) in enumerate(BODIES):
        g = [gk / math.sqrt(rk) for rk, gk in zip(rr, gg)]
        n = 1 / math.sqrt(sum(x * x for x in g))
        vals = list(rr) + [x * n for x in g] + [split]
        cs.c(msg_to(cs, sel, " ".join(f"{v:.5g}" for v in vals), 900 + k * 60, 120, outlet=k), 0, unp, 0)
    # breath (and MPE timbre) open the body: mode k comes in as o rises; Bloom spreads how far the opening reaches
    o = c.i(ex(e, "min(1, max(0, $v1 * 1.3 + ($v2 - 0.5) * 0.8))", [eb, tb], 650, 120))
    parts = None
    for k in range(NM):
        fk = cs.obj("*~ 1", 20 + k * 100, 300)
        cs.c(fi, 0, fk, 0)
        cs.c(unp, k, fk, 1)
        # above 16 kHz a mode is left out (no aliasing): gain x clip((18000 - fk) / 2000, 0, 1)
        nyq = chain(cs, fk, ["*~ -0.0005", "+~ 9", "clip~ 0 1"], 20 + k * 100, 330)
        gk = cs.obj("*~ 0", 20 + k * 100, 420)
        cs.c(nyq, 0, gk, 0)
        cs.c(unp, NM + k, gk, 1)
        # opening: mode k needs breath above k / NM x (1.2 - Bloom); full a little above that
        if k:
            th = ctl_float(cs, "$1-p2", f"{k / NM:.3f} * (1.2 - $f1)", 20 + k * 100, 360)
            op = cs.obj("-~ 0", 20 + k * 100, 390)
            cs.c(o, 0, op, 0)
            cs.c(th, 0, op, 1)
            gk2 = mul(cs, gk, chain(cs, op, ["*~ 3", "clip~ 0 1"], 20 + k * 100, 445), 20 + k * 100, 500)
        else:
            gk2 = gk
        osc = chain(e, c.f(fk), ["osc~"], 20 + k * 100, 450)
        m = mul(e, osc, c.o(gk2), 20 + k * 100, 480)
        parts = m if parts is None else add(e, parts, m, 20 + k * 100, 510)
    # the fundamental's twin, Shimmer x split Hz above it: the two beat (ombak)
    spm = cs.obj("*~ 0", 760, 250)                                 # Shimmer x the body's split (Hz)
    cs.c(c.i(r(e, "$1-p3~", 900, 30)), 0, spm, 0)
    cs.c(unp, 2 * NM, spm, 1)
    tw = add(cs, fi, spm, 700, 300)
    twin = mul(e, chain(e, c.f(tw), ["osc~"], 700, 450), chain(e, e.obj("r~ $1-p3~", 800, 400), ["*~ 0.8"], 800, 425),
               700, 480)
    body = add(e, parts, twin, 20, 540)
    # Tone: a gentle tilt toward the upper modes (and their level up a little); breath noise rubbing the fundamental
    rub = e.obj("vcf~ 30", 400, 560)
    e.c(e.obj("noise~", 400, 540), 0, rub, 0)
    e.c(f, 0, rub, 1)
    rubg = ex(e, "$v1 * $v1 * (0.5 + $v2) * 4", [eb, p4], 500, 560)
    mix = add(e, mul(e, body, ex(e, "0.8 + $v1 * 0.4", [p4], 150, 560), 20, 580), mul(e, rub, rubg, 400, 590), 20, 610)
    sub = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 600, 600), r(e, "eng-body~", 700, 600), 600, 630)
    finish(e, add(e, mix, chain(e, sub, ["*~ 0.5"], 600, 650), 20, 670), env, 0.55, 20, 700, path)


# ================================================================== String
def string(path):
    e, pl, env, tb = frame("String - a bowed string after Jaffedrone's: a waveguide kept ringing by a noise bow, with "
                           "a jawari bridge (Buzz: a loud note buzzes) and stiffness (Stiff: the partials stretch). "
                           "Breath is the bow: harder is louder and brighter, and buzzes more. "
                           "Knobs: Bright, Buzz, Stiff, Sustain")
    p1, bamt = r(e, "$1-p1~", 650, 30), r(e, "eng-bamt~", 740, 30)
    eb = mul(e, env, bamt, 650, 80)
    c = Ctl(e, 300, 100)
    cs = c.s
    fi = chain(cs, add(cs, c.i(pl), c.i(e.obj("r~ eng-vib", 100, 80)), 20, 600), ["mtof~", "clip~ 30 2700"], 20, 625)
    f = c.f(fi)
    # the loop's low-pass: Bright and breath (and MPE timbre) open it (Jaffedrone: 0.08 + 0.9 bright^1.5)
    bri = c.i(ex(e, "min(1, max(0, $v1 * 0.45 + $v2 * 0.9 - 0.1 + ($v3 - 0.5) * 0.4))", [p1, eb, tb], 650, 120))
    lpa = c.ex("0.08 + 0.9 * $v1 * sqrt($v1)", [bri])
    stf = ctl_float(cs, "$1-p3", "$f1 * 0.5", 500, 150)                  # allpass coefficient (Jaffedrone: x 0.7)
    stv = chain(cs, cs.obj("sig~ 0", 500, 200), [], 500, 200)
    cs.c(stf, 0, stv, 0)
    # the loop delay: the period minus the low-pass's and the allpass's own delay (samples -> ms)
    dl = c.o(c.ex(f"max(0.37, (44100 / $v1 - min(6, (1 - $v2) / $v2) - 2 * (1 - $v3) / (1 + $v3)) * {1000 / SR:.6f})",
                  [fi, lpa, stv]))
    lpo = c.o(lpa)
    # the bow: band-passed noise, its colour with Bright, its force with breath (squared: soft is gentle)
    bow = chain(e, mul(e, e.obj("noise~", 400, 300), ex(e, "$v1 * (0.3 + $v1) * 0.06", [eb], 500, 300), 400, 330),
                ["lop~ 700", "lop~ 1500"], 400, 360)                      # (dark: the string makes the colour)
    s = Canvas("string", w=900, h=500)
    s.comment("the string in 16-sample blocks: delay -> stiffness allpass -> low-pass -> sustain -> jawari -> + bow", 20, 5)
    s.obj("block~ 16", 750, 5)
    i_dl, i_a, i_bow = (s.obj("inlet~", 20 + k * 150, 30) for k in range(3))
    rd = s.obj("vd~ $0-str", 20, 70)
    s.c(i_dl, 0, rd, 0)
    ap = rd
    sa = s.obj("r $1-p3", 500, 30)
    sx = chain(s, sa, ["expr $f1 * 0.5"], 500, 55)
    rz = s.obj("rzero_rev~ 0", 20, 100)
    s.c(ap, 0, rz, 0)
    s.c(sx, 0, rz, 1)
    rp = s.obj("rpole~ 0", 20, 125)
    s.c(rz, 0, rp, 0)
    s.c(sx, 0, rp, 1)
    lp = s.obj("rpole~", 20, 180)
    s.c(mul(s, rp, i_a, 20, 155), 0, lp, 0)
    s.c(chain(s, i_a, ["*~ -1", "+~ 1"], 150, 155), 0, lp, 1)
    g = s.obj("*~ 0.99", 20, 210)
    s.c(lp, 0, g, 0)
    s.c(chain(s, s.obj("r $1-p4", 600, 30), ["expr 0.97 + 0.0298 * pow($f1, 0.35)"], 600, 55), 0, g, 1)
    # jawari: past a threshold th the swing is squashed, x -> th + (|x| - th) / (1 + k (|x| - th)) (signed)
    th = chain(s, s.obj("r $1-p2", 700, 100), ["expr 0.4 * (1 - $f1) * (1 - $f1) + 0.01"], 700, 125)
    kk = chain(s, s.obj("r $1-p2", 800, 100), ["expr 40 * $f1"], 800, 125)
    ax = chain(s, g, ["abs~"], 200, 240)
    ov = s.obj("-~ 0.4", 200, 265)
    s.c(ax, 0, ov, 0)
    s.c(th, 0, ov, 1)
    ov = chain(s, ov, ["max~ 0"], 200, 290)
    kd = s.obj("*~ 0", 300, 315)
    s.c(ov, 0, kd, 0)
    s.c(kk, 0, kd, 1)
    sq = s.obj("/~", 200, 365)
    s.c(ov, 0, sq, 0)
    s.c(chain(s, kd, ["+~ 1"], 300, 340), 0, sq, 1)
    lost = s.obj("-~", 200, 390)                                  # what the squash takes off |x|
    s.c(ov, 0, lost, 0)
    s.c(sq, 0, lost, 1)
    keep = s.obj("/~", 200, 440)                                  # 1 - lost / |x|
    s.c(lost, 0, keep, 0)
    s.c(chain(s, ax, ["max~ 1e-06"], 300, 415), 0, keep, 1)
    jw = mul(s, g, chain(s, keep, ["*~ -1", "+~ 1"], 200, 465), 20, 490)
    sm = add(s, jw, i_bow, 20, 515)
    s.c(chain(s, sm, ["clip~ -1.5 1.5"], 20, 540), 0, s.obj("delwrite~ $0-str 120", 20, 565), 0)
    s.c(rd, 0, s.obj("outlet~", 20, 600), 0)
    st = e.sub(s, 20, 450)
    for k, src in enumerate((dl, lpo, bow)):
        e.c(src, 0, st, k)
    out = chain(e, st, ["hip~ 30"], 20, 480)
    sat = softclip(e, chain(e, out, ["*~ 1.6"], 20, 505), 20, 530)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 600), mul(e, r(e, "eng-body~", 500, 600), env, 500, 625), 400, 650)
    mix = add(e, sat, chain(e, body, ["*~ 0.4"], 400, 675), 20, 700)
    e.c(chain(e, mix, ["*~ 3.3"], 20, 725), 0, e.obj("outlet~", 20, 790), 0)
    e.save(path)


# ================================================================== Wind
def bore(s, ins, kind):
    """one exciter on the bore, in 16-sample blocks. ins: delay (ms), low-pass coefficient, mouth pressure"""
    w = Canvas("bore", w=900, h=600)
    w.comment(f"{kind}: the bore in 16-sample blocks", 20, 5)
    w.obj("block~ 16", 750, 5)
    dl, a, p = (w.obj("inlet~", 20 + k * 150, 30) for k in range(3))
    y = w.obj(f"vd~ $0-bore-{kind}", 20, 70)
    w.c(dl, 0, y, 0)
    lp = w.obj("rpole~", 20, 120)                                 # the open end and the walls: a one-pole
    w.c(mul(w, y, a, 20, 95), 0, lp, 0)
    w.c(chain(w, a, ["*~ -1", "+~ 1"], 150, 95), 0, lp, 1)
    b = chain(w, lp, ["*~ 0.995"], 20, 145)
    if kind in ("reed", "double"):
        # the reed opens and closes with the pressure across it: pd = (-+0.95) b - p, t = clip(roff + rslope pd)
        sign, roff, rsl = (-0.95, 0.7, -0.3) if kind == "reed" else (0.95, 0.6, -0.6)
        pd = w.obj("-~", 20, 200)
        w.c(chain(w, b, [f"*~ {sign}"], 20, 175), 0, pd, 0)
        w.c(p, 0, pd, 1)
        t = chain(w, pd, [f"*~ {rsl}", f"+~ {roff}", "clip~ -1 1"], 200, 200)
        out = add(w, p, mul(w, pd, t, 20, 280), 20, 305)
        if kind == "double":                                       # double-dc: no DC in the loop
            out = chain(w, out, ["rzero~ 1", "rpole~ 0.995"], 20, 320)
        o = y
    else:
        # free reed: it swings at its own pitch (a phasor at the note); puffs of air sound the pipe
        fr = w.obj("inlet~", 600, 30)                             # (4th inlet: the note's frequency)
        ph = chain(w, fr, ["phasor~", "cos~"], 600, 60)
        # the opening: harder breath narrows the puffs (more harmonics), as a harmonium reed brightens when pushed
        r_ = chain(w, add(w, ph, chain(w, p, ["*~ -0.7", "+~ 0.3"], 700, 85), 600, 110), ["max~ 0"], 600, 135)
        flow = add(w, mul(w, mul(w, r_, r_, 600, 160), p, 600, 185), chain(w, p, ["*~ -0.4"], 700, 185), 600, 210)
        out = add(w, chain(w, flow, ["*~ 0.3"], 600, 235), chain(w, b, ["*~ 0.6"], 20, 235), 20, 260)
        out = chain(w, out, ["rzero~ 1", "rpole~ 0.995"], 20, 285)   # (no DC in the loop)
        o = add(w, y, chain(w, flow, ["*~ 0.6"], 700, 260), 600, 285)
    w.c(chain(w, out, ["clip~ -1.2 1.2"], 20, 340), 0, w.obj(f"delwrite~ $0-bore-{kind} 100", 20, 365), 0)
    w.c(o, 0, w.obj("outlet~", 20, 420), 0)
    box = s.sub(w, 20, 100)
    for k, src in enumerate(ins):
        s.c(src, 0, box, k)
    return box


WIND_LOOP = {"reed": 0.5, "double": 1.0, "free": 1.0}           # bore length in periods
WIND_OUT = {"reed": 1.0, "double": 1.0, "free": 1.5}


def wind(path):
    e, pl, env, tb = frame("Wind - a bore driven by breath after Jaffedrone's wind voices (Cook / Smith waveguides): "
                           "knob 1 picks a single reed (clarinet, odd harmonics), a double reed (all harmonics) or a free "
                           "reed (harmonium). Breath is the mouth pressure: soft is near a sine, harder makes the reed beat. "
                           "Knobs: Reed, Bright, Air (breath noise), Vibrato")
    p2, p3, bamt = (r(e, n, 650 + i * 90, 30) for i, n in enumerate(("$1-p2~", "$1-p3~", "eng-bamt~")))
    eb = mul(e, env, bamt, 650, 80)
    c = Ctl(e, 300, 100)
    cs = c.s
    # vibrato: a breath-player's, 4.6 Hz, up to 0.4 semitone (knob 4), on the pitch
    vib = mul(cs, cs.obj("osc~ 4.6", 500, 60), c.i(r(e, "$1-p4~", 900, 30)), 500, 90)
    fi = chain(cs, add(cs, add(cs, c.i(pl), c.i(e.obj("r~ eng-vib", 100, 80)), 20, 600),
                       chain(cs, vib, ["*~ 0.4"], 500, 120), 20, 625), ["mtof~", "clip~ 30 1300"], 20, 650)
    f = c.f(fi)
    # the walls' low-pass: Bright, breath and MPE timbre open it (Jaffedrone: 0.25 + 0.7 bright^1.2). A reed model
    # speaks at one strength above its threshold; breath opening the bore is what makes harder breath brighter
    lpa = c.ex("min(0.95, 0.15 + 0.8 * min(1, max(0, $v1 * 0.5 + $v3 + ($v2 - 0.5) * 0.5)))", [c.i(p2), c.i(tb), c.i(eb)])
    # mouth pressure: pmax (1 - exp(-2.5 p)). As in Jaffedrone, a player's pressure sits in the reed's speaking range
    # (0.3 .. 1.2 here) whenever there is breath; the breath gate (env x 6, up to 1) starts and stops it
    gate = chain(e, env, ["*~ 6", "clip~ 0 1"], 300, 80)
    pr = c.o(c.ex("$v2 * (1 - exp(-2.5 * (0.3 + 0.9 * $v1)))", [c.i(eb), c.i(gate)]))
    pn = mul(e, pr, add(e, mul(e, chain(e, e.obj("noise~", 500, 300), ["lop~ 8000"], 500, 325),
                                ex(e, "0.015 + $v1 * 0.2", [p3], 600, 325), 500, 350), e.obj("sig~ 1", 650, 350),
                        500, 375), 400, 400)
    builders, names = [], ["reed", "double", "free"]
    for kind in names:
        def b(s, ins, kind=kind):
            fr, a, p = ins
            cc = Ctl(s, 600, 30)
            fii, ai = cc.i(fr), cc.i(a)
            dl = cc.o(cc.ex(f"max(0.37, ({WIND_LOOP[kind] * SR} / $v1 - min(8, (1 - $v2) / $v2)) * {1000 / SR:.6f})",
                            [fii, ai]))
            if kind == "double":                                     # a stiffer reed: less pressure, or it shrieks
                p = chain(s, p, ["*~ 0.75"], 300, 60)
            ins2 = [dl, a, p] + ([fr] if kind == "free" else [])
            box = bore(s, ins2, kind)
            return chain(s, box, [f"*~ {WIND_OUT[kind]}"], 20, 200)
        builders.append(b)
    sound = modes(e, "$1-p1", names, builders, [f, c.o(lpa), pn], 20, 450)
    # and the player's dynamics: the level follows breath (the model alone would be on or off)
    dyn = ex(e, "0.15 + 0.85 * sqrt(min(1, $v1 * 1.6))", [eb], 300, 480)
    out = softclip(e, mul(e, chain(e, sound, ["hip~ 40", "*~ 1.2"], 20, 500), dyn, 20, 525), 20, 550)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 600), mul(e, r(e, "eng-body~", 500, 600), env, 500, 625), 400, 650)
    mix = add(e, out, chain(e, body, ["*~ 0.4"], 400, 675), 20, 700)
    e.c(chain(e, mix, ["*~ 0.9"], 20, 725), 0, e.obj("outlet~", 20, 790), 0)
    e.save(path)


ENGINES = {
    "metal": (metal, "Body Bloom Shimmer Tone", "0.44 0.5 0.4 0.5"),
    "string": (string, "Bright Buzz Stiff Sustain", "0.5 0.25 0.1 0.6"),
    "wind": (wind, "Reed Bright Air Vibrato", "0.15 0.5 0.3 0.2"),
}

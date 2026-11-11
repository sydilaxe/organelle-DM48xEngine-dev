"""Two ambient engines after FRASIL by Styves Goupil (https://github.com/styvesgoupil/frasil, MPL-2.0), a drone
firmware for the M-VAVE FM-1. Reimplemented in Pd from its design (no code copied):

  Frasil - one drone voice in FRASIL's three layers: CHOEUR (three detuned saws through a soft low-pass), PARTIELS
           (additive partials whose levels wander on their own) and SOUFFLE (breath noise ringing resonators tuned to
           the note). Every voice drifts by itself (slow random walks on pitch, levels and brightness), and a slow
           tide moves the brightness. Breath is FRASIL's pressure: it swells the voice and opens it.
  Glint  - FRASIL's GLINT: a two-operator FM bell, bright at the strike and mellower as it rings, with a vibrato
           that fades in after the strike. Breath sets its level and brightness; Ring holds it like a lead.

Slow signals run at 1/8 of the sample rate (Ctl, see gen_engines.py): frequencies leave stepped, anything that scales
audio leaves interpolated or stays at full rate. A layer that is turned all the way down is switched off."""
import math
from pdgen import Canvas
from gen_engines import frame, mul, add, chain, ex, softclip, finish, r, Ctl
from gen_hybrid import switched
from sec_core import to, msg_to

# ================================================================== Frasil
NP = 5                                                    # partials
SOUFFLE_RATIOS = (1, 2, 3)                                # harmonic resonators (FRASIL's first COLOR set)
# each voice's drifts: slow sines at rates that never line up (FRASIL uses random walks; a sine at 1/8 of the rate
# is one object, and an object costs as much in a Ctl block as at full rate - only its arithmetic is cheaper)
DRIFT_HZ = (0.071, 0.113, 0.089, 0.137, 0.059, 0.167, 0.101, 0.079)


def onepole(cs, f, x, lo, span, xx, y):
    """a one-pole's coefficient for a cutoff of f (lo + span x^2), x clipped to 0..1: a = w / (1 + w), w = 2 pi fc / sr
    (close to FRASIL's 1 - exp(-w), and no exp~: few objects, each costs as much here as at full rate)"""
    xc = chain(cs, x, ["clip~ 0 1"], xx, y)
    w = chain(cs, mul(cs, xc, xc, xx, y + 25), [f"*~ {span}", f"+~ {lo}"], xx, y + 50)
    w = chain(cs, mul(cs, w, f, xx, y + 100), [f"*~ {2 * math.pi / 44100:.8f}", "clip~ 0 2.3"], xx, y + 125)
    q = cs.obj("/~", xx, y + 200)
    cs.c(w, 0, q, 0)
    cs.c(chain(cs, w, ["+~ 1"], xx + 60, y + 175), 0, q, 1)
    return q


def ctl_float(cs, recv, expr, x, y):
    """[r recv] -> [expr ...]: a knob-only value, computed as a message (no signal objects)"""
    return chain(cs, cs.obj(f"r {recv}", x, y), [f"expr {expr}"], x, y + 25)


def tide_sig(cs, x, y):
    """the tide: one slow turn (about 40 s) on the brightness, deeper with Motion (inside a Ctl block)"""
    t = cs.obj("*~ 0.2", x, y + 25)
    cs.c(cs.obj("osc~ 0.025", x, y), 0, t, 0)
    cs.c(ctl_float(cs, "$1-p3", "$f1 * 0.3", x + 100, y - 25), 0, t, 1)
    return t


MW = "$f1 * (1 + 2 * $f1)"                                # Motion's wander: wider as it rises (FRASIL)


def frasil_choir(s, ins):
    """CHOEUR: three saws, the sides +-detune (8 .. 22 cents), each drifting (up to +-21 cents at full Motion),
    through a one-pole whose cutoff is f (1 + 39 ce^2) (FRASIL), ce from Timbre, the tide and breath"""
    f, prs, nn = ins
    c = Ctl(s, 600, 30)
    cs = c.s
    fi, prsi = c.i(f), c.i(prs)
    cf = []
    for k, side in enumerate((0, -1, 1)):
        m = cs.obj("*~ 0.0003", 20 + k * 90, 230)                     # drift depth (ratio)
        cs.c(cs.obj(f"osc~ {DRIFT_HZ[k]}", 20 + k * 90, 200), 0, m, 0)
        cs.c(ctl_float(cs, "$1-p3", f"{MW} * 7 * 0.0005778", 20 + k * 90, 150), 0, m, 1)
        o = cs.obj(f"+~ {1 + side * 12 * 0.0005778:.6f}", 20 + k * 90, 255)
        cs.c(m, 0, o, 0)
        if side:
            cs.c(ctl_float(cs, "$1-p3", f"1 + {side} * (8 + 14 * $f1) * 0.0005778", 20 + k * 90, 100), 0, o, 1)
        cf.append(c.f(mul(cs, o, fi, 20 + k * 90, 280)))
    ce = cs.obj("+~ 0.5", 500, 300)
    cs.c(add(cs, tide_sig(cs, 400, 200), chain(cs, prsi, ["*~ 0.5"], 600, 250), 500, 275), 0, ce, 0)
    cs.c(ctl_float(cs, "$1-p4", "$f1 * 0.8 + ($f1 - 0.5) * 0.6", 500, 150), 0, ce, 1)
    a = c.o(onepole(cs, fi, ce, 1, 39, 500, 330))
    sw = [s.obj("lib/bsaw", 20 + k * 150, 120) for k in range(3)]
    for k in range(3):
        s.c(cf[k], 0, sw[k], 0)
        s.c(nn, 0, sw[k], 1)
    sm = add(s, add(s, sw[0], sw[1], 20, 160), sw[2], 20, 185)
    return onepole_run(s, sm, a, 0.57)


def onepole_run(s, x, a, gain):
    """y = a x + (1 - a) y, then x gain (level-matched)"""
    lp = s.obj("rpole~", 20, 250)
    s.c(mul(s, x, a, 20, 220), 0, lp, 0)
    s.c(chain(s, a, ["*~ -1", "+~ 1"], 150, 220), 0, lp, 1)
    return chain(s, lp, [f"*~ {gain}"], 20, 280)


def frasil_partials(s, ins):
    """PARTIELS: NP sines at the harmonics. Timbre tilts their levels (bright .. dark), levelled to the same
    loudness (FRASIL: 0.6 / sqrt(sum a^2)) - a message, knob values only; each level wanders with Motion; breath and
    the tide open a one-pole on their sum"""
    f, prs = ins
    c = Ctl(s, 600, 30)
    cs = c.s
    fi, prsi = c.i(f), c.i(prs)
    tilt = cs.obj("expr " + "; ".join(
        f"pow(2, -(0.3 + 2.7 * min(1, max(0, 1.05 - $f1 - ($f1 - 0.5) * 0.7))) * {math.log2(k + 1):.4f})"
        for k in range(NP)), 1100, 300)
    cs.c(cs.obj("r $1-p4", 1100, 275), 0, tilt, 0)
    pk = cs.obj("pack " + " ".join(["0"] * NP), 1100, 330)          # (expr's outlets fire right to left: pack's
    for k in range(NP):                                               # hot left inlet comes last)
        cs.c(tilt, k, pk, k)
    N = "0.6 / sqrt(" + " + ".join(f"$f{k + 1} * $f{k + 1}" for k in range(NP)) + ")"
    lev = cs.obj("expr " + "; ".join(f"$f{k + 1} * {N}" for k in range(NP)), 1100, 360)
    cs.c(pk, 0, lev, 0)
    dep = ctl_float(cs, "$1-p3", "$f1 * 0.7", 20, 350)
    tot = None
    for k in range(NP):
        w = cs.obj("*~ 0", 20 + k * 90, 400)                          # 1 + depth x drift
        cs.c(cs.obj(f"osc~ {DRIFT_HZ[3 + k]}", 20 + k * 90, 375), 0, w, 0)
        cs.c(dep, 0, w, 1)
        ak = cs.obj("*~ 0.2", 20 + k * 90, 450)
        cs.c(to(cs, w, "+~ 1", 20 + k * 90, 425), 0, ak, 0)
        cs.c(lev, k, ak, 1)
        fk = chain(s, f, [f"*~ {k + 1}"], 20 + k * 120, 90) if k else f
        o = mul(s, chain(s, fk, ["osc~"], 20 + k * 120, 120), c.f(ak), 20 + k * 120, 150)
        tot = o if tot is None else add(s, tot, o, 20 + k * 120, 180)
    pcv = cs.obj("+~ 0.35", 700, 300)
    cs.c(add(cs, tide_sig(cs, 800, 200), chain(cs, prsi, ["*~ 0.6"], 700, 250), 700, 275), 0, pcv, 0)
    cs.c(ctl_float(cs, "$1-p4", "0.35 + ($f1 - 0.5) * 0.6", 700, 150), 0, pcv, 1)
    return onepole_run(s, tot, c.o(onepole(cs, fi, pcv, 3, 30, 700, 330)), 0.75)


def frasil_souffle(s, ins):
    """SOUFFLE: noise through resonators at f, 2f, 3f; more Souffle = louder and glassier (narrower); breath and
    brightness bring the upper ones in (FRASIL's sb). Noise through a band-pass of peak 1 has power ~ f / q, so the
    level goes as sqrt(q / f): pitch and Q don't move the loudness"""
    f, prs = ins
    c = Ctl(s, 600, 30)
    cs = c.s
    rg = cs.obj("/~", 300, 300)
    cs.c(ctl_float(cs, "$1-p2", "0.5 * sqrt((4 + $f1 * $f1 * 90) * 220)", 300, 250), 0, rg, 0)
    cs.c(chain(cs, c.i(f), ["sqrt~"], 400, 275), 0, rg, 1)
    g0 = c.f(rg)
    sb = ex(s, "min(1, max(0.05, 0.55 + ($v1 - 0.5) * 0.8 + $v2 * 0.5))", [s.obj("r~ $1-p4~", 700, 30), prs], 700, 60)
    nz = s.obj("noise~", 20, 80)
    q = chain(s, s.obj("r $1-p2", 900, 30), ["expr 4 + $f1 * $f1 * 90"], 900, 55)
    g1 = mul(s, g0, sb, 300, 100)
    gains = (g0, g1, mul(s, g1, sb, 400, 100))
    tot = None
    for k, rt in enumerate(SOUFFLE_RATIOS):
        b = s.obj("vcf~ 10", 20 + k * 150, 150)
        s.c(nz, 0, b, 0)
        s.c(chain(s, f, [f"*~ {rt}", "clip~ 20 12000"], 20 + k * 150, 100), 0, b, 1)
        s.c(q, 0, b, 2)
        o = mul(s, b, gains[k], 20 + k * 150, 180)
        tot = o if tot is None else add(s, tot, o, 20 + k * 150, 210)
    return chain(s, tot, ["*~ 2.6"], 20, 240)


def frasil(path):
    e, pl, env, tb = frame("Frasil - an ambient drone voice after FRASIL (Styves Goupil): CHOEUR, three detuned saws "
                           "through a soft low-pass; PARTIELS, additive partials whose levels wander; SOUFFLE, breath "
                           "noise ringing resonators tuned to the note. Every voice drifts on its own. Breath swells "
                           "and opens it. Knobs: Layers (choir .. partials), Souffle, Motion, Timbre. Each layer runs "
                           "(with its own slow-rate controls) only while it is turned up.")
    p1, p2, bamt = (r(e, n, 650 + i * 90, 30) for i, n in enumerate(("$1-p1~", "$1-p2~", "eng-bamt~")))
    es = chain(e, env, ["lop~ 3"], 300, 80)               # a slow swell, as a drone breathes
    prs = mul(e, es, bamt, 650, 80)                       # the 'pressure': breath x Breath>Tone
    c = Ctl(e, 300, 120)                                  # pitch -> Hz and the saws' rate at sr/8
    fi = c.freq(pl)
    f = c.f(fi)
    nn = c.f(c.ex("$v1 / max(1, $v2)", [c.i(r(e, "eng-sawk", 150, 80)), fi]))
    choir = switched(e, "choir", "$1-p1", "$f1 < 0.97", frasil_choir, [f, prs, nn], 20, 400)
    part = switched(e, "partials", "$1-p1", "$f1 > 0.03", frasil_partials, [f, prs], 150, 400)
    souf = switched(e, "souffle", "$1-p2", "$f1 > 0.02", frasil_souffle, [f, prs], 300, 400)
    # about equal power across Layers (a plain crossfade of two different sounds dips 3 dB half-way)
    layers = add(e, mul(e, choir, ex(e, "1 - $v1 * $v1", [p1], 20, 440), 20, 475),
                 mul(e, part, ex(e, "1 - (1 - $v1) * (1 - $v1)", [p1], 150, 440), 150, 475), 20, 500)
    mix = add(e, layers, mul(e, souf, p2, 300, 475), 20, 530)
    # breath swells it (up to +4 dB louder), warmth (a soft saturation), the body tone
    sw = ex(e, "0.75 + $v1 * 0.5", [prs], 500, 530)
    warm = softclip(e, mul(e, mix, sw, 20, 560), 20, 580)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 650), r(e, "eng-body~", 500, 650), 400, 700)
    finish(e, add(e, warm, chain(e, body, ["*~ 0.6"], 400, 720), 20, 740), es, 1.1, 20, 770, path)


# ================================================================== Glint
# the modulator over the carrier, knob 1 picks one: FRASIL's 13 (its default X3.5 sounds an octave below the note:
# the sidebands fall on half-multiples; ours is X3)
RATIOS = (0.5, 1, 1.414, 2, 2.756, 3, 3.5, 4, 5, 7, 9, 11, 13.6)


def glint(path):
    e, pl, env, tb = frame("Glint - icy FM bells after FRASIL's GLINT (Styves Goupil): a modulator at Ratio into a "
                           "carrier, bright at the strike and mellower as it rings, a vibrato fading in after it. "
                           "Breath sets the level and brightness. Knobs: Ratio, Bright, Decay, Ring (0 a bell that dies "
                           "away, up: held like a lead)")
    p2, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in enumerate(("$1-p2~", "$1-p4~", "eng-bamt~")))
    eb = mul(e, env, bamt, 650, 80)
    # the strike: a pitch message with time 0 (a new note) fires two pings, the level's and the index's
    st = chain(e, e.ip, ["unpack 0 0"], 150, 30)
    hit = chain(e, to(e, st, "sel 0", 150, 80, outlet=1), ["t b b"], 150, 105)
    dk = chain(e, e.obj("r $1-p3", 350, 105), ["expr 80 * pow(75, $f1)", "t f f"], 350, 130)   # 80 ms .. 6 s
    pa = e.obj("f 1000", 150, 160)
    e.c(dk, 1, pa, 1)
    e.c(hit, 1, pa, 0)
    ping = to(e, msg_to(e, pa, "0, 1 4, 0 $1 4", 150, 185), "vline~", 150, 210)
    pi_ = e.obj("f 300", 300, 160)
    e.c(to(e, dk, "expr 30 + $f1 * 0.2", 450, 155, outlet=0), 0, pi_, 1)
    e.c(hit, 0, pi_, 0)
    pingi = to(e, msg_to(e, pi_, "0, 1 2, 0 $1 2", 300, 185), "vline~", 300, 210)
    # cubed: an exponential-like fall
    pa3 = mul(e, mul(e, ping, ping, 150, 240), ping, 150, 265)
    pi3 = mul(e, mul(e, pingi, pingi, 300, 240), pingi, 300, 265)
    # pitch, the vibrato (5.2 Hz, up to 12 cents, fading in as the strike dies) and the modulator at Ratio
    c = Ctl(e, 500, 300)
    cs = c.s
    vib = mul(cs, cs.obj("osc~ 5.2", 400, 80), c.ex("(1 - $v1) * 0.12", [c.i(ping)]), 400, 110)
    fi = c.freq(pl, vib)
    rt = chain(cs, cs.obj("r $1-p1", 600, 80),
               [f"expr int(min(max($f1, 0), 0.999) * {len(RATIOS)})",
                "sel " + " ".join(str(k) for k in range(len(RATIOS)))], 600, 105)
    rv = cs.obj("f 3", 600, 180)
    for k, v in enumerate(RATIOS):
        cs.c(msg_to(cs, rt, str(v), 600 + k * 40, 150, outlet=k), 0, rv, 0)
    fm = cs.obj("*~ 3", 400, 220)
    cs.c(fi, 0, fm, 0)
    cs.c(rv, 0, fm, 1)
    f, fmo = c.f(fi), c.f(fm)
    # the index: Bright^2 x 5 at the strike, down to half as it rings; breath brightens it (radians -> turns: / 2pi)
    idx = ex(e, "$v1 * $v1 * 5 * (0.5 + 0.5 * $v2) * (0.5 + $v3) * 0.15915", [p2, pi3, eb], 20, 380)
    mod = mul(e, chain(e, fmo, ["phasor~", "cos~"], 300, 400), idx, 300, 450)
    car = chain(e, add(e, chain(e, f, ["phasor~"], 20, 420), mod, 20, 470), ["cos~"], 20, 495)
    # the level: the strike decays to Ring's level, held while you breathe
    amp = ex(e, "$v1 + (1 - $v1) * $v2", [p4, pa3], 150, 520)
    # the body: a sine an octave down that rings with the bell (not held under it)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 520), r(e, "eng-body~", 500, 520), 400, 560)
    finish(e, mul(e, add(e, car, chain(e, body, ["*~ 0.5"], 400, 580), 20, 600), amp, 20, 620), env, 0.75, 20, 640,
           path)


ENGINES = {
    "frasil": (frasil, "Layers Souffle Motion Timbre", "0 0.35 0.4 0.5"),
    "glint": (glint, "Ratio Bright Decay Ring", f"{5.5 / len(RATIOS):.3f} 0.45 0.55 0.3"),
}

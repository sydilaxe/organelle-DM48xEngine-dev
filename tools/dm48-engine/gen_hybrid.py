"""Hybrid engines: modes live in their own [switch~] subpatches, so only the chosen ones cost CPU."""
from pdgen import Canvas
from gen_engines import frame, mul, add, chain, ex, softclip, pitch_to_freq, finish, r


def selector(c, recv, k, x, y):
    """[r recv] -> == k -> change -> [switch~]  (switch~ starts off)"""
    chain(c, c.obj(f"r {recv}", x, y), [f"== {k}", "change -1", "switch~"], x, y + 25)


def mode_sub(name, k, recv, nin, build):
    """subpatch with nin signal inlets (left to right), one outlet~, switched on when recv == k"""
    s = Canvas(name, w=900, h=600)
    ins = [s.obj("inlet~", 20 + i * 110, 10) for i in range(nin)]
    selector(s, recv, k, 750, 10)
    out = build(s, ins)
    s.c(out, 0, s.obj("outlet~", 20, 560), 0)
    return s


def vowel_expr(idx):
    # formant tables (Hz) for u o a e i
    F = [(300, 870, 2240), (450, 800, 2830), (730, 1090, 2440), (530, 1840, 2480), (270, 2290, 3010)]
    v = [row[idx] for row in F]
    e = str(v[4])
    for i in (3, 2, 1, 0):
        e = f"if($v1 < {i + 1}, {v[i]} + ({v[i + 1] - v[i]}) * ($v1 - {i}), {e})"
    return e


# ------------------------------------------------------------------ sources (inlets: f, eb, color, nn, sr)
def src_phase(s, ins):
    """CZ phase distortion: breath is the DCW (brightness) envelope; Color blends in the resonant CZ wave"""
    f, eb, col, nn, sr = ins
    ph = chain(s, f, ["phasor~"], 20, 60)
    d = ex(s, "max(0.5 - 0.48 * min(1, $v1 * 0.3 + $v2 * 0.9), 4 * $v3 / $v4)", [col, eb, f, sr], 150, 60)
    pb = ex(s, "if($v1 < $v2, 0.5 * $v1 / $v2, 0.5 + 0.5 * ($v1 - $v2) / (1 - $v2))", [ph, d], 20, 100)
    saw = chain(s, pb, ["cos~", "*~ -1"], 20, 130)
    R = ex(s, "min(1 + $v1 * 5 + $v2 * 4, 0.45 * $v4 / $v3)", [col, eb, f, sr], 300, 60)
    reso = mul(s, chain(s, mul(s, ph, R, 300, 100), ["cos~"], 300, 125),
               chain(s, ph, ["cos~", "*~ -0.5", "+~ 0.5"], 420, 100), 300, 200)
    return ex(s, "$v1 * (1 - $v3 * 0.8) + $v2 * $v3 * 1.4", [saw, reso, col], 20, 260)


def src_vowel(s, ins):
    """formant voice (Braids 'Vowel' idea): saw + aspiration through 3 formants; breath opens the vowel"""
    f, eb, col, nn, sr = ins
    saw = s.obj("lib/bsaw", 20, 60)
    s.c(f, 0, saw, 0)
    s.c(nn, 0, saw, 1)
    asp = mul(s, s.obj("noise~", 150, 60), ex(s, "0.05 + $v1 * 0.25", [eb], 250, 60), 150, 90)
    src = add(s, saw, asp, 20, 120)
    x = ex(s, "4 * min(1, max(0, $v1 * 0.75 + $v2 * 0.4))", [col, eb], 400, 60)
    outs = []
    for i, (q, g) in enumerate(((5, 1.0), (10, 0.7), (16, 0.45))):
        F = ex(s, vowel_expr(i), [x], 400, 100 + i * 30)
        b = s.obj(f"vcf~ {q}", 20 + i * 130, 200)
        s.c(src, 0, b, 0)
        s.c(F, 0, b, 1)
        outs.append(chain(s, b, [f"*~ {g * q ** 0.5 * 1.2}"], 20 + i * 130, 230))
    return add(s, add(s, outs[0], outs[1], 20, 280), outs[2], 20, 310)


def src_pulse(s, ins):
    """Juno-style: soft-edged pulse with PWM (breath speeds it up and widens it) + square sub an octave down"""
    f, eb, col, nn, sr = ins
    saw = s.obj("lib/bsaw", 20, 60)
    s.c(f, 0, saw, 0)
    s.c(nn, 0, saw, 1)
    lfo = chain(s, ex(s, "0.3 + $v1 * 4", [eb], 200, 60), ["osc~"], 200, 90)
    w = ex(s, "($v1 * 0.35 + $v3 * 0.1) * $v2", [col, lfo, eb], 200, 130)
    k = ex(s, "min(8, 1500 / $v1)", [f], 350, 60)          # softer edges up high (less aliasing)
    pul = chain(s, ex(s, "($v1 + $v2) * $v3", [saw, w, k], 20, 160), ["clip~ -0.5 0.5"], 20, 190)
    sub = chain(s, ex(s, "$v1 * 0.5", [f], 350, 100), ["phasor~", "-~ 0.5"], 350, 125)
    subq = chain(s, ex(s, "$v1 * $v2", [sub, k], 350, 175), ["clip~ -0.5 0.5", "*~ 0.6"], 350, 200)
    return add(s, pul, subq, 20, 260)


def src_breath(s, ins):
    """blown: pitched noise (DOOM's noise x oscillator 'grit') + a breathy flute tone; Color = noise <-> tone"""
    f, eb, col, nn, sr = ins
    nz = s.obj("noise~", 20, 60)
    q = ex(s, "40 - $v1 * 30", [eb], 150, 60)              # more breath = wider band
    jet = s.obj("vcf~ 20", 20, 100)
    s.c(nz, 0, jet, 0)
    s.c(f, 0, jet, 1)
    tone = chain(s, f, ["osc~"], 300, 60)
    grit = mul(s, mul(s, nz, tone, 300, 100), ex(s, "$v1 * 0.4", [eb], 400, 100), 300, 130)
    nzs = chain(s, jet, ["*~ 5"], 20, 130)
    return ex(s, "$v1 * (1 - $v4) * 1.5 + $v2 * $v4 * (0.5 + $v5) + $v3", [nzs, tone, grit, col, eb], 20, 200)


# ------------------------------------------------------------------ bodies (inlets: in, f, eb, shape, sr)
def body_filter(s, ins):
    """plain resonant lowpass; breath opens it (key-tracked); Shape = resonance"""
    x, f, eb, sh, sr = ins
    cf = ex(s, "min(6500, $v1 * (1.2 + $v2 * $v2 * 14) + 150)", [f, eb], 150, 60)
    lp = s.obj("vcf~ 1", 20, 120)
    s.c(x, 0, lp, 0)
    s.c(cf, 0, lp, 1)
    q = chain(s, s.obj("r eng-p4", 300, 60), ["expr 0.7 + $f1 * $f1 * 7"], 300, 85)
    s.c(q, 0, lp, 2)
    return chain(s, lp, [], 20, 150) if False else _lp_out(s, lp)


def _lp_out(s, lp):
    o = s.obj("*~ 1", 20, 160)
    s.c(lp, 1, o, 0)          # vcf~ right outlet = lowpass
    return o


def body_modal(s, ins):
    """Elements-style modal resonator: 6 modes, Shape = geometry (string -> bell); breath lets them ring longer"""
    x, f, eb, sh, sr = ins
    exc = chain(s, x, ["*~ 0.6"], 20, 40)
    outs = []
    for n in range(1, 7):
        xx = 20 + (n - 1) * 120
        rat = ex(s, f"{n} * (1 + $v1 * $v1 * {0.06 * (n * n - 1) / 6:.4f}) * ($v1 * 0.1 + 1)", [sh], xx, 80)
        fn = mul(s, f, rat, xx, 110)
        amp = 0.9 * abs(__import__("math").sin(n * 3.14159 * 0.23)) / n ** 0.4
        b = s.obj("vcf~ 1", xx, 170)
        s.c(exc, 0, b, 0)
        s.c(chain(s, fn, ["clip~ 20 12000"], xx, 140), 0, b, 1)
        # decay: q = pi * f * T, T = (0.6 .. 3 s) / sqrt(n); fixed per mode at control rate from the base pitch
        outs.append((b, amp, n))
    qs = chain(s, s.obj("r eng-p4", 760, 40), ["t f"], 760, 65)
    res = None
    for b, amp, n in outs:
        qv = ex(s, f"min(3000, 3.14159 * $v1 * {n} * (0.6 + $v2 * 2.4) / {n ** 0.5:.3f})", [f, eb], 20 + (n - 1) * 120, 200)
        # vcf~ q is control-rate: approximate with a fixed long ring; breath scales the level instead
        g = chain(s, b, [f"*~ {amp * 4:.3f}"], 20 + (n - 1) * 120, 230)
        res = g if res is None else add(s, res, g, 20, 260 + n * 20)
        s.items[qv] = ("text", (20 + (n - 1) * 120, 200, "-"))      # (placeholder removed below)
    return add(s, res, chain(s, x, ["*~ 0.25"], 300, 400), 20, 420)


def build_hybrid(path):
    e, pl, env, tb = frame("Hybrid - SOURCE x BODY. Knob 1 picks the source (Phase, Vowel, Pulse, Breath), knob 2 the body "
                           "(Filter, Modal, Strings, Tube). Only the chosen two run. Knob 3 Color (source), knob 4 Shape (body).")
    return e

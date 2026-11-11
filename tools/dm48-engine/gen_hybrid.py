"""Two engines with switchable modes: Hybrid (SOURCE x BODY) and Doom (Lyra-style cross-modulated triangles into a
dirty chain). Each mode is its own [switch~] subpatch, so only the chosen ones cost CPU; turning a mode knob
crossfades the old and the new mode over 10 ms. Native signal objects only (ex() compiles formulas, see sigexpr)."""
import math
from pdgen import Canvas
from gen_engines import frame, mul, add, chain, ex, softclip, finish, r, Ctl
from sec_core import to, msg_to


def switched(e, nm, knob, cond, build, ins, x, y, gain=None):
    """a subpatch that runs only while [r knob] -> [expr cond] is 1 (cond on $f1, the knob's 0..1 value). It gets the
    signals ins on its inlet~s; build(s, inlets) returns its output. Switching on fades in over 10 ms, off fades out
    and switches the DSP off 20 ms later. On switch-on [s $0-on-<nm>] fires (clear delay lines, reset filters)."""
    global MODE
    s = Canvas(nm, w=1000, h=700)
    s.comment(f"{nm}: runs only while {cond}", 20, 5)
    inl = [s.obj("inlet~", 20 + i * 110, 30) for i in range(len(ins))]
    sw = s.obj("switch~", 850, 230)
    g = s.obj("line~", 700, 230)
    sel = chain(s, s.obj(f"r {knob}", 850, 30), [f"expr {cond}", "change -1", "sel 1 0"], 850, 55)
    off = s.obj("delay 20", 950, 180)
    on = to(s, sel, "t b b b", 850, 130)
    s.c(msg_to(s, on, "stop", 950, 155, outlet=2), 0, off, 0)
    s.c(msg_to(s, on, "1", 900, 180, outlet=1), 0, sw, 0)
    s.c(msg_to(s, on, "1 10", 850, 180, outlet=0), 0, g, 0)
    to(s, on, f"s $0-on-{nm}", 900, 205, outlet=1)        # (before DSP runs) a mode clears its old delay lines
    ft = to(s, sel, "t b b", 950, 130, outlet=1)
    s.c(msg_to(s, ft, "0 10", 1000, 155, outlet=1), 0, g, 0)
    s.c(ft, 0, off, 0)
    s.c(msg_to(s, off, "0", 950, 205), 0, sw, 0)
    MODE = nm
    out = build(s, inl)
    if gain is not None:
        out = chain(s, out, [f"*~ {gain:.4f}"], 20, 615)
    s.c(mul(s, out, g, 20, 640), 0, s.obj("outlet~", 20, 670), 0)
    box = e.sub(s, x, y)
    for i, src in enumerate(ins):
        e.c(src, 0, box, i)
    return box


def modes(e, knob, names, builders, ins, x, y, gains=None):
    """one switched() subpatch per mode, picked by the control-rate knob [r knob] (0..1 -> int(v * n)); the outputs
    are summed. gains: per-mode level trims (loudness matching)."""
    n = len(names)
    total = None
    for k, (nm, build) in enumerate(zip(names, builders)):
        box = switched(e, nm, knob, f"int(min(max($f1, 0), 0.999) * {n}) == {k}", build, ins, x + k * 120, y,
                       gains[k] if gains else None)
        total = box if total is None else add(e, total, box, x + k * 120, y + 30)
    return total


MODE = ""


def delwrite(s, src, name, ms, x, y):
    """[delwrite~ name ms], cleared whenever its mode is switched on (else the old contents ring out: a click)"""
    d = s.obj(f"delwrite~ {name} {ms}", x, y)
    s.c(src, 0, d, 0)
    s.c(msg_to(s, s.obj(f"r $0-on-{MODE}", x + 150, y - 50), "clear", x + 150, y - 25), 0, d, 0)
    return d


def sr_sig(s, x, y):
    """the sample rate as a signal (eng-sawk = sr / 2.5; engines get no loadbang)"""
    return chain(s, s.obj("r~ eng-sawk", x, y), ["*~ 2.5"], x, y + 25)


# ================================================================== Hybrid
# sources: inlets f (Hz), eb (breath x Breath>Tone), nn (sr / 2.5f for lib/bsaw); Color = knob 3
def src_phase(s, ins):
    """CZ phase distortion: breath is the DCW (brightness) envelope; Color blends in the resonant CZ wave"""
    f, eb, nn = ins
    col, sr = s.obj("r~ $1-p3~", 400, 30), sr_sig(s, 500, 30)
    ph = chain(s, f, ["phasor~"], 20, 80)
    d = ex(s, "max(0.5 - 0.48 * min(1, $v1 * 0.3 + $v2 * 0.9), 4 * $v3 / $v4)", [col, eb, f, sr], 150, 80)
    pb = add(s, ex(s, "min($v1 / (2 * $v2), 0.5)", [ph, d], 20, 200),
             ex(s, "max(($v1 - $v2) / (2 - 2 * $v2), 0)", [ph, d], 150, 200), 20, 300)
    saw = chain(s, pb, ["cos~", "*~ -1"], 20, 330)
    R = ex(s, "min(1 + $v1 * 5 + $v2 * 4, 0.45 * $v4 / $v3)", [col, eb, f, sr], 300, 80)
    reso = mul(s, chain(s, mul(s, ph, R, 300, 200), ["cos~"], 300, 225),
               chain(s, ph, ["cos~", "*~ -0.5", "+~ 0.5"], 420, 200), 300, 300)
    return ex(s, "$v1 * (1 - $v3 * 0.8) + $v2 * $v3 * 1.4", [saw, reso, col], 20, 400)


VOWELS = [(300, 870, 2240), (450, 800, 2830), (730, 1090, 2440), (530, 1840, 2480), (270, 2290, 3010)]   # u o a e i


def src_vowel(s, ins):
    """formant voice (Braids' Vowel idea): saw + aspiration through 3 formants; Color and breath move u-o-a-e-i"""
    f, eb, nn = ins
    col = s.obj("r~ $1-p3~", 400, 30)
    saw = s.obj("lib/bsaw", 20, 80)
    s.c(f, 0, saw, 0)
    s.c(nn, 0, saw, 1)
    asp = mul(s, s.obj("noise~", 150, 80), ex(s, "0.05 + $v1 * 0.25", [eb], 250, 80), 150, 110)
    src = add(s, saw, asp, 20, 140)
    c = Ctl(s, 400, 200)                                  # the formant frequencies at sr/8
    x = c.ex("4 * min(1, max(0, $v1 * 0.75 + $v2 * 0.4))", [c.i(col), c.i(eb)])
    outs = []
    for i, (q, g) in enumerate(((5, 1.0), (10, 0.7), (16, 0.45))):
        v = [row[i] for row in VOWELS]
        fx = f"{v[0]}" + "".join(f" + {v[j + 1] - v[j]} * min(1, max(0, $v1 - {j}))" for j in range(4))
        b = s.obj(f"vcf~ {q}", 20 + i * 130, 300)
        s.c(src, 0, b, 0)
        s.c(c.o(c.ex(fx, [x])), 0, b, 1)
        outs.append(chain(s, b, [f"*~ {g * q ** 0.5 * 1.2:.4f}"], 20 + i * 130, 330))
    return add(s, add(s, outs[0], outs[1], 20, 380), outs[2], 20, 410)


def src_pulse(s, ins):
    """Juno-style: soft-edged pulse with PWM (breath speeds it up and widens it) + square sub an octave down"""
    f, eb, nn = ins
    col = s.obj("r~ $1-p3~", 400, 30)
    saw = s.obj("lib/bsaw", 20, 80)
    s.c(f, 0, saw, 0)
    s.c(nn, 0, saw, 1)
    lfo = chain(s, ex(s, "0.3 + $v1 * 4", [eb], 200, 80), ["osc~"], 200, 130)
    w = ex(s, "($v1 * 0.35 + $v3 * 0.1) * $v2", [col, lfo, eb], 200, 160)
    k = ex(s, "min(8, 1500 / $v1)", [f], 350, 80)          # softer edges up high (less aliasing)
    pul = chain(s, ex(s, "($v1 + $v2) * $v3", [saw, w, k], 20, 260), ["clip~ -0.5 0.5"], 20, 330)
    sub = chain(s, f, ["*~ 0.5", "phasor~", "-~ 0.5"], 350, 160)
    subq = chain(s, mul(s, sub, k, 350, 240), ["clip~ -0.5 0.5", "*~ 0.6"], 350, 265)
    return add(s, pul, subq, 20, 360)


def src_breath(s, ins):
    """blown: pitched noise (DOOM's noise x oscillator grit) + a breathy flute tone; Color = noise <-> tone"""
    f, eb, nn = ins
    col = s.obj("r~ $1-p3~", 400, 30)
    nz = s.obj("noise~", 20, 80)
    jet = s.obj("vcf~ 20", 20, 110)
    s.c(nz, 0, jet, 0)
    s.c(f, 0, jet, 1)
    tone = chain(s, f, ["osc~"], 300, 80)
    grit = mul(s, mul(s, nz, tone, 300, 110), ex(s, "$v1 * 0.4", [eb], 400, 110), 300, 140)
    nzs = chain(s, jet, ["*~ 5"], 20, 140)
    return ex(s, "$v1 * (1 - $v4) * 1.5 + $v2 * $v4 * (0.5 + $v5) + $v3", [nzs, tone, grit, col, eb], 20, 200)


# bodies: inlets x (the source), f, eb; Shape = knob 4
def body_filter(s, ins):
    """resonant lowpass; breath opens it (key-tracked); Shape = resonance"""
    x, f, eb = ins
    cf = ex(s, "min(6500, $v1 * (1.2 + $v2 * $v2 * 14) + 150)", [f, eb], 150, 80)
    lp = s.obj("vcf~ 1", 20, 200)
    s.c(x, 0, lp, 0)
    s.c(cf, 0, lp, 1)
    s.c(chain(s, s.obj("r $1-p4", 400, 80), ["expr 1 + $f1 * $f1 * 7"], 400, 105), 0, lp, 2)   # q >= 1 (vcf~ limit)
    o = s.obj("*~ 1", 20, 230)
    s.c(lp, 1, o, 0)                                      # right outlet = lowpass
    return o


MODES_STRING = (1, 2, 3, 4)
MODES_BELL = (1, 2.76, 5.40, 8.93)


def body_modal(s, ins):
    """Elements-style modal resonator, 4 modes: Shape bends the ratios from a string (1 2 3 4) to a bell
    (1 2.76 5.4 8.93) and lets them ring longer"""
    x, f, eb = ins
    sh = s.obj("r~ $1-p4~", 400, 30)
    q = chain(s, s.obj("r $1-p4", 600, 30), ["expr 12 + $f1 * 60"], 600, 55)
    exc = chain(s, x, ["*~ 0.6"], 20, 60)
    res = None
    for n, (a, b) in enumerate(zip(MODES_STRING, MODES_BELL)):
        xx = 20 + n * 140
        fn = ex(s, f"min(12000, $v1 * ({a} + $v2 * {b - a:.3f}))", [f, sh], xx, 100)
        bp = s.obj("vcf~ 12", xx, 220)
        s.c(exc, 0, bp, 0)
        s.c(fn, 0, bp, 1)
        s.c(q, 0, bp, 2)
        g = chain(s, bp, [f"*~ {1.6 / (n + 1) ** 0.5:.3f}"], xx, 250)
        res = g if res is None else add(s, res, g, xx, 280)
    return add(s, res, chain(s, x, ["*~ 0.25"], 600, 300), 20, 330)


def body_strings(s, ins):
    """Rings-style sympathetic strings: three comb 'strings' tuned to f, 2f and 3f ring along with the source;
    Shape = sustain. Runs in 16-sample blocks so short (high) strings work."""
    x, f, eb = ins
    st = Canvas("strings", w=900, h=500)
    st.comment("three comb strings in 16-sample blocks: delay -> damping -> feedback", 20, 5)
    st.obj("block~ 16", 750, 5)
    ix, iff = st.obj("inlet~", 20, 30), st.obj("inlet~", 200, 30)
    # the strings are fed through a 30 ms fade-in when the mode starts, so they build up instead of stepping in
    rmp = chain(st, msg_to(st, st.obj(f"r $0-on-{MODE}", 350, 30), "0, 0.25 30", 350, 55), ["line~"], 350, 80)
    exc = mul(st, ix, rmp, 20, 100)
    fbk = chain(st, st.obj("r $1-p4", 600, 30), ["expr 0.9 + $f1 * 0.095"], 600, 55)
    tot = None
    for k, rat in enumerate((1, 2, 3)):
        xx = 20 + k * 200
        dl = ex(st, f"max(0.37, 1000 / ($v1 * {rat}))", [iff], xx + 100, 100)
        rd = st.obj(f"vd~ $0-hs{k}", xx, 180)
        st.c(dl, 0, rd, 0)
        lp = to(st, rd, "lop~ 5000", xx, 210)
        st.c(msg_to(st, st.obj(f"r $0-on-{MODE}", xx + 100, 160), "clear", xx + 100, 185), 0, lp, 0)
        fb = to(st, lp, "*~ 0.95", xx, 235)
        st.c(fbk, 0, fb, 1)
        sm = add(st, exc, fb, xx, 270)
        delwrite(st, sm, f"$0-hs{k}", 60, xx, 300)
        tot = rd if tot is None else add(st, tot, rd, xx, 330)
    st.c(add(st, chain(st, tot, ["*~ 0.35"], 20, 360), chain(st, ix, ["*~ 0.3"], 200, 360), 20, 390), 0,
         st.obj("outlet~", 20, 420), 0)
    box = s.sub(st, 20, 200)
    s.c(x, 0, box, 0)
    s.c(f, 0, box, 1)
    hp = to(s, box, "hip~ 30", 20, 230)
    s.c(msg_to(s, s.obj(f"r $0-on-{MODE}", 150, 180), "clear", 150, 205), 0, hp, 0)
    return hp


def body_tube(s, ins):
    """tube: asymmetric saturation (even harmonics) then a key-tracked lowpass; Shape and breath = drive"""
    x, f, eb = ins
    sh = s.obj("r~ $1-p4~", 400, 30)
    drv = ex(s, "1 + $v1 * 6 + $v2 * 3", [sh, eb], 300, 80)
    y = mul(s, x, drv, 20, 160)
    den = add(s, chain(s, y, ["abs~", "*~ 1.4", "+~ 1"], 120, 190), chain(s, y, ["*~ -0.4"], 220, 190), 120, 240)
    tube = s.obj("/~", 20, 270)
    s.c(y, 0, tube, 0)
    s.c(den, 0, tube, 1)
    cf = ex(s, "min(6500, $v1 * (3 + $v2 * 8) + 200)", [f, eb], 300, 280)
    lp = s.obj("vcf~ 1.5", 20, 360)
    s.c(chain(s, tube, ["hip~ 20"], 20, 300), 0, lp, 0)
    s.c(cf, 0, lp, 1)
    o = s.obj("*~ 1.3", 20, 390)
    s.c(lp, 1, o, 0)
    return o


def hybrid(path):
    e, pl, env, tb = frame("Hybrid - SOURCE x BODY. Knob 1 Source (Phase, Vowel, Pulse, Breath), knob 2 Body (Filter, "
                           "Modal, Strings, Tube): only the chosen two run. Knob 3 Color (source), knob 4 Shape (body).")
    bamt = r(e, "eng-bamt~", 650, 30)
    eb = mul(e, env, bamt, 650, 80)
    c = Ctl(e, 300, 100)                                  # pitch -> Hz, saw rate at sr/8
    fi = c.freq(pl)
    f = c.f(fi)
    nn = c.f(c.ex("$v1 / max(1, $v2)", [c.i(r(e, "eng-sawk", 150, 80)), fi]))
    src = modes(e, "$1-p1", ["src-phase", "src-vowel", "src-pulse", "src-breath"],
                [src_phase, src_vowel, src_pulse, src_breath], [f, eb, nn], 20, 200,
                gains=[0.8366, 1.4622, 0.8660, 1.0902])       # level-matched (t_loud)
    body = modes(e, "$1-p2", ["body-filter", "body-modal", "body-strings", "body-tube"],
                 [body_filter, body_modal, body_strings, body_tube], [src, f, eb], 20, 300,
                 gains=[1.5223, 1.0471, 0.6683, 1.1028])
    sub = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 600, 300), r(e, "eng-body~", 700, 300), 600, 350)
    finish(e, add(e, softclip(e, body, 20, 400), sub, 20, 520), env, 0.72, 20, 560, path)


# ================================================================== Doom
# dirty chains: inlets x (the clean core), f, eb, d (dirt 0..1)
def ch_rip(s, ins):
    """RIP: hard drive into a rational tanh, then a bitcrusher and sample-rate reduction that deepen with dirt"""
    x, f, eb, d = ins
    y = chain(s, mul(s, x, ex(s, "1 + $v1 * 30", [d], 150, 60), 20, 90), ["clip~ -3 3"], 20, 115)
    y2 = mul(s, y, y, 150, 140)
    th = ex(s, "$v1 * (27 + $v2) / (27 + 9 * $v2)", [y, y2], 20, 160)
    N = ex(s, "4 + (1 - $v1) * 60", [d], 300, 160)        # quantiser levels
    q = mul(s, th, N, 20, 260)
    rnd = ex(s, "($v1 + 0.5 - fmod($v1 + 4.5, 1)) / $v2", [q, N], 20, 290)   # round(q) / N
    sh = s.obj("samphold~", 20, 400)
    s.c(rnd, 0, sh, 0)
    sr = sr_sig(s, 400, 300)
    s.c(chain(s, ex(s, "$v1 * (1 - $v2 * 0.85)", [sr, d], 300, 340), ["phasor~"], 300, 370), 0, sh, 1)
    return chain(s, sh, ["*~ 0.55"], 20, 430)


def ch_tear(s, ins):
    """TEAR: a 4-stage phaser swept by an LFO that speeds up with breath, then a little drive"""
    x, f, eb, d = ins
    lfo = chain(s, ex(s, "0.15 + $v1 * 2.5", [eb], 300, 60), ["osc~"], 300, 90)
    a = ex(s, "0.35 + $v1 * (0.25 + $v2 * 0.35)", [lfo, d], 300, 120)
    st = x
    for k in range(4):
        rz = s.obj("rzero_rev~", 20, 160 + k * 60)
        s.c(st, 0, rz, 0)
        s.c(a, 0, rz, 1)
        rp = s.obj("rpole~", 20, 185 + k * 60)
        s.c(rz, 0, rp, 0)
        s.c(a, 0, rp, 1)
        st = rp
    ph = chain(s, add(s, x, st, 20, 420), ["*~ 0.6"], 20, 445)
    return softclip(s, mul(s, ph, ex(s, "1 + $v1 * 2", [d], 200, 445), 20, 470), 20, 500)


def ch_metal(s, ins):
    """METAL: inharmonic ring modulation (2.76 f) into a dispersive spring-like comb"""
    x, f, eb, d = ins
    rm = mul(s, x, chain(s, f, ["*~ 2.76", "osc~"], 200, 60), 20, 110)
    mx = ex(s, "$v1 * (1 - $v3 * 0.8) + $v2 * $v3 * 0.8", [x, rm, d], 20, 140)
    rd = s.obj("vd~ $0-dsp", 300, 260)
    s.c(chain(s, s.obj("osc~ 0.7", 450, 200), ["*~ 2", "+~ 23"], 450, 225), 0, rd, 0)
    ap = rd
    for k in range(2):                                    # dispersion: the 'boing'
        rz = to(s, ap, "rzero_rev~ 0.6", 300, 290 + k * 50)
        ap = to(s, rz, "rpole~ 0.6", 300, 315 + k * 50)
    fb = mul(s, chain(s, ap, ["lop~ 4000"], 300, 400), ex(s, "0.55 + $v1 * 0.35", [d], 420, 400), 300, 430)
    wr = add(s, mx, fb, 20, 460)
    delwrite(s, wr, "$0-dsp", 80, 20, 490)
    return chain(s, add(s, mx, chain(s, ap, ["*~ 0.7"], 300, 470), 20, 520), ["*~ 0.6"], 20, 550)


def ch_flesh(s, ins):
    """FLESH: feedback distortion - a saturating loop two periods long, its feedback rising with dirt"""
    x, f, eb, d = ins
    rd = s.obj("vd~ $0-dfl", 300, 120)
    s.c(ex(s, "min(80, max(1.5, 2000 / $v1))", [f], 300, 60), 0, rd, 0)
    fb = mul(s, chain(s, rd, ["lop~ 3000"], 300, 150), ex(s, "$v1 * 0.9", [d], 420, 150), 300, 180)
    y = mul(s, add(s, x, fb, 20, 210), ex(s, "1 + $v1 * 4", [d], 150, 210), 20, 240)
    sat = softclip(s, y, 20, 270)
    delwrite(s, sat, "$0-dfl", 100, 200, 400)
    return chain(s, sat, ["*~ 0.6"], 20, 400)


def doom(path):
    e, pl, env, tb = frame("Doom - two cross-modulating triangles (after Lyra) into a dirty chain (after DOOM_SYNTH): "
                           "Rip, Tear, Metal or Flesh (knob 1; only the chosen one runs). Breath pushes clean to dirty "
                           "and ducks the clean side. Knobs: Chain, Mod, Dirt, Tone")
    p2, p3, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in enumerate(("$1-p2~", "$1-p3~", "$1-p4~", "eng-bamt~")))
    es = chain(e, env, ["lop~ 8"], 300, 80)
    eb = mul(e, es, bamt, 650, 80)
    c = Ctl(e, 300, 100)                                  # pitch, the detuned twin, the tone cutoff at sr/8
    ebi = c.i(eb)
    fi = c.freq(pl)
    f = c.f(fi)
    fb = c.f(c.ex("$v1 * (1.004 + $v2 * 0.004)", [fi, ebi]))
    m = ex(e, "$v1 * $v1 * 1.4 + $v2 * 0.9", [p2, eb], 400, 180)       # cross-mod index
    aprev = e.obj("delread~ $0-a 0", 400, 230)
    phb = chain(e, fb, ["phasor~"], 250, 260)
    triB = ex(e, "4 * abs(fmod($v1 + $v2 * $v3 * 0.18 + 4, 1) - 0.5) - 1", [phb, m, aprev], 250, 310)
    pha = chain(e, f, ["phasor~"], 20, 340)
    triA = ex(e, "4 * abs(fmod($v1 + $v2 * $v3 * 0.18 + 4, 1) - 0.5) - 1", [pha, m, triB], 20, 390)
    e.c(triA, 0, e.obj("delwrite~ $0-a 20", 150, 420), 0)
    clean = chain(e, add(e, triA, triB, 20, 450), ["*~ 0.5"], 20, 475)
    # dirt: the Dirt knob, pushed further by breath
    d = ex(e, "min(1, $v1 * (0.35 + $v2 * 0.9) + $v2 * 0.15)", [p3, eb], 400, 450)
    dirty = modes(e, "$1-p1", ["rip", "tear", "metal", "flesh"], [ch_rip, ch_tear, ch_metal, ch_flesh],
                  [clean, f, eb, d], 20, 520, gains=[1, 1.1092, 1.1749, 1])
    mix = ex(e, "$v1 * (1 - $v3 * 0.7) + $v2 * $v3", [clean, dirty, d], 20, 560)
    cut = c.o(c.ex("min(6500, 150 * pow(2, $v1 * 5.4 + $v2 * 1.2 + ($v3 - 0.5)))", [c.i(p4), ebi, c.i(tb)]))
    lp = e.obj("vcf~ 1", 20, 660)
    e.c(mix, 0, lp, 0)
    e.c(cut, 0, lp, 1)
    lpo = e.obj("*~ 1", 20, 690)
    e.c(lp, 1, lpo, 0)                                    # right outlet = lowpass
    out = chain(e, lpo, ["hip~ 25"], 20, 715)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 650), r(e, "eng-body~", 500, 650), 400, 700)
    finish(e, add(e, out, body, 20, 740), es, 0.93, 20, 770, path)


ENGINES = {
    "hybrid": (hybrid, "Source Body Color Shape", "0.1 0.1 0.5 0.4"),
    "doom": (doom, "Chain Mod Dirt Tone", "0.1 0.3 0.4 0.5"),
}

"""Bundled engines. Each engines/NAME.pd is ONE voice following the engine contract (see CONTRACT)."""
import os
from pdgen import Canvas

CONTRACT = """MAKING AN ENGINE
================
An engine is one Pd patch in this folder: engines/NAME.pd. It is ONE voice; the host
loads a copy into each of its 8 voices. Copy an existing engine and change it.

Inlets (left to right) - each receives "value ms" pairs, ready for [line~]:
  1 pitch    MIDI note number, fractional (bends, tuning and octave already included)
  2 level    0..1 - breath (or velocity), already curved. 0 with the release time at note-off.
  3 timbre   0..1, 0.5 = neutral (MPE CC74 / slide)
  (A pitch message with time 0 marks the start of a new note - e.g. reset a phase or pluck on it.
   With glide (VOICE page) a new note sends "source 0" then "pitch glide-ms"; a legato change in
   Mono mode only sends "pitch glide-ms": no new attack.)
Outlet: one [outlet~], mono.

Shared values you can read anywhere in the engine:
  [r~ eng-p1~] .. [r~ eng-p4~]  the 4 PLAY knobs, 0..1, smoothed   ([r eng-p1] .. control rate)
                 (the bundled engines write this as [r~ $1-p1~]: the host creates every engine with
                  the argument "eng", so it is the same thing)
  Every engine in the folder is created once when the patch loads and switched off until selected,
  so keep idle engines cheap: nothing runs while another engine is selected.
  [r~ eng-bamt~]  SHAPE Breath>Tone, 0..1: scale your breath-to-timbre effects by this
  [r~ eng-body~]  SHAPE Body, 0..1: suggested sub / fundamental level
  [r~ eng-vib]    vibrato in semitones - add it to the pitch
  [r~ eng-sawk]   sample rate / 2.5, for lib/bsaw (band-limited saw)
Helpers: lib/bsaw.pd (band-limited saw: [lib/bsaw] inlets freq~, [r~ eng-sawk] / freq~).

engines/NAME.txt (optional):
  line 1: the 4 knob names shown on the PLAY page (one word each)
  line 2: their default values 0..1
e.g.   Fold Grit Detune Tone;
       0.3 0.2 0.4 0.5;

Tips: keep it light (8 copies run at once). Let breath (the level inlet) shape several
things a little - brightness, harmonics, noise, detune - rather than one thing a lot.
After adding a file, reload the patch; the new engine appears on the ENGINE page.
"""


def frame(title):
    e = Canvas(w=1100, h=900)
    e.comment(title, 20, 5)
    ip, il, it = e.obj("inlet", 20, 30), e.obj("inlet", 300, 30), e.obj("inlet", 500, 30)
    pl = e.obj("line~", 20, 55)
    e.c(ip, 0, pl, 0)
    env = e.obj("line~", 300, 55)
    e.c(il, 0, env, 0)
    tb = e.obj("line~", 500, 55)
    e.c(it, 0, tb, 0)
    return e, pl, env, tb


def mul(e, a, b, x, y):
    o = e.obj("*~", x, y)
    e.c(a, 0, o, 0)
    e.c(b, 0, o, 1)
    return o


def add(e, a, b, x, y):
    o = e.obj("+~", x, y)
    e.c(a, 0, o, 0)
    e.c(b, 0, o, 1)
    return o


def chain(e, src, texts, x, y, outlet=0):
    prev, o = src, outlet
    for i, t in enumerate(texts):
        n = e.obj(t, x, y + i * 25)
        e.c(prev, o, n, 0)
        prev, o = n, 0
    return prev


def ex(e, text, ins, x, y):
    """[expr~ text] with signal inputs ins ($v1, $v2, ...)"""
    o = e.obj(f"expr~ {text}", x, y)
    for i, s in enumerate(ins):
        e.c(s, 0, o, i)
    return o


def softclip(e, src, x, y):
    yc = chain(e, src, ["clip~ -1.5 1.5"], x, y)
    y2 = mul(e, yc, yc, x + 100, y + 25)
    y3 = mul(e, y2, yc, x + 100, y + 50)
    ys = chain(e, y3, ["*~ -0.148148"], x + 100, y + 75)
    return add(e, yc, ys, x, y + 100)


def pitch_to_freq(e, pl, extra, x, y):
    """pitch (+ vibrato + extra signal in semitones) -> Hz"""
    pv = add(e, pl, e.obj("r~ eng-vib", x + 80, y), x, y + 25)
    if extra is not None:
        pv = add(e, pv, extra, x, y + 50)
    return chain(e, pv, ["mtof~", "clip~ 1 20000"], x, y + 75)


def finish(e, sig, env, gain, x, y, path):
    out = mul(e, sig, env, x, y)
    e.c(chain(e, out, [f"*~ {gain}"], x, y + 25), 0, e.obj("outlet~", x, y + 75), 0)
    e.save(path)


def r(e, name, x, y):
    return e.obj(f"r~ {name}", x, y)


def volt(path):
    """raw / electric: two saws -> wavefolder -> sample-rate grit -> filter"""
    e, pl, env, tb = frame("Volt - raw and electric. Two saws, a wavefolder, sample-rate grit, a filter. "
                           "Breath: more folding, more grit, brighter, strains sharp.")
    p1, p2, p3, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in
                            enumerate(("$1-p1~", "$1-p2~", "$1-p3~", "$1-p4~", "eng-bamt~")))
    eb = mul(e, env, bamt, 650, 80)                     # breath x Breath>Tone
    strain = chain(e, eb, ["*~ 0.08"], 650, 105)        # up to +8 cents
    f = pitch_to_freq(e, pl, strain, 20, 80)
    nn = ex(e, "$v1 / max(1, $v2)", [r(e, "eng-sawk", 150, 180), f], 150, 205)   # sr / (2.5 f)
    det = ex(e, "1 + $v1 * $v1 * 0.02 + $v2 * 0.004", [p3, eb], 250, 180)
    f2 = mul(e, f, det, 250, 205)
    s1, s2 = e.obj("lib/bsaw", 20, 240), e.obj("lib/bsaw", 250, 240)
    e.c(f, 0, s1, 0)
    e.c(nn, 0, s1, 1)
    e.c(f2, 0, s2, 0)
    e.c(nn, 0, s2, 1)
    x = add(e, s1, chain(e, s2, ["*~ 0.8"], 250, 265), 20, 300)
    # fold: sin(pi * x * F), F = 1 + fold*4 + breath*3
    F = ex(e, "min(1 + $v1 * 4 + $v2 * 3, 1 + 2500 / $v3)", [p1, eb, f], 400, 300)   # fewer folds up high: less aliasing
    fx = mul(e, x, F, 20, 330)
    fold = chain(e, fx, ["*~ 0.5", "-~ 0.25", "cos~"], 20, 355)
    # grit: sample-and-hold at a rate that drops with Grit and breath
    gr = ex(e, "max(800, 44100 * (1 - $v1 * 0.92) * (1 - $v2 * 0.25))", [p2, eb], 400, 380)
    sh = e.obj("samphold~", 20, 460)
    e.c(fold, 0, sh, 0)
    e.c(chain(e, gr, ["phasor~"], 400, 405), 0, sh, 1)
    # filter: 150 Hz * 2^(tone*5.5 + breath*3 + timbre) (vcf~ needs cutoff well under q * sr / 2pi)
    cut = ex(e, "min(7000, 150 * pow(2, $v1 * 5.5 + $v2 * 3 + ($v3 - 0.5) * 2))", [p4, eb, tb], 400, 480)
    vcf = e.obj("vcf~ 1.3", 20, 520)
    e.c(sh, 0, vcf, 0)
    e.c(cut, 0, vcf, 1)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 250, 520), r(e, "eng-body~", 350, 545), 250, 570)
    mix = add(e, chain(e, vcf, [], 20, 520), body, 20, 600)
    e.conns.remove((vcf, 0, mix, 0))
    e.c(vcf, 1, mix, 0)
    finish(e, softclip(e, mix, 20, 630), env, 1.0, 20, 760, path)


def halo(path):
    """ethereal / resonant: partials that bloom with breath + noise ringing in tuned resonators"""
    e, pl, env, tb = frame("Halo - ethereal and resonant. Sine partials bloom open with breath; breath noise "
                           "rings tuned resonators. Breath: upper partials, air, shimmer, resonator brightness.")
    p1, p2, p3, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in
                            enumerate(("$1-p1~", "$1-p2~", "$1-p3~", "$1-p4~", "eng-bamt~")))
    es = chain(e, env, ["lop~ 4"], 300, 80)             # slow, soft swell
    eb = mul(e, es, bamt, 650, 80)
    f = pitch_to_freq(e, pl, None, 20, 80)
    # partials 1, 2, 3, 4 (3 and 4 drift with Shimmer); amplitudes open with breath x Bloom
    parts = []
    for h, x in ((1, 20), (2, 150), (3, 280), (4.01, 410)):
        if h in (3, 4.01):
            rat = ex(e, f"{h} * (1 + $v1 * {0.004 if h == 3 else 0.007})", [p1], x, 180)
            fh = mul(e, f, rat, x, 205)
        elif h == 2:
            fh = chain(e, f, ["*~ 2"], x, 205)
        else:
            fh = f
        o = chain(e, fh, ["osc~"], x, 230)
        if h == 1:
            parts.append(o)
            continue
        k = {2: 1.5, 3: 2.2, 4.01: 3.0}[h]
        lv = {2: 0.45, 3: 0.3, 4.01: 0.22}[h]
        amp = ex(e, f"{lv} * pow(min(1, $v1 * (0.4 + $v2 * 1.6)), {k} - $v2)", [eb, p4], x, 260)
        parts.append(mul(e, o, amp, x, 290))
    s = add(e, add(e, parts[0], parts[1], 20, 330), add(e, parts[2], parts[3], 280, 330), 20, 360)
    # noise through two resonators at 2f and 3.01f (centre rises a little with breath and timbre)
    nz = e.obj("noise~", 600, 330)
    air = ex(e, "$v1 * (0.15 + $v2 * 0.85)", [p3, eb], 700, 330)
    ng = mul(e, nz, air, 600, 360)
    q = chain(e, e.obj("r $1-p2", 850, 330), ["expr 3 + $f1 * $f1 * 45"], 850, 355)
    rs = []
    for k, x in ((2, 600), (3.01, 750)):
        cf = ex(e, f"min(7000, $v1 * {k} * (1 + $v2 * 0.02 + ($v3 - 0.5) * 0.1))", [f, eb, tb], x, 400)
        b = e.obj("vcf~ 10", x, 430)
        e.c(ng, 0, b, 0)
        e.c(cf, 0, b, 1)
        e.c(q, 0, b, 2)
        rs.append(b)
    rsum = add(e, rs[0], rs[1], 600, 460)
    qg = chain(e, q, ["sqrt", "* 0.5"], 850, 405)
    rg = e.obj("*~ 1", 600, 490)
    e.c(rsum, 0, rg, 0)
    e.c(qg, 0, rg, 1)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 300, 400), r(e, "eng-body~", 400, 425), 300, 450)
    mix = add(e, add(e, s, rg, 20, 520), body, 20, 550)
    finish(e, mix, es, 0.5, 20, 600, path)


def under(path):
    """bass / subharmonic: oscillator + f/2 f/3 f/4 subharmonics, breath brings the deeper ones in"""
    e, pl, env, tb = frame("Under - bass and subharmonics. A tone plus subharmonics f/2 f/3 f/4, saturated, "
                           "low-passed. Breath: lower subs fade in, more drive, filter opens.")
    p1, p2, p3, bamt = (r(e, n, 650 + i * 90, 30) for i, n in
                        enumerate(("$1-p1~", "$1-p2~", "$1-p3~", "eng-bamt~")))
    eb = mul(e, env, bamt, 650, 80)
    f0 = pitch_to_freq(e, pl, None, 20, 80)
    octm = chain(e, e.obj("r $1-p4", 300, 130), ["expr pow(0.5, int(min($f1, 0.999) * 3))"], 300, 155)
    f = e.obj("*~ 1", 20, 180)
    e.c(f0, 0, f, 0)
    e.c(octm, 0, f, 1)
    subs = []
    for d, x in ((1, 20), (2, 150), (3, 280), (4, 410)):
        fd = chain(e, f, [f"*~ {1 / d}"], x, 210)
        o = chain(e, fd, ["osc~"], x, 235)
        if d == 1:
            subs.append(o)
            continue
        w = {2: "$v1 * 0.9 + $v2 * 0.2", 3: "$v1 * $v2 * 0.9", 4: "$v1 * $v1 * 0.7 * (0.3 + $v2)"}[d]
        subs.append(mul(e, o, ex(e, w, [p1, eb], x, 265), x, 295))
    s = add(e, add(e, subs[0], subs[1], 20, 330), add(e, subs[2], subs[3], 280, 330), 20, 360)
    drv = ex(e, "0.8 + $v1 * 5 + $v2 * 3", [p2, eb], 400, 360)
    sat = softclip(e, mul(e, s, drv, 20, 390), 20, 415)
    cut = ex(e, "min(6000, $v1 * (2 + $v2 * 14 + $v3 * 10 + $v4 * 3))", [f, p3, eb, tb], 400, 520)
    vcf = e.obj("vcf~ 1.2", 20, 560)
    e.c(sat, 0, vcf, 0)
    e.c(cut, 0, vcf, 1)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 300, 560), r(e, "eng-body~", 400, 585), 300, 610)
    mix = add(e, chain(e, vcf, [], 20, 560), body, 20, 640)
    e.conns.remove((vcf, 0, mix, 0))
    e.c(vcf, 1, mix, 0)
    finish(e, mix, env, 0.6, 20, 680, path)


def velvet(path):
    """lush virtual-analog pad: three detuned band-limited saws, warm two-stage filter, swell"""
    e, pl, env, tb = frame("Velvet - lush virtual-analog pad. Three detuned saws, a warm 4-pole filter, slow swell. "
                           "Breath: filter opens, detune widens, warmth and slow drift deepen.")
    p1, p2, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in
                        enumerate(("$1-p1~", "$1-p2~", "$1-p4~", "eng-bamt~")))
    sw = chain(e, e.obj("r $1-p3", 300, 80), ["expr 20 - $f1 * 19.7"], 300, 105)
    es = e.obj("lop~ 10", 300, 140)
    e.c(env, 0, es, 0)
    e.c(sw, 0, es, 1)
    eb = mul(e, es, bamt, 650, 80)
    # slow per-voice drift that deepens with breath
    drift = mul(e, chain(e, e.obj("noise~", 450, 80), ["lop~ 0.7", "*~ 6"], 450, 105),
                chain(e, eb, ["*~ 0.05", "+~ 0.01"], 550, 105), 450, 160)
    f = pitch_to_freq(e, pl, drift, 20, 80)
    nn = ex(e, "$v1 / max(1, $v2)", [r(e, "eng-sawk", 150, 180), f], 150, 205)   # sr / (2.5 f)
    d = ex(e, "$v1 * $v1 * 0.018 + $v2 * 0.005", [p2, eb], 300, 180)
    df = mul(e, f, d, 300, 205)
    flo = e.obj("-~", 250, 230)
    e.c(f, 0, flo, 0)
    e.c(df, 0, flo, 1)
    fhi = add(e, f, df, 380, 230)
    saws = []
    for i, src in enumerate((f, flo, fhi)):
        s = e.obj("lib/bsaw", 20 + i * 140, 270)
        e.c(src, 0, s, 0)
        e.c(nn, 0, s, 1)
        saws.append(s)
    side = chain(e, add(e, saws[1], saws[2], 160, 300), ["*~ 0.85"], 160, 325)
    mix = add(e, saws[0], side, 20, 350)
    sub = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 450, 270),
              ex(e, "$v1 * 0.6 + $v2", [p4, r(e, "eng-body~", 550, 270)], 450, 300), 450, 330)
    mix = chain(e, add(e, mix, sub, 20, 380), ["*~ 0.4"], 20, 405)
    warm = ex(e, "1 + $v1 * 1.5 + $v2 * 0.6", [p4, eb], 300, 405)
    sat = softclip(e, mul(e, mix, warm, 20, 430), 20, 455)
    cut = ex(e, "min(6500, mtof(30 + $v1 * 70 + $v2 * 40 + ($v3 - 0.5) * 24))", [p1, eb, tb], 400, 560)
    v1 = e.obj("vcf~ 1.3", 20, 600)
    e.c(sat, 0, v1, 0)
    e.c(cut, 0, v1, 1)
    v2 = e.obj("vcf~ 1.3", 20, 640)
    e.c(v1, 1, v2, 0)
    e.c(cut, 0, v2, 1)
    lv = chain(e, v2, [], 20, 640)
    out = e.obj("*~ 1", 20, 680)
    e.c(v2, 1, out, 0)
    finish(e, out, es, 2.0, 20, 710, path)


def steel(path):
    """pedal steel: a waveguide string (after Steelie by gur_shulman, WTFPL) played by breath"""
    e = Canvas(w=1200, h=900)
    e.comment("Steel - pedal steel string (waveguide, after Steelie by gur_shulman), bowed by breath: no pluck. "
              "Breath is the volume pedal and the bow, and brightens the string. Knobs: Tone, Sustain, Steel, Attack "
              "(how fast the breath swells in: 5 ms .. 2 s)", 20, 5)
    ip, il, it = e.obj("inlet", 20, 30), e.obj("inlet", 300, 30), e.obj("inlet", 500, 30)
    pl = e.obj("line~", 20, 105)
    e.c(ip, 0, pl, 0)
    # breath attack: a rising level ramps over at least the Attack time (falling and note-off keep their own time)
    lu = e.obj("unpack 0 0", 300, 55)
    e.c(il, 0, lu, 0)
    atk = e.obj("expr if($f1 > $f3, max($f2, 5 + $f4 * $f4 * 2000), $f2)", 300, 105)
    e.c(lu, 1, atk, 1)
    lt = e.obj("t f f", 300, 80)
    e.c(lu, 0, lt, 0)
    e.c(lt, 1, atk, 0)
    e.c(e.obj("r $1-p4", 560, 80), 0, atk, 3)
    lpk = e.obj("pack 0 0", 300, 130)
    e.c(atk, 0, lpk, 1)
    e.c(lt, 0, lpk, 0)
    e.c(lt, 0, atk, 2)
    env = e.obj("line~", 300, 155)
    e.c(lpk, 0, env, 0)
    tb = e.obj("line~", 500, 55)
    e.c(it, 0, tb, 0)
    p1, p2, p3, p4, bamt = (e.obj(f"r~ {n}", 650 + i * 90, 30) for i, n in
                            enumerate(("$1-p1~", "$1-p2~", "$1-p3~", "$1-p4~", "eng-bamt~")))
    eb = mul(e, env, bamt, 650, 80)
    f = chain(e, add(e, pl, e.obj("r~ eng-vib", 100, 105), 20, 130), ["mtof~", "clip~ 30 2700"], 20, 155)
    per = ex(e, "1000 / $v1", [f], 20, 205)          # period, ms
    # filter coefficients: damping d (darker = more), dispersion a (steel stiffness)
    dmp = ex(e, "min(0.95, max(0.02, 0.08 + (1 - $v1) * 0.75 - $v2 * 0.3 - ($v3 - 0.5) * 0.2))", [p1, eb, tb], 300, 205)
    disp = ex(e, "-0.05 - $v1 * 0.4", [p3], 450, 205)
    # ms per sample (no loadbang in engines: they are created on the fly) - eng-sawk = sample rate / 2.5
    sr = ex(e, "400 / max(1000, $v1)", [r(e, "eng-sawk", 1000, 100)], 1000, 125)
    # loop delay = period minus the filters' own delay (in samples, converted to ms)
    dl = ex(e, "max(0.37, $v1 - ($v2 / (1 + $v2) + (1 + $v3) / (1 - $v3)) * $v4)", [per, dmp, disp, sr], 20, 260)
    t60 = ex(e, "1.2 + $v1 * $v1 * 11 + $v2 * 3", [p2, eb], 650, 230)
    g = ex(e, "exp(-6.9078 * $v1 / 1000 / $v2) / (1 + $v3)", [per, t60, dmp], 650, 260)
    # excitation: the breath bow (band-passed noise), stronger as you blow harder
    nz = e.obj("noise~", 850, 300)
    bow = ex(e, "($v1 * 0.5 + $v1 * $v1 * 0.5) * 0.03", [eb], 1000, 330)
    exc = chain(e, mul(e, nz, bow, 1000, 360), ["bp~ 800 1"], 1000, 385)
    pos = ex(e, "$v1 * (0.1 + $v2 * 0.12)", [per, p3], 450, 290)
    # the string, in 16-sample blocks so short (high) delays work
    s = Canvas("string", w=700, h=450)
    s.comment("waveguide in 16-sample blocks: delay -> damping -> dispersion -> gain -> + excitation", 20, 5)
    i_dl, i_g, i_d, i_a, i_ex, i_pos = (s.obj("inlet~", 20 + k * 100, 30) for k in range(6))
    s.obj("block~ 16", 620, 30)
    rd = s.obj("vd~ $0-str", 20, 80)
    s.c(i_dl, 0, rd, 0)
    nd = s.obj("*~ -1", 220, 60)
    s.c(i_d, 0, nd, 0)
    rz = s.obj("rzero~", 20, 110)
    s.c(rd, 0, rz, 0)
    s.c(nd, 0, rz, 1)
    rr = s.obj("rzero_rev~", 20, 140)
    s.c(rz, 0, rr, 0)
    s.c(i_a, 0, rr, 1)
    rp = s.obj("rpole~", 20, 170)
    s.c(rr, 0, rp, 0)
    s.c(i_a, 0, rp, 1)
    gm = s.obj("*~", 20, 200)
    s.c(rp, 0, gm, 0)
    s.c(i_g, 0, gm, 1)
    sm = s.obj("+~", 20, 230)
    s.c(gm, 0, sm, 0)
    s.c(i_ex, 0, sm, 1)
    s.c(sm, 0, s.obj("delwrite~ $0-str 120", 20, 260), 0)
    t1 = s.obj("delread~ $0-str 0.4", 300, 300)
    t2 = chain(s, i_pos, ["+~ 0.4", "vd~ $0-str", "*~ 0.7"], 520, 250)
    o = s.obj("-~", 300, 360)
    s.c(t1, 0, o, 0)
    s.c(t2, 0, o, 1)
    s.c(o, 0, s.obj("outlet~", 300, 400), 0)
    st = e.sub(s, 20, 480)
    for k, src in enumerate((dl, g, dmp, disp, exc, pos)):
        e.c(src, 0, st, k)
    # amp: volume pedal (breath), a little drive with breath
    drv = ex(e, "1.2 + $v1 * 1.5", [eb], 300, 520)
    amp = mul(e, mul(e, st, env, 20, 520), drv, 20, 545)
    sat = softclip(e, chain(e, amp, ["hip~ 40"], 20, 570), 20, 600)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 600), mul(e, r(e, "eng-body~", 500, 600), env, 500, 625), 400, 650)
    mix = add(e, sat, chain(e, body, ["*~ 0.4"], 400, 675), 20, 720)
    e.c(chain(e, mix, ["*~ 3.3"], 20, 745), 0, e.obj("outlet~", 20, 790), 0)
    e.save(path)


def lyra(path):
    """LIRA-8 style: a pair of cross-modulating triangle oscillators (after LIRA-8 by Miguel Moreno, BSD)"""
    e, pl, env, tb = frame("Lyra - after LIRA-8 (Miguel Moreno). Two triangle oscillators modulate each other. "
                           "Breath: deeper cross-mod, sharper waves, wider beating, more drive. Knobs: Mod, Sharp, Detune, Drive")
    p1, p2, p3, p4, bamt = (r(e, n, 650 + i * 90, 30) for i, n in
                            enumerate(("$1-p1~", "$1-p2~", "$1-p3~", "$1-p4~", "eng-bamt~")))
    es = chain(e, env, ["lop~ 6"], 300, 80)            # Lyra-like soft swell
    eb = mul(e, es, bamt, 650, 80)
    # slow random drift per voice (the original's vibrato source)
    drift = mul(e, chain(e, e.obj("noise~", 450, 80), ["lop~ 0.5", "*~ 8"], 450, 105),
                chain(e, eb, ["*~ 0.06", "+~ 0.02"], 550, 105), 450, 160)
    f = pitch_to_freq(e, pl, drift, 20, 80)
    det = ex(e, "1 + $v1 * $v1 * 0.012 + $v2 * 0.004", [p3, eb], 250, 180)
    fb = mul(e, f, det, 250, 205)
    m = ex(e, "$v1 * $v1 * 1.4 + $v2 * 0.9", [p1, eb], 400, 180)      # cross-mod index
    # phase modulation each way (keeps the pitch steady); B hears A from the previous block
    aprev = e.obj("delread~ $0-a 0", 400, 230)
    phb = chain(e, fb, ["phasor~"], 250, 260)
    triB = ex(e, "4 * abs(fmod($v1 + $v2 * $v3 * 0.18 + 4, 1) - 0.5) - 1", [phb, m, aprev], 250, 310)
    pha = chain(e, f, ["phasor~"], 20, 340)
    triA = ex(e, "4 * abs(fmod($v1 + $v2 * $v3 * 0.18 + 4, 1) - 0.5) - 1", [pha, m, triB], 20, 390)
    e.c(triA, 0, e.obj("delwrite~ $0-a 20", 150, 420), 0)
    # sharpness: push the triangles towards squares
    sh = ex(e, "min(1 + $v1 * 5 + $v2 * 2, 1 + 2500 / $v3)", [p2, eb, f], 400, 390)
    sA = chain(e, mul(e, triA, sh, 20, 420), ["clip~ -1 1"], 20, 445)
    sB = chain(e, mul(e, triB, sh, 250, 420), ["clip~ -1 1"], 250, 445)
    mix = chain(e, add(e, sA, sB, 20, 475), ["*~ 0.5"], 20, 500)
    drv = ex(e, "min(1 + $v1 * 5 + $v2 * 2.5, 1 + 3000 / $v3)", [p4, eb, f], 400, 500)
    sat = softclip(e, mul(e, mix, drv, 20, 525), 20, 550)
    nrm = ex(e, "1 / sqrt($v1)", [drv], 400, 600)
    out = chain(e, mul(e, sat, nrm, 20, 680), ["hip~ 25"], 20, 705)
    body = mul(e, chain(e, f, ["*~ 0.5", "osc~"], 400, 650), r(e, "eng-body~", 500, 650), 400, 700)
    mix2 = add(e, out, body, 20, 735)
    finish(e, mix2, es, 0.73, 20, 765, path)


def bsaw(path):
    bs = Canvas(w=700, h=450)
    bs.comment("Band-limited saw. Left: frequency (signal). Right: sr / (2.5 * freq) as a signal.", 20, 5)
    b_f, b_n = bs.obj("inlet~", 20, 30), bs.obj("inlet~", 300, 30)
    ph = chain(bs, b_f, ["phasor~"], 20, 60)
    naive = chain(bs, ph, ["-~ 0.5"], 20, 90)
    u = chain(bs, ph, ["+~ 0.5", "wrap~", "-~ 0.5"], 150, 90)
    st = chain(bs, u, ["*~ 1e+06", "clip~ -0.5 0.5"], 150, 170)
    w = chain(bs, mul(bs, u, b_n, 300, 170), ["clip~ -0.5 0.5", "*~ 0.5", "-~ 0.25", "cos~", "*~ 0.5"], 300, 195)
    a2 = bs.obj("-~", 20, 360)
    bs.c(add(bs, naive, st, 20, 330), 0, a2, 0)
    bs.c(w, 0, a2, 1)
    bs.c(a2, 0, bs.obj("outlet~", 20, 400), 0)
    bs.save(path)


def feral(path):
    """Feral - built from scratch (no parts shared with the other engines): a capacitor-charge oscillator,
    a hard-synced slave, a vactrol low-pass gate, a breath-puff detector and an asymmetric diode clipper.
    Native signal objects only (expr~ is slow on the Organelle)."""
    e = Canvas(w=1400, h=1100)
    e.comment("Feral - raw, unstable, made to be played with breath. A capacitor-charge oscillator and a hard-synced "
              "slave whose ratio breath sweeps, through a vactrol low-pass gate (opens fast, closes slow). "
              "Fast breath changes (puffs) kick the sync, crackle and snarl. Knobs: Sync, Snarl, Tone, Tail", 20, 5)
    ip, il, it = e.obj("inlet", 20, 40), e.obj("inlet", 300, 40), e.obj("inlet", 500, 40)
    pl = e.obj("line~", 20, 65)
    e.c(ip, 0, pl, 0)
    lv = e.obj("line~", 300, 65)
    e.c(il, 0, lv, 0)
    tb = e.obj("line~", 500, 65)
    e.c(it, 0, tb, 0)
    k1, k2, k3, bamt = (e.obj(f"r~ {n}", 700 + i * 90, 40) for i, n in
                        enumerate(("$1-p1~", "$1-p2~", "$1-p3~", "eng-bamt~")))
    SR = 44100
    # Tail knob (control rate): vactrol release coefficient, and puff sensitivity
    k4 = e.obj("r $1-p4", 1100, 40)
    tc = chain(e, k4, [f"expr exp(-1 / ((0.03 + $f1 * $f1 * 0.6) * {SR}))", "t f f"], 1100, 65)
    tg = chain(e, tc, ["expr 1 - $f1"], 1200, 115, outlet=0)
    # puff: how fast breath is rising (differentiator, rectified, held ~30 ms)
    dv = chain(e, lv, ["rzero~ 1", "clip~ 0 1", "*~ 500"], 300, 95)
    pf = chain(e, dv, ["rpole~ 0.9993", "*~ 0.0007", "clip~ 0 1"], 300, 170)
    puff = pf
    # breath, scaled by Breath>Tone
    br = mul(e, lv, chain(e, bamt, ["*~ 0.65", "+~ 0.35"], 420, 95), 300, 245)
    # wander: sample-and-hold random steps, smoothed
    sh = e.obj("samphold~", 900, 120)
    e.c(e.obj("noise~", 900, 95), 0, sh, 0)
    e.c(e.obj("phasor~ 2.3", 980, 95), 0, sh, 1)
    wd = chain(e, sh, ["*~ 0.0003", "rpole~ 0.9997", "*~ 0.12"], 900, 145)
    # pitch (MIDI) -> Hz: wander, puffs push sharp, host vibrato
    m = add(e, add(e, pl, e.obj("r~ eng-vib", 120, 95), 20, 120), add(e, wd, chain(e, puff, ["*~ 0.35"], 200, 200), 200, 225), 20, 250)
    hz = chain(e, m, ["mtof~", "clip~ 1 6000"], 20, 275)
    ph = e.obj("phasor~", 20, 325)
    e.c(hz, 0, ph, 0)
    dt = chain(e, hz, [f"*~ {1 / SR:.9f}"], 120, 325)
    # A: capacitor-charge curve: a straight ramp bending into a charging curve (sin quarter) as breath rises,
    # with poly-BLEP at the reset
    cq = chain(e, ph, ["*~ 0.25", "-~ 0.25", "cos~"], 220, 350)
    cm = chain(e, mul(e, br, br, 330, 350), ["clip~ 0 1"], 330, 375)
    nd = e.obj("-~", 220, 400)                            # ramp -> curve by cm
    e.c(cq, 0, nd, 0)
    e.c(ph, 0, nd, 1)
    naive = chain(e, add(e, ph, mul(e, nd, cm, 220, 425), 20, 450), ["*~ 2", "-~ 1"], 20, 475)
    # poly-BLEP at the reset, from two clamped ramps: (1 - (1 - t)/dt)^2 - (1 - t/dt)^2
    q1 = e.obj("/~", 120, 400)
    e.c(ph, 0, q1, 0)
    e.c(dt, 0, q1, 1)
    ra = chain(e, q1, ["*~ -1", "+~ 1", "clip~ 0 1"], 120, 425)
    q2 = e.obj("/~", 170, 400)
    e.c(chain(e, ph, ["*~ -1", "+~ 1"], 170, 375), 0, q2, 0)
    e.c(dt, 0, q2, 1)
    rb = chain(e, q2, ["*~ -1", "+~ 1", "clip~ 0 1"], 170, 425)
    blep = e.obj("-~", 120, 500)
    e.c(mul(e, rb, rb, 170, 475), 0, blep, 0)
    e.c(mul(e, ra, ra, 120, 475), 0, blep, 1)
    capo = e.obj("-~", 20, 525)
    e.c(naive, 0, capo, 0)
    e.c(blep, 0, capo, 1)
    # B: hard-synced slave: wrap(phase * ratio), ratio swept by breath and puffs, capped below 7 kHz
    r1 = add(e, chain(e, k1, ["*~ 3", "+~ 1"], 450, 300), mul(e, mul(e, br, k1, 550, 300), e.obj("sig~ 5", 650, 275), 550, 325), 450, 350)
    rr = add(e, r1, chain(e, puff, ["*~ 2"], 650, 350), 450, 375)
    cap = e.obj("/~", 600, 400)
    e.c(e.obj("sig~ 7000", 600, 375), 0, cap, 0)
    e.c(hz, 0, cap, 1)
    rat = e.obj("min~", 450, 425)
    e.c(rr, 0, rat, 0)
    e.c(cap, 0, rat, 1)
    syn = chain(e, mul(e, ph, rat, 450, 450), ["wrap~", "*~ 2", "-~ 1"], 450, 475)
    # half-rate square sub, slightly rounded
    sq = chain(e, chain(e, hz, ["*~ 0.5", "phasor~"], 650, 450), ["-~ 0.5", "*~ -1e+06", "clip~ -1 1", "*~ 0.15", "rpole~ 0.85"], 650, 500)
    # mix: capo * (1 - 0.8 Sync) + sync * 0.9 Sync + sub * (0.25 + 0.8 Body)
    mix = add(e, add(e, mul(e, capo, chain(e, k1, ["*~ -0.8", "+~ 1"], 120, 625), 20, 650),
                     mul(e, syn, chain(e, k1, ["*~ 0.9"], 450, 625), 450, 650), 20, 675),
              mul(e, sq, chain(e, e.obj("r~ eng-body~", 760, 600), ["*~ 0.8", "+~ 0.25"], 760, 625), 650, 650), 20, 700)
    # crackle: sparse clicks while puffing (noise above a threshold that drops with the puff), a little breath hiss
    nz = e.obj("noise~", 900, 600)
    hit = chain(e, add(e, nz, chain(e, puff, ["*~ 0.06", "-~ 0.985"], 1000, 625), 900, 650), ["*~ 1e+06", "clip~ 0 1"], 900, 675)
    crk = add(e, mul(e, hit, chain(e, puff, ["*~ 1.2"], 1000, 700), 900, 725), mul(e, mul(e, nz, lv, 1100, 650), e.obj("sig~ 0.08", 1150, 675), 1100, 700), 900, 750)
    pre = add(e, mix, crk, 20, 780)
    # asymmetric diode clipper (even harmonics): y / (1 + 1.4|y| - 0.4y)  =  y/(1+y) above 0, y/(1+1.8|y|) below
    drv = add(e, add(e, chain(e, mul(e, k2, k2, 220, 780), ["*~ 7", "+~ 1"], 220, 805), chain(e, br, ["*~ 2"], 320, 805), 220, 855),
              chain(e, puff, ["*~ 5"], 420, 805), 220, 880)
    y = mul(e, pre, drv, 20, 905)
    den = add(e, chain(e, y, ["abs~", "*~ 1.4", "+~ 1"], 120, 930), chain(e, y, ["*~ -0.4"], 220, 930), 120, 980)
    dio = e.obj("/~", 20, 1005)
    e.c(y, 0, dio, 0)
    e.c(den, 0, dio, 1)
    # vactrol: opens with breath at once, closes with a slow tail
    tl = e.obj("*~ 0", 450, 810)
    e.c(lv, 0, tl, 0)
    e.c(tg, 0, tl, 1)
    tr = e.obj("rpole~", 450, 835)
    e.c(tl, 0, tr, 0)
    e.c(tc, 1, tr, 1)
    vac = e.obj("max~", 300, 885)
    e.c(lv, 0, vac, 0)
    e.c(chain(e, tr, ["*~ 0.92"], 450, 860), 0, vac, 1)
    vg = chain(e, add(e, vac, chain(e, puff, ["*~ 0.3"], 400, 885), 300, 910), ["clip~ 0 1"], 300, 935)
    # gate filter: two one-poles; cutoff = 70 Hz * 2^(gate*6.2 + Tone*2.4 + timbre) via mtof~;
    # coefficient a = 1 - w (w = 2 pi fc / sr, kept below 0.9)
    sm = add(e, add(e, chain(e, vg, ["*~ 74.4"], 300, 960), chain(e, k3, ["*~ 28.8"], 400, 960), 300, 985),
             chain(e, tb, ["*~ 16.8"], 500, 960), 300, 1010)
    w = chain(e, sm, ["+~ 16.9", "mtof~", f"*~ {6.2832 / SR:.8f}", "clip~ 0.002 0.9"], 300, 1035)
    a_ = chain(e, w, ["*~ -1", "+~ 1"], 450, 1135)
    st = dio
    for i in range(2):
        g = mul(e, st, w, 20 + i * 120, 860 + i * 60)
        rp = e.obj("rpole~", 20 + i * 120, 885 + i * 60)
        e.c(g, 0, rp, 0)
        e.c(a_, 0, rp, 1)
        st = rp
    # VCA side of the gate (gate^1.5), DC blocker, out
    out = mul(e, st, mul(e, vg, chain(e, vg, ["sqrt~"], 260, 975), 200, 1000), 20, 1000)
    e.c(chain(e, out, ["rzero~ 1", "rpole~ 0.995", "*~ 0.6"], 20, 1025), 0, e.obj("outlet~", 20, 1110), 0)
    e.save(path)

ENGINES = {
    "volt": (volt, "Fold Grit Detune Tone", "0.3 0.2 0.35 0.55"),
    "halo": (halo, "Shimmer Resonance Air Bloom", "0.5 0.5 0.35 0.5"),
    "under": (under, "Subs Drive Tone Octave", "0.5 0.3 0.4 0.4"),
    "velvet": (velvet, "Cutoff Spread Swell Warmth", "0.5 0.5 0.5 0.4"),
    "steel": (steel, "Tone Sustain Steel Attack", "0.55 0.5 0.35 0.3"),
    "lyra": (lyra, "Mod Sharp Detune Drive", "0.3 0.25 0.35 0.3"),
    "feral": (feral, "Sync Snarl Tone Tail", "0.35 0.4 0.45 0.3"),
}


def build(out_dir):
    ed = os.path.join(out_dir, "engines")
    os.makedirs(os.path.join(ed, "lib"), exist_ok=True)
    bsaw(os.path.join(ed, "lib", "bsaw.pd"))
    for name, (fn, names, defaults) in ENGINES.items():
        fn(os.path.join(ed, name + ".pd"))
        with open(os.path.join(ed, name + ".txt"), "w") as fh:
            fh.write(f"{names};\n{defaults};\n")
    with open(os.path.join(ed, "README.txt"), "w") as fh:
        fh.write(CONTRACT)

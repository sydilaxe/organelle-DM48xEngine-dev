"""Audio looper: up to 6 stacked stereo layers, so sounds from different engines can be layered.

Keys (high octave):  A tap = record > play > overdub > play ...   A held 1 s = clear
                     A# = undo (removes the newest layer)          B = stop / start
Hold A + knob:  1 speed & direction (tape style: centre normal, left reverse)  2 pitch -12..+12 (speed unchanged)
                3 loop level  4 loop decay (left = off; turning right, older layers fade faster)
Hold B + knob:  Pre (records the synth before the effects; the loop then plays through delay/reverb) / Post
If a MIDI loop is playing, recording waits for the MIDI loop start and lasts exactly one MIDI cycle.

Layers: engaL<j> / engaR<j>. One writer (two tabwrite~) records the newest layer. A layer is always written for at
least one whole pass (after the overdub ends it keeps writing silence until the pass is complete), so it never keeps
leftovers from an earlier, undone take.
States (engastate): 0 empty, 1 armed (waits for the MIDI loop start), 2 REC, 3 PLAY, 4 DUB, 5 STOP.
"""
import os
from pdgen import Canvas
from sec_core import chain, to, msg_to, setv

NL = 6
MAXSEC = 45
MAXA = 44100 * MAXSEC
RECOV = 1024          # overview of the first take, one value per 50 ms
ZCH = 4096            # background zeroing: samples per layer side per millisecond


def arrays():
    out = []
    for j in range(NL):
        out += [(f"engaL{j}", MAXA), (f"engaR{j}", MAXA), (f"engov{j}", 128)]
    out += [("engzero", ZCH), ("engadirty", NL), ("engaon", NL), ("engag", NL), ("engaage", NL), ("engrecov", RECOV), ("engscope", 1024), ("engscy", 128)]
    return out


VALUES = ("engastate engalen engalenms engaspd engapitch engalvl engafb engapost engasr engamaxms engaw engak "
          "engatail engasync engacnt engaph engview engatop engarecn engapk engawA engawB engazp engazl").split()


def mul2(c, a, b, x, y):
    o = c.obj("*~", x, y)
    c.c(a, 0, o, 0)
    c.c(b, 0, o, 1)
    return o


def add2(c, a, b, x, y):
    o = c.obj("+~", x, y)
    c.c(a, 0, o, 0)
    c.c(b, 0, o, 1)
    return o


def smooth_msg(c, recv, ms, x, y):
    """[r recv] -> [$1 ms( -> [line~]"""
    m = msg_to(c, c.obj(f"r {recv}", x, y), f"$1 {ms}", x, y + 25)
    return to(c, m, "line~", x, y + 50)


def send(c, src, text, name, x, y, outlet=0):
    """src -> [text( -> [s name]"""
    return to(c, msg_to(c, src, text, x, y, outlet), f"s {name}", x, y + 25)


def tabset(c, src, expr_text, table, x, y, outlet=0):
    """src -> [expr index; value] -> table[index] = value"""
    ex = to(c, src, f"expr {expr_text}", x, y, outlet)
    val = c.obj("f", x + 100, y + 50)
    c.c(ex, 1, val, 1)
    t = to(c, ex, "t b f", x, y + 25)
    tw = c.obj(f"tabwrite {table}", x, y + 75)
    c.c(t, 1, tw, 1)
    c.c(t, 0, val, 0)
    c.c(val, 0, tw, 0)
    return ex


def dsp():
    """signal part, switched off while there is no audio loop"""
    a = Canvas("aloop-dsp", w=2000, h=1300)
    a.comment("Audio looper signals. Off (switch~) while the looper is empty.", 20, 5)
    chain(a, a.obj("r $0-adsp", 1800, 10), ["switch~"], 1800, 35)
    post = smooth_msg(a, "eng-apost", 30, 20, 30)
    dry = a.obj("r~ eng-tap-pre", 150, 30)
    if os.environ.get("DBG_ALOOP"):                      # debug: record a sample counter instead of sound
        dry = chain(a, a.obj("sig~ 1", 150, 30), ["rpole~ 1"], 150, 30)
    pL, pR = a.obj("r~ eng-tap-postL", 270, 30), a.obj("r~ eng-tap-postR", 400, 30)
    ins = []
    for p, x in ((pL, 150), (pR, 330)):                 # dry + (post - dry) * post   (native objects: cheap)
        d = a.obj("-~", x, 85)
        a.c(p, 0, d, 0)
        a.c(dry, 0, d, 1)
        ins.append(add2(a, dry, mul2(a, d, post, x, 110), x, 135))
    inL, inR = ins
    # playhead
    ph = a.obj("phasor~", 600, 110)
    a.c(a.obj("r $0-afreq", 600, 80), 0, ph, 0)
    a.c(a.obj("r $0-aphase", 680, 80), 0, ph, 1)
    # each layer has its own length and direction (it was recorded at some loop speed):
    # read index = phase x A + B, with A = +-(samples per loop pass), B = 0 (forward) or the length (reverse)
    # Each layer is its own subpatch that only runs while its gain is not 0 (switched off 100 ms after a fade to 0),
    # so unused layers cost nothing. A switched-off subpatch's outlet~ gives zeros (and the gain is 0 by then).
    # (Not throw~/catch~: Pd runs a catch~ before the layers, so the loop would come out a block late.)
    sums = [None, None]
    for j in range(NL):
        ly = Canvas(f"layer{j}", w=700, h=400)
        ly.comment("one layer: runs only while its gain is not 0", 20, 5)
        lin = ly.obj("inlet~", 20, 30)
        ia = ly.obj("*~ 0", 20, 60)
        ly.c(lin, 0, ia, 0)
        ly.c(ly.obj(f"r $0-alayA{j}", 80, 35), 0, ia, 1)
        ib = ly.obj("+~ 0", 20, 85)
        ly.c(ia, 0, ib, 0)
        ly.c(ly.obj(f"r $0-alayB{j}", 80, 60), 0, ib, 1)
        gt = chain(ly, ly.obj(f"r $0-ag{j}", 300, 30), ["t a a"], 300, 55)
        g = to(ly, gt, "line~", 300, 85)
        sw = ly.obj("switch~", 450, 205)
        gz = chain(ly, gt, ["unpack 0 0", "sel 0"], 450, 80, outlet=1)
        off = to(ly, gz, "delay 100", 450, 130)
        ly.c(msg_to(ly, off, "0", 450, 155), 0, sw, 0)
        on = to(ly, gz, "t b b", 550, 130, outlet=1)
        ly.c(msg_to(ly, on, "stop", 600, 155, outlet=1), 0, off, 0)
        ly.c(msg_to(ly, on, "1", 550, 155), 0, sw, 0)
        for side, x in (("L", 20), ("R", 160)):
            rd = to(ly, ib, f"tabread4~ enga{side}{j}", x, 120)
            to(ly, mul2(ly, rd, g, x, 150), "outlet~", x, 175)
        lb = a.sub(ly, 20 + j * 160, 220)
        a.c(ph, 0, lb, 0)
        for k in (0, 1):
            sums[k] = (lb, k) if sums[k] is None else add2(a, sums[k], (lb, k), 20 + j * 160 + k * 60, 260)
    sumL, sumR = sums
    widx = a.obj("*~ 0", 1400, 140)
    a.c(ph, 0, widx, 0)
    a.c(a.obj("r $0-awA", 1450, 115), 0, widx, 1)
    widx2 = a.obj("+~ 0", 1400, 165)
    a.c(widx, 0, widx2, 0)
    a.c(a.obj("r $0-awB", 1450, 140), 0, widx2, 1)
    sn = a.obj("snapshot~", 750, 140)
    a.c(ph, 0, sn, 0)
    a.c(a.obj("r $0-asnap", 830, 115), 0, sn, 0)
    to(a, sn, "v engaph", 750, 165)
    # pitch shifter: two crossfaded delay taps per side, in its own subpatch that only runs while the pitch is
    # not 0 (switched off 100 ms after the bypass fade). Speed and window glide, so turning the knob is smooth.
    ps = Canvas("pitch-shift", w=1200, h=700)
    ps.comment("Runs only while the loop pitch is not 0. Out via throw~ (silent when switched off).", 20, 5)
    sw = ps.obj("switch~", 900, 180)
    sl = chain(ps, ps.obj("r $0-apson", 900, 30), ["sel 0"], 900, 55)
    psd = to(ps, sl, "delay 100", 900, 80)
    ps.c(msg_to(ps, psd, "0", 900, 105), 0, sw, 0)
    on = to(ps, sl, "t b b", 1000, 80, outlet=1)
    ps.c(msg_to(ps, on, "stop", 1060, 105, outlet=1), 0, psd, 0)
    ps.c(msg_to(ps, on, "1", 1000, 105), 0, sw, 0)
    rate = chain(ps, msg_to(ps, ps.obj("r $0-apsrate", 20, 30), "$1 30", 20, 55), ["line~"], 20, 80)
    win = chain(ps, msg_to(ps, ps.obj("r $0-apswin", 200, 30), "$1 60", 200, 55), ["line~"], 200, 80)
    pph = to(ps, rate, "phasor~", 20, 105)
    # the two taps' delay times and windows are the same for both sides
    taps = []
    for k, dx in ((0, 0), (0.5, 250)):
        p = to(ps, pph, f"+~ {k}", 20 + dx, 200)
        w = to(ps, p, "wrap~", 20 + dx, 225)
        d = mul2(ps, w, win, 20 + dx, 250)
        wnd = chain(ps, w, ["-~ 0.5", "*~ 0.5", "cos~"], 20 + dx + 120, 250)
        taps.append((d, wnd))
    for side, x in (("L", 20), ("R", 600)):
        src = ps.obj(f"r~ $0-apin{side}", x, 140)
        to(ps, src, f"delwrite~ $0-aps{side} 400", x, 165)
        outs = []
        for (d, wnd), dx in zip(taps, (0, 250)):
            rd = to(ps, d, f"vd~ $0-aps{side}", x + dx, 330)
            outs.append(mul2(ps, rd, wnd, x + dx, 360))
        to(ps, add2(ps, outs[0], outs[1], x, 390), f"throw~ $0-apout{side}", x, 415)
    a.sub(ps, 1300, 300)
    byp = smooth_msg(a, "$0-apson", 40, 1600, 330)
    shifted = []
    for side, src, x in (("L", sumL, 20), ("R", sumR, 650)):
        to(a, src, f"s~ $0-apin{side}", x, 360)
        sh = a.obj(f"catch~ $0-apout{side}", x + 150, 590)
        d = a.obj("-~", x + 150, 615)                   # src + (shifted - src) * bypass
        a.c(sh, 0, d, 0)
        a.c(src, 0, d, 1)
        shifted.append(add2(a, src, mul2(a, d, byp, x + 150, 640), x, 665))
    lvl = smooth_msg(a, "$0-alvlsig", 50, 1300, 620)
    oL, oR = mul2(a, shifted[0], lvl, 20, 680), mul2(a, shifted[1], lvl, 650, 680)
    # routing: Pre -> mono into the effects input; Post -> stereo after the effects
    pre = mul2(a, to(a, add2(a, oL, oR, 20, 695), "*~ 0.5", 20, 710), chain(a, post, ["*~ -1", "+~ 1"], 120, 695), 20, 730)
    # throw~ (not s~): when the looper's DSP is switched off a throw~ adds nothing, an s~ would repeat its last block
    to(a, pre, "throw~ eng-aret-pre", 20, 745)
    for o, side, x in ((oL, "L", 300), (oR, "R", 450)):
        to(a, mul2(a, o, post, x, 720), f"throw~ eng-aret-{side}", x, 745)
    # writer: newest layer = input x gate + what is already there x k (k = 0 during the first pass)
    gate = smooth_msg(a, "$0-agatesig", 8, 1100, 800)
    ksig = chain(a, a.obj("r $0-aksig", 1250, 800), ["sig~"], 1250, 825)
    for side, src, x in (("L", inL, 20), ("R", inR, 500)):
        # the layer's old sample at exactly the write position (rounded, no interpolation: an interpolating read
        # would blend in the neighbour the writer has just overwritten)
        rd = to(a, to(a, widx2, "+~ 0.5", x + 200, 860), f"tabread~ enga{side}0", x + 200, 880)
        a.c(a.obj(f"r $0-awset{side}", x + 200, 855), 0, rd, 0)
        wr = add2(a, mul2(a, src, gate, x, 900), mul2(a, rd, ksig, x + 100, 900), x, 920)   # in * gate + old * k
        tw = a.obj(f"tabwrite~ enga{side}0", x, 950)
        a.c(wr, 0, tw, 0)
        a.c(a.obj(f"r $0-awset{side}", x + 120, 925), 0, tw, 0)
        a.c(a.obj("r $0-awcmd", x + 250, 925), 0, tw, 0)
    # input level for the waveform overview
    lv = chain(a, add2(a, inL, inR, 1100, 1000), ["env~ 2048 1024"], 1100, 1030)
    to(a, lv, "v engapk", 1100, 1080)
    return a


def control():
    a = Canvas("aloop-control", w=2600, h=3600)
    a.comment("Audio looper control. See sec_aloop.py.", 20, 5)
    stat = a.obj("s $0-astat", 20, 3550)
    toast = a.obj("s $0-toast", 200, 3550)

    # ---------- start-up
    lbt = chain(a, a.obj("loadbang", 20, 30), ["t b b b"], 20, 55)
    sr = chain(a, lbt, ["samplerate~", "t f f"], 20, 80, outlet=2)
    to(a, sr, "v engasr", 120, 105, outlet=1)
    to(a, to(a, sr, f"expr min({MAXA - 2048}, $f1 * {MAXSEC}) / $f1 * 1000", 20, 105), "v engamaxms", 20, 130)
    for i, (nm, v) in enumerate((("engaspd", 1), ("engafb", 1), ("engalvl", 0.8), ("engapost", 0), ("engapitch", 0),
                                 ("engview", 0))):
        setv(a, lbt, nm, v, 250 + i * 60, 80, outlet=1)
    for i, (nm, v) in enumerate((("eng-apost", 0), ("$0-alvlsig", 0), ("$0-apson", 0), ("$0-agatesig", 0),
                                 ("$0-aksig", 0), ("$0-afreq", 0), ("$0-adsp", 0))):
        send(a, lbt, str(v), nm, 650 + i * 70, 80, outlet=0)

    # ---------- layer gain: [s $0-asetgain] "gain layer"
    sg = chain(a, a.obj("r $0-asetgain", 20, 200), ["t a a"], 20, 225)
    sgu = to(a, sg, "unpack 0 0", 150, 250, outlet=1)
    tw = a.obj("tabwrite engag", 150, 300)
    a.c(sgu, 1, tw, 1)
    a.c(sgu, 0, tw, 0)
    rt = to(a, msg_to(a, sg, "$2 $1", 20, 250), "route " + " ".join(str(j) for j in range(NL)), 20, 275)
    for j in range(NL):
        send(a, rt, "$1 60", f"$0-ag{j}", 20 + j * 60, 300, outlet=j)

    # ---------- layer mapping: [s $0-alayset] "j A B" (also the writer's, when j is the write layer)
    ls_ = chain(a, a.obj("r $0-alayset", 20, 350), ["t a a"], 20, 375)
    lrt = to(a, ls_, "route " + " ".join(str(j) for j in range(NL)), 20, 400)
    for j in range(NL):
        lu = to(a, lrt, "unpack 0 0", 20 + j * 70, 425, outlet=j)
        to(a, lu, f"s $0-alayB{j}", 60 + j * 70, 450, outlet=1)
        to(a, lu, f"s $0-alayA{j}", 20 + j * 70, 475)
    lw = a.obj("spigot", 500, 400)
    a.c(to(a, ls_, "expr $f1 == engaw", 560, 400, outlet=1), 0, lw, 1)
    a.c(ls_, 0, lw, 0)
    lwu = to(a, lw, "unpack 0 0 0", 500, 425)
    tB = to(a, lwu, "t f f", 560, 450, outlet=2)
    to(a, tB, "v engawB", 620, 475, outlet=1)
    to(a, tB, "s $0-awB", 560, 475)
    tA = to(a, lwu, "t f f", 500, 450, outlet=1)
    to(a, tA, "v engawA", 450, 500, outlet=1)
    to(a, tA, "s $0-awA", 500, 475)
    # the first take: its length is known when it ends ([s $0-alen])
    bl = chain(a, a.obj("r $0-alen", 750, 350), ["t b", "expr engaw; engalen; 0"], 750, 375)
    blp = a.obj("pack 0 0 0", 750, 450)
    for k in (2, 1, 0):
        a.c(bl, k, blp, k)
    to(a, blp, "s $0-alayset", 750, 475)

    # ---------- write layer: [s $0-awlayer] j
    wl = chain(a, a.obj("r $0-awlayer", 500, 200), ["t f f f"], 500, 225)
    to(a, wl, "v engaw", 650, 250, outlet=2)
    send(a, wl, "set engaL$1", "$0-awsetL", 500, 250, outlet=1)
    send(a, wl, "set engaR$1", "$0-awsetR", 600, 250, outlet=1)
    send(a, wl, "set engov$1", "$0-aovset", 700, 250, outlet=0)

    # ---------- find a free layer -> engaw (-1 if none): [s $0-afree]
    ff = chain(a, a.obj("r $0-afree", 900, 200), ["t b b b"], 900, 225)
    setv(a, ff, "engaw", -1, 1050, 250, outlet=2)
    fc = a.obj("f", 900, 300)
    a.c(msg_to(a, ff, "0", 1000, 275, outlet=1), 0, fc, 1)
    a.c(to(a, msg_to(a, ff, str(NL), 900, 250), "until", 900, 275), 0, fc, 0)
    a.c(to(a, fc, "+ 1", 950, 325), 0, fc, 1)
    fr = chain(a, fc, ["expr if((engaon[$f1] == 0) && (engaw < 0), $f1, -1)", "moses 0"], 900, 325)
    to(a, fr, "v engaw", 950, 375, outlet=1)

    # ---------- take layer engaw: on, newest, gain 1, writer points at it: [s $0-ause]
    ul = chain(a, a.obj("r $0-ause", 1300, 200), ["t b b b b"], 1300, 225)
    to(a, to(a, ul, "expr engaw", 1300, 250, outlet=3), "s $0-awlayer", 1300, 275)
    tabset(a, ul, "engaw; 1", "engaon", 1450, 250, outlet=2)
    to(a, to(a, ul, "expr engacnt + 1", 1650, 250, outlet=1), "v engacnt", 1650, 275)
    tabset(a, ul, "engaw; engacnt", "engaage", 1800, 250, outlet=0)
    ug = to(a, ul, "t b b b", 1300, 300, outlet=0)
    send(a, to(a, ug, "expr engaw", 1300, 325, outlet=0), "1 $1", "$0-asetgain", 1300, 350)
    um = to(a, ug, "expr engaw; if(engaspd > 0, 1, -1) * int(engalen / max(0.05, abs(engaspd))); "
                   "if(engaspd > 0, 0, 1) * int(engalen / max(0.05, abs(engaspd)))", 1400, 325, outlet=1)
    ump = a.obj("pack 0 0 0", 1400, 350)
    for k in (2, 1, 0):
        a.c(um, k, ump, k)
    to(a, ump, "s $0-alayset", 1400, 375)
    zd = chain(a, ug, ["expr if(engadirty[engaw], engaw, -1)", "moses 0"], 1650, 325, outlet=2)
    zt = to(a, zd, "t f f", 1700, 375, outlet=1)
    msg_to(a, zt, "; engaL$1 const 0; engaR$1 const 0", 1700, 400, outlet=1)
    tabset(a, zt, "$f1; 0", "engadirty", 1850, 400, outlet=0)

    # ---------- loop clock. The playhead (phasor~) runs freely; it is only reset when playback (re)starts.
    # The clock ticks ~3 ms after each wrap: the writer carries on across the loop seam (the few samples it wrote
    # past the end are copied to the start), older layers fade, and the next tick is scheduled from the real phase.
    nx = a.obj("delay", 600, 700)
    to(a, nx, "s $0-atick", 600, 725)
    a.c(msg_to(a, a.obj("r $0-awstop", 700, 675), "stop", 700, 700), 0, nx, 0)
    # start playback from the loop start: [s $0-aplay]
    ap = chain(a, a.obj("r $0-aplay", 20, 450), ["t b b"], 20, 475)
    send(a, ap, "0", "$0-aphase", 100, 500, outlet=1)
    a.c(chain(a, ap, ["expr if(engalen > 0, engalenms / max(0.05, abs(engaspd)) + 3, -1)", "moses 0"], 20, 500), 1, nx, 0)
    # schedule the next tick from the current phase: [s $0-anext]
    an = chain(a, a.obj("r $0-anext", 300, 450), ["t b b"], 300, 475)
    to(a, an, "s $0-asnap", 380, 500, outlet=1)
    a.c(chain(a, an, ["expr if((engalen > 0) && ((engastate == 3) || (engastate == 4)), "
                      "if(engaspd > 0, 1 - engaph, engaph) * engalenms / max(0.05, abs(engaspd)) + 3, -1)", "moses 0"],
              300, 500), 1, nx, 0)
    # tick
    tk = chain(a, a.obj("r $0-atick", 20, 560), ["t b b b b"], 20, 585)
    to(a, tk, "s $0-asnap", 20, 610, outlet=3)
    wsel = chain(a, tk, ["expr (engastate == 4) || engatail", "sel 1"], 150, 610, outlet=2)
    to(a, wsel, "s $0-aseam", 150, 660)
    # decay (like a tape looper's feedback): every on layer except the one being written is multiplied by engafb
    # each pass. The gain glides there over the whole pass, so the loop fades smoothly instead of stepping at the
    # seam. Below -60 dB a layer is gone: gain 0 (its DSP switches off) and its slot is free for a new overdub.
    fg = chain(a, tk, ["expr engafb < 0.999", "sel 1"], 350, 610, outlet=1)
    fu = to(a, msg_to(a, fg, str(NL), 350, 660), "until", 350, 685)
    fz = msg_to(a, fg, "0", 450, 660)
    fcn = a.obj("f", 350, 710)
    a.c(fz, 0, fcn, 1)
    a.c(fu, 0, fcn, 0)
    a.c(to(a, fcn, "+ 1", 400, 735), 0, fcn, 1)
    fx = to(a, fcn, "expr if(engaon[$f1] && !(($f1 == engaw) && ((engastate == 4) || engatail)), $f1, -1); "
                    "if(engag[$f1] * engafb < 0.001, 0, engag[$f1] * engafb); "
                    "max(60, engalenms / max(0.05, abs(engaspd)))", 350, 760)
    fpk = a.obj("pack 0 0 0", 350, 810)
    a.c(fx, 2, fpk, 2)
    a.c(fx, 1, fpk, 1)
    a.c(to(a, fx, "moses 0", 350, 785), 1, fpk, 0)
    to(a, fpk, "s $0-adecay", 350, 835)
    # [s $0-adecay] "layer gain ms"
    dg = chain(a, a.obj("r $0-adecay", 20, 870), ["t a a a"], 20, 895)
    tabset(a, dg, "$f1; $f2 + 0 * $f3", "engag", 250, 920, outlet=2)
    tabset(a, dg, "$f1; ($f2 > 0) + 0 * $f3", "engaon", 400, 920, outlet=1)
    drt = to(a, dg, "route " + " ".join(str(j) for j in range(NL)), 20, 920)
    for j in range(NL):
        to(a, drt, f"s $0-ag{j}", 20 + j * 40, 945, outlet=j)
    to(a, tk, "s $0-anext", 600, 610, outlet=0)
    # seam: copy what the writer wrote past the end (layer length lw, x samples) to the start, then write on from x
    sm = chain(a, a.obj("r $0-aseam", 1000, 560), ["expr int(engaph * engawA + engawB + 1); int(abs(engawA))"], 1000, 585)
    smt = to(a, sm, "t f f f", 1000, 610)
    send(a, smt, "start $1", "$0-awcmd", 1000, 635, outlet=0)
    cnt = a.obj("f", 1100, 685)
    a.c(msg_to(a, smt, "0", 1150, 660, outlet=2), 0, cnt, 1)
    a.c(to(a, to(a, smt, "clip 0 1024", 1050, 635, outlet=1), "until", 1050, 660), 0, cnt, 0)
    a.c(to(a, cnt, "+ 1", 1150, 710), 0, cnt, 1)
    ct = to(a, cnt, "t f f", 1100, 710)
    for side, x in (("L", 1100), ("R", 1300)):
        src = to(a, ct, "+ 0", x, 735, outlet=0)          # lw + i
        a.c(sm, 1, src, 1)                                # (the layer length lw arrives first, cold)
        rdt = to(a, src, f"tabread enga{side}0", x, 760)
        a.c(a.obj(f"r $0-awset{side}", x + 80, 735), 0, rdt, 0)
        wrt = a.obj(f"tabwrite enga{side}0", x, 800)
        a.c(a.obj(f"r $0-awset{side}", x + 80, 775), 0, wrt, 0)
        a.c(ct, 1, wrt, 1)                                # index i first
        a.c(rdt, 0, wrt, 0)
    # a MIDI loop cycle re-aligns a synced audio loop that has drifted (normal speed only)
    sy = chain(a, a.obj("r $0-cycle", 900, 450),
               ["expr engasync && ((engastate == 3) || (engastate == 4)) && (engaspd == 1) && (englspd == 1)", "sel 1"],
               900, 475)
    syt = to(a, sy, "t b b", 900, 500)
    to(a, syt, "s $0-asnap", 1000, 525, outlet=1)
    to(a, chain(a, syt, ["expr min(engaph, 1 - engaph) * engalenms > 5", "sel 1"], 900, 525), "s $0-aplay", 900, 575)

    # ---------- start writing a new layer at the playhead: [s $0-awbegin]
    wb = chain(a, a.obj("r $0-awbegin", 1300, 450), ["t b b b b b"], 1300, 475)
    setv(a, wb, "engak", 0, 1400, 500, outlet=4)
    send(a, wb, "0", "$0-aksig", 1450, 500, outlet=4)
    to(a, wb, "s $0-asnap", 1550, 500, outlet=3)
    st0 = to(a, wb, "expr int(engaph * engawA + engawB + 1) % max(1, int(abs(engawA)))", 1600, 525, outlet=2)
    send(a, st0, "start $1", "$0-awcmd", 1600, 550)
    p1 = a.obj("delay", 1300, 550)
    a.c(to(a, wb, "expr engalenms / max(0.05, abs(engaspd)) - 3", 1300, 525), 0, p1, 0)
    a.c(msg_to(a, a.obj("r $0-awcancel", 1400, 525), "stop", 1400, 550), 0, p1, 0)
    # first pass complete: from now on the layer adds to itself; a finishing tail ends here
    p1t = to(a, p1, "t b b b", 1300, 575)
    setv(a, p1t, "engak", 1, 1400, 600, outlet=2)
    send(a, p1t, "1", "$0-aksig", 1450, 600, outlet=1)
    to(a, chain(a, p1t, ["expr engatail", "sel 1"], 1300, 600), "s $0-awend", 1300, 650)
    # stop writing: [s $0-awend]
    we0 = chain(a, a.obj("r $0-awend", 1700, 425), ["t b b"], 1700, 440)
    dsel = chain(a, we0, ["expr (engak == 0) && (engaw >= 0)", "sel 1"], 1850, 440, outlet=1)
    tabset(a, dsel, "engaw; 1", "engadirty", 1850, 490)
    # Zero dirty layers that are off in the background, ZCH samples a millisecond (a whole layer in about
    # half a second), from 100 ms after (once a clear or undo has faded out). Zeroing a whole 45 s layer at once
    # takes ~3 ms on a PC, far longer on the Organelle: an audio dropout. A layer taken before it is done is
    # still zeroed at once when it is taken (see $0-ause).
    zgo = a.obj("delay 100", 2050, 490)
    a.c(dsel, 0, zgo, 0)
    zm = a.obj("metro 1", 2050, 540)
    a.c(msg_to(a, zgo, "bang", 2050, 515), 0, zm, 0)
    first = "-1"
    for j in reversed(range(NL)):
        first = f"if(engadirty[{j}] && (engaon[{j}] == 0), {j}, {first})"
    zd = chain(a, zm, [f"expr {first}", "moses 0"], 2050, 565)
    a.c(msg_to(a, zd, "stop", 2050, 615), 0, zm, 0)
    zt = to(a, zd, "t b b b f", 2150, 615, outlet=1)
    zl = to(a, zt, "expr $f1; if($f1 != engazl, 0, engazp)", 2350, 640, outlet=3)
    to(a, zl, "v engazp", 2450, 665, outlet=1)
    zlt = to(a, zl, "t f f f", 2350, 665)
    to(a, zlt, "v engazl", 2500, 690, outlet=2)
    asL, asR = a.obj("array set", 2150, 790), a.obj("array set", 2250, 790)
    a.c(msg_to(a, zlt, "symbol engaL$1", 2350, 715, outlet=1), 0, asL, 2)
    a.c(msg_to(a, zlt, "symbol engaR$1", 2450, 715, outlet=0), 0, asR, 2)
    zon = to(a, zt, "expr engazp", 2250, 690, outlet=2)
    a.c(zon, 0, asL, 1)
    a.c(zon, 0, asR, 1)
    zg = to(a, zt, "array get engzero", 2150, 740, outlet=1)
    a.c(zg, 0, asL, 0)
    a.c(zg, 0, asR, 0)
    zn = chain(a, zt, [f"expr engazp + {ZCH}", f"moses {MAXA}"], 2050, 690)
    to(a, zn, "v engazp", 2050, 740)
    zdone = to(a, zn, "t b b", 2100, 740, outlet=1)
    setv(a, zdone, "engazp", 0, 2100, 790, outlet=1)
    tabset(a, zdone, "engazl; 0", "engadirty", 2100, 815, outlet=0)
    we = to(a, we0, "t b b b", 1700, 475)
    setv(a, we, "engatail", 0, 1700, 500, outlet=2)
    send(a, we, "stop", "$0-awcmd", 1800, 500, outlet=1)
    send(a, we, "0", "$0-agatesig", 1900, 500, outlet=0)

    # ---------- waveform overview while writing (playhead bin = level), and for the first take by time
    ovm = a.obj("metro 50", 20, 950)
    a.c(a.obj("r $0-aovrun", 20, 925), 0, ovm, 0)
    ovt = to(a, ovm, "t b b", 20, 975)
    to(a, ovt, "s $0-asnap", 120, 1000, outlet=1)
    ovs = chain(a, ovt, ["expr engastate == 2", "sel 1 0"], 20, 1000)
    # first take: by time
    rv = to(a, ovs, "expr min(1, dbtorms(engapk) * 3); engarecn", 20, 1050)
    rvp = a.obj("pack 0 0", 20, 1100)
    a.c(rv, 1, rvp, 1)
    a.c(rv, 0, rvp, 0)
    rvt = to(a, rvp, "t a b", 20, 1125)
    to(a, to(a, rvt, "expr min(engarecn + 1, " + str(RECOV - 1) + ")", 120, 1150, outlet=1), "v engarecn", 120, 1175)
    rvu = to(a, rvt, "unpack 0 0", 20, 1150)
    rvw = a.obj("tabwrite engrecov", 20, 1200)
    a.c(rvu, 1, rvw, 1)       # index (unpack: right outlet first)
    a.c(rvu, 0, rvw, 0)       # then the value
    # overdubs: max of what is there (or 0 on the first pass) and the input level, at the playhead bin
    od = to(a, ovs, "expr int(min(127, max(0, engaph * 128))); min(1, dbtorms(engapk) * 3) * (engagatev > 0)", 300, 1050,
            outlet=1)
    odv = a.obj("f", 450, 1100)
    a.c(od, 1, odv, 1)
    odt = to(a, od, "t f b f", 300, 1075)
    otw = a.obj("tabwrite engov0", 300, 1200)
    a.c(a.obj("r $0-aovset", 450, 1175), 0, otw, 0)
    a.c(odt, 2, otw, 1)                      # index first
    mx = a.obj("expr max($f1 * engak, $f2)", 350, 1150)
    a.c(odt, 1, odv, 0)                      # then the new level (cold) ...
    a.c(odv, 0, mx, 1)
    old = to(a, odt, "tabread engov0", 350, 1100, outlet=0)   # ... then the old one (hot)
    a.c(a.obj("r $0-aovset", 450, 1075), 0, old, 0)
    a.c(old, 0, mx, 0)
    a.c(mx, 0, otw, 0)
    # gate value for the overview ([v] mirror of the input gate)
    to(a, a.obj("r $0-agatesig", 600, 1050), "v engagatev", 600, 1075)
    # first take -> 128 bins: [s $0-arecbins]
    rb = chain(a, a.obj("r $0-arecbins", 800, 950), ["t b b"], 800, 975)
    bc = a.obj("f", 800, 1025)
    a.c(msg_to(a, rb, "0", 900, 1000, outlet=1), 0, bc, 1)
    a.c(to(a, msg_to(a, rb, "128", 800, 1000, outlet=0), "until", 850, 1000), 0, bc, 0)
    a.c(to(a, bc, "+ 1", 850, 1050), 0, bc, 1)
    bx = to(a, bc, "expr $f1; engrecov[int($f1 * max(1, engarecn) / 128)]", 800, 1075)
    bvf = a.obj("f", 900, 1125)
    a.c(bx, 1, bvf, 1)                       # value first (cold) ...
    bi = to(a, bx, "t b f", 800, 1100)       # ... then the index, then write
    bw = a.obj("tabwrite engov0", 800, 1150)
    a.c(a.obj("r $0-aovset", 950, 1100), 0, bw, 0)
    a.c(bi, 1, bw, 1)
    a.c(bi, 0, bvf, 0)
    a.c(bvf, 0, bw, 0)

    # ---------- tap / clear key (high A): tap = next state, held 900 ms = clear
    kp = chain(a, a.obj("r notesRaw", 20, 1350), ["route 81", "sel 0"], 20, 1375)
    ktm = a.obj("timer", 20, 1425)
    a.c(to(a, kp, "t b", 60, 1400, outlet=1), 0, ktm, 0)     # press: start timing
    kk = chain(a, a.obj("r eng-aloop-key", 150, 1350), ["t b b"], 150, 1375)
    a.c(kk, 1, ktm, 1)
    kv = a.obj("f", 150, 1450)
    a.c(ktm, 0, kv, 1)
    a.c(kk, 0, kv, 0)
    km = to(a, kv, "moses 900", 150, 1475)
    to(a, to(a, km, "t b", 150, 1500), "s eng-aloop-tap", 150, 1525)
    to(a, to(a, km, "t b", 250, 1500, outlet=1), "s eng-aloop-clear", 250, 1525)

    st = chain(a, a.obj("r eng-aloop-tap", 20, 1600), ["v engastate", "sel 0 1 2 3 4 5"], 20, 1625)
    # EMPTY: armed if a MIDI loop plays (record one MIDI cycle from its start), else record now
    e0 = chain(a, st, ["expr (englstate == 2) || (englstate == 3)", "sel 1 0"], 20, 1650)
    arm = to(a, e0, "t b b", 20, 1700)
    setv(a, arm, "engastate", 1, 100, 1725, outlet=1)
    a.c(arm, 0, stat, 0)
    rstart = a.obj("s $0-arecstart", 200, 1725)
    a.c(e0, 1, rstart, 0)
    am = chain(a, a.obj("r $0-cycle", 350, 1650), ["expr engastate == 1", "sel 1"], 350, 1675)
    amt = to(a, am, "t b b", 350, 1700)
    setv(a, amt, "engasync", 1, 450, 1725, outlet=1)
    a.c(amt, 0, rstart, 0)
    # ARMED: tap again cancels
    ca = to(a, st, "t b b", 600, 1650, outlet=1)
    setv(a, ca, "engastate", 0, 650, 1675, outlet=1)
    a.c(ca, 0, stat, 0)
    # REC -> PLAY
    to(a, st, "s $0-arecend", 800, 1650, outlet=2)
    # PLAY -> DUB
    to(a, st, "s $0-adubstart", 1000, 1650, outlet=3)
    # DUB -> PLAY
    to(a, st, "s $0-adubend", 1200, 1650, outlet=4)
    # STOP -> PLAY from the start
    s5 = to(a, st, "t b b b", 1400, 1650, outlet=5)
    setv(a, s5, "engastate", 3, 1400, 1675, outlet=2)
    to(a, s5, "s $0-aplay", 1500, 1675, outlet=1)
    a.c(s5, 0, stat, 0)

    # ---------- record the first take: [s $0-arecstart]
    rs = chain(a, a.obj("r $0-arecstart", 20, 1850), ["t b b b b b b b b b"], 20, 1875)
    to(a, rs, "s $0-afree", 20, 1900, outlet=8)
    to(a, rs, "s $0-ause", 100, 1900, outlet=7)
    send(a, rs, "1", "$0-adsp", 180, 1900, outlet=7)
    to(a, rs, "s $0-adspcancel", 260, 1900, outlet=8)
    for i, (nm, v) in enumerate((("engastate", 2), ("engalen", 0), ("engaspd", 1), ("engatail", 0), ("engak", 0),
                                 ("engarecn", 0))):
        setv(a, rs, nm, v, 280 + i * 60, 1900, outlet=6)
    send(a, rs, "0", "$0-afreq", 650, 1900, outlet=5)
    send(a, rs, "0", "$0-alen", 720, 1900, outlet=4)
    send(a, rs, "0", "$0-aksig", 790, 1900, outlet=5)
    send(a, rs, "1", "$0-agatesig", 860, 1900, outlet=4)
    send(a, rs, "start 0", "$0-awcmd", 930, 1900, outlet=3)
    send(a, rs, "1", "$0-aovrun", 1020, 1900, outlet=2)
    rtm = a.obj("timer", 20, 1950)
    a.c(rs, 1, rtm, 0)
    # ends by itself after one MIDI cycle (synced) or at the maximum length
    rend = a.obj("delay", 300, 1975)
    a.c(to(a, rs, "expr if(engasync, engllen / max(0.05, abs(englspd)), engamaxms)", 300, 1950, outlet=1), 0, rend, 0)
    to(a, rend, "s eng-aloop-tap", 300, 2000)
    a.c(rs, 0, stat, 0)
    # ---------- first take done: [s $0-arecend]
    re = chain(a, a.obj("r $0-arecend", 20, 2100), ["t b b b b b b b b b"], 20, 2125)
    a.c(msg_to(a, re, "stop", 400, 2150, outlet=8), 0, rend, 0)
    a.c(re, 8, rtm, 1)
    rms = a.obj("f", 20, 2175)
    a.c(rtm, 0, rms, 1)
    a.c(to(a, re, "t b", 20, 2150, outlet=7), 0, rms, 0)
    to(a, to(a, rms, "expr if(engasync, engllen / max(0.05, abs(englspd)), min($f1, engamaxms))", 20, 2200),
       "v engalenms", 20, 2225)
    to(a, to(a, re, "expr max(64, int(engalenms * engasr / 1000))", 200, 2175, outlet=6), "v engalen", 200, 2200)
    to(a, to(a, re, "expr engalen", 400, 2175, outlet=5), "s $0-alen", 400, 2200)
    to(a, re, "s $0-axfade", 500, 2175, outlet=5)
    send(a, re, "0", "$0-aovrun", 660, 2175, outlet=5)
    to(a, re, "s $0-arecbins", 740, 2175, outlet=4)
    setv(a, re, "engastate", 3, 840, 2175, outlet=3)
    to(a, to(a, re, "expr engalvl", 920, 2175, outlet=2), "s $0-alvlsig", 920, 2200)
    to(a, to(a, re, "expr engaspd * engasr / max(1, engalen)", 1000, 2175, outlet=2), "s $0-afreq", 1000, 2200)
    to(a, re, "s $0-aplay", 1150, 2175, outlet=1)
    a.c(re, 0, stat, 0)
    # seam crossfade of the first take: start[i] = start[i] * i/N + after_end[i] * (1 - i/N), N = 441 (10 ms)
    xd = chain(a, a.obj("r $0-axfade", 1300, 2100), ["delay 12", "t b b b"], 1300, 2125)
    send(a, xd, "stop", "$0-awcmd", 1300, 2175, outlet=2)
    send(a, xd, "0", "$0-agatesig", 1380, 2175, outlet=2)
    xc = a.obj("f", 1500, 2225)
    a.c(msg_to(a, xd, "0", 1550, 2200, outlet=1), 0, xc, 1)
    a.c(to(a, msg_to(a, xd, "441", 1500, 2175, outlet=1), "until", 1500, 2200), 0, xc, 0)
    a.c(to(a, xc, "+ 1", 1550, 2250), 0, xc, 1)
    for side, x in (("L", 1500), ("R", 1800)):
        t4 = to(a, xc, "t f f f f", x, 2275)
        wr_ = a.obj(f"tabwrite enga{side}0", x, 2400)
        a.c(t4, 3, wr_, 1)                                       # index i
        mix = a.obj("expr $f1 * $f2 / 441 + $f3 * (1 - $f2 / 441)", x, 2375)
        nxt = chain(a, t4, ["expr $f1 + engalen", f"tabread enga{side}0"], x + 150, 2300, outlet=2)
        a.c(nxt, 0, mix, 2)                                      # what was recorded after the end
        a.c(t4, 1, mix, 1)                                       # i
        cur = to(a, t4, f"tabread enga{side}0", x, 2325, outlet=0)
        a.c(cur, 0, mix, 0)                                      # the start (hot)
        a.c(mix, 0, wr_, 0)
        for o in (cur, nxt, wr_):
            a.c(a.obj(f"r $0-awset{side}", x + 250, 2300), 0, o, 0)

    # ---------- overdub start (normal speed only): [s $0-adubstart]
    ds = chain(a, a.obj("r $0-adubstart", 20, 2350), ["t b b"], 20, 2375)
    fit = chain(a, ds, [f"expr engalen / max(0.05, abs(engaspd)) <= {MAXA - 2048}", "sel 0"], 120, 2400, outlet=1)
    a.c(msg_to(a, fit, "list Audio: too slow to overdub this loop", 120, 2450), 0, toast, 0)
    dg = a.obj("spigot", 20, 2375)
    a.c(ds, 0, dg, 0)
    a.c(to(a, ds, f"expr engalen / max(0.05, abs(engaspd)) <= {MAXA - 2048}", 250, 2350, outlet=1), 0, dg, 1)
    dt = chain(a, dg, ["expr engatail", "sel 1 0"], 20, 2400)
    # the layer's first pass is still finishing: carry on with the same layer
    sl = to(a, dt, "t b b b", 20, 2450)
    setv(a, sl, "engatail", 0, 20, 2475, outlet=2)
    setv(a, sl, "engastate", 4, 80, 2475, outlet=1)
    send(a, sl, "1", "$0-agatesig", 140, 2475, outlet=1)
    a.c(sl, 0, stat, 0)
    # a new layer
    nl = to(a, dt, "t b b", 300, 2450, outlet=1)
    to(a, nl, "s $0-afree", 400, 2475, outlet=1)
    ok = chain(a, nl, ["expr engaw >= 0", "sel 1 0"], 300, 2475)
    a.c(msg_to(a, ok, "list Audio: 6 layers used - undo or clear", 450, 2525, outlet=1), 0, toast, 0)
    ng = to(a, ok, "t b b b b", 300, 2525)
    to(a, ng, "s $0-ause", 300, 2550, outlet=3)
    send(a, ng, "1", "$0-agatesig", 400, 2550, outlet=2)
    to(a, ng, "s $0-awbegin", 500, 2550, outlet=2)
    setv(a, ng, "engastate", 4, 600, 2550, outlet=1)
    a.c(ng, 0, stat, 0)
    # ---------- overdub end: [s $0-adubend] (writes silence until the layer's first pass is complete)
    de = chain(a, a.obj("r $0-adubend", 800, 2350), ["t b b b"], 800, 2375)
    send(a, de, "0", "$0-agatesig", 800, 2400, outlet=2)
    setv(a, de, "engastate", 3, 900, 2400, outlet=2)
    dk = chain(a, de, ["expr engak", "sel 1 0"], 1000, 2400, outlet=1)
    to(a, dk, "s $0-awend", 1000, 2450)
    setv(a, dk, "engatail", 1, 1100, 2450, outlet=1)
    a.c(de, 0, stat, 0)

    # ---------- stop / start (high B)
    ss = chain(a, a.obj("r eng-aloop-stopstart", 20, 2650), ["v engastate", "sel 3 4 5"], 20, 2675)
    sp = a.obj("t b b b b", 20, 2725)
    a.c(ss, 0, sp, 0)
    dd = to(a, ss, "t b b", 150, 2700, outlet=1)      # stopping while overdubbing ends the overdub first
    to(a, dd, "s $0-adubend", 250, 2725, outlet=1)
    a.c(dd, 0, sp, 0)
    send(a, sp, "0", "$0-alvlsig", 20, 2750, outlet=3)
    to(a, sp, "s $0-awstop", 100, 2775, outlet=2)
    setv(a, sp, "engastate", 5, 180, 2750, outlet=1)
    a.c(sp, 0, stat, 0)
    to(a, ss, "s eng-aloop-tap", 350, 2700, outlet=2)

    # ---------- undo (high A#): remove the newest layer
    ud = chain(a, a.obj("r eng-aloop-undo", 600, 2650), ["t b b b"], 600, 2675)
    setv(a, ud, "engatop", -1, 750, 2700, outlet=2)
    uc = a.obj("f", 600, 2750)
    a.c(msg_to(a, ud, "0", 700, 2725, outlet=1), 0, uc, 1)
    a.c(to(a, msg_to(a, ud, str(NL), 600, 2700, outlet=1), "until", 600, 2725), 0, uc, 0)
    a.c(to(a, uc, "+ 1", 650, 2775), 0, uc, 1)
    to(a, chain(a, uc, ["expr if(engaon[$f1] && ((engatop < 0) || (engaage[$f1] > engaage[engatop])), $f1, -1)",
                         "moses 0"], 600, 2775), "v engatop", 650, 2825, outlet=1)
    ux = chain(a, ud, ["expr engatop", "moses 0"], 900, 2700)
    a.c(msg_to(a, ux, "list Audio: nothing to undo", 900, 2750), 0, toast, 0)
    # the first take itself, or no layer left afterwards -> clear
    ub = chain(a, ux, ["expr if((engastate == 2) || ((engaon[0] + engaon[1] + engaon[2] + engaon[3] + engaon[4] + "
                        "engaon[5]) <= 1), 1, 0)", "sel 1 0"], 1000, 2750, outlet=1)
    to(a, ub, "s eng-aloop-clear", 1000, 2800)
    ut = to(a, ub, "t b b b b", 1150, 2800, outlet=1)
    # the newest layer is being written: stop the writer first
    uw = chain(a, ut, ["expr (engatop == engaw) && ((engastate == 4) || engatail)", "sel 1"], 1150, 2825, outlet=3)
    uwt = to(a, uw, "t b b b", 1150, 2875)
    to(a, uwt, "s $0-awcancel", 1150, 2900, outlet=2)
    to(a, uwt, "s $0-awend", 1250, 2900, outlet=1)
    setv(a, uwt, "engastate", 3, 1350, 2900, outlet=0)
    send(a, to(a, ut, "expr engatop", 1450, 2825, outlet=2), "0 $1", "$0-asetgain", 1450, 2850)
    tabset(a, ut, "engatop; 0", "engaon", 1600, 2825, outlet=1)
    a.c(msg_to(a, ut, "list Audio: undo", 1800, 2825, outlet=0), 0, toast, 0)

    # ---------- clear (high A held)
    cl = chain(a, a.obj("r eng-aloop-clear", 20, 3000), ["t b b b b b b b b"], 20, 3025)
    to(a, cl, "s $0-awcancel", 20, 3050, outlet=7)
    to(a, cl, "s $0-awend", 100, 3050, outlet=7)
    a.c(msg_to(a, cl, "stop", 180, 3050, outlet=7), 0, rend, 0)
    to(a, cl, "s $0-awstop", 260, 3050, outlet=6)
    send(a, cl, "0", "$0-aovrun", 340, 3050, outlet=6)
    msg_to(a, cl, "; engaon const 0; engag const 0; engaage const 0" +
           "".join(f"; engov{j} const 0" for j in range(NL)), 420, 3050, outlet=5)
    for j in range(NL):
        send(a, cl, "0 20", f"$0-ag{j}", 700 + j * 50, 3050, outlet=4)      # fade out, then switch the DSP off
    for i, nm in enumerate(("engastate", "engalen", "engasync", "engatail", "engacnt", "engak")):
        setv(a, cl, nm, 0, 20 + i * 60, 3100, outlet=3)
    send(a, cl, "0", "$0-afreq", 400, 3100, outlet=2)
    send(a, cl, "0", "$0-alvlsig", 470, 3100, outlet=2)
    adoff = to(a, cl, "delay 40", 540, 3075, outlet=1)
    send(a, adoff, "0", "$0-adsp", 540, 3100)
    a.c(msg_to(a, a.obj("r $0-adspcancel", 640, 3025), "stop", 640, 3050), 0, adoff, 0)   # a new take cancels it
    a.c(cl, 0, stat, 0)

    # ---------- speed (hold A + knob 1): [s eng-aloop-speed] v
    sp_ = chain(a, a.obj("r eng-aloop-speed", 20, 3200), ["t f f"], 20, 3225)
    # an overdub ends before the speed changes (overdubs record at normal speed)
    spc = to(a, sp_, "t f f", 150, 3240, outlet=1)
    to(a, chain(a, spc, ["expr (engastate == 4) && ($f1 != engaspd)", "sel 1"], 150, 3265, outlet=1), "s $0-adubend", 150, 3315)
    to(a, chain(a, spc, ["expr engatail && ($f1 != engaspd)", "sel 1"], 300, 3265, outlet=0), "s $0-awend", 300, 3315)
    spd = to(a, sp_, "t b f", 20, 3250)
    to(a, spd, "v engaspd", 100, 3275, outlet=1)
    spt = to(a, spd, "t b b b", 20, 3275)
    to(a, spt, "s $0-asnap", 20, 3300, outlet=2)
    to(a, to(a, spt, "expr if(engalen > 0, engaspd * engasr / engalen, 0)", 100, 3300, outlet=1), "s $0-afreq", 100, 3325)
    to(a, spt, "s $0-anext", 300, 3300, outlet=0)
    # speed back to 1 for an overdub
    # ---------- pitch (hold A + knob 2): semitones
    pt = chain(a, a.obj("r eng-aloop-pitch", 900, 3200), ["t f f f"], 900, 3225)
    to(a, pt, "v engapitch", 1100, 3250, outlet=2)
    to(a, to(a, pt, "expr 60 + 4 * abs($f1)", 1000, 3250, outlet=1), "s $0-apswin", 1000, 3275)
    to(a, to(a, pt, "expr (1 - pow(2, $f1 / 12)) * 1000 / (60 + 4 * abs($f1))", 900, 3250), "s $0-apsrate", 900, 3275)
    to(a, to(a, pt, "!= 0", 1100, 3275, outlet=2), "s $0-apson", 1100, 3300)
    # ---------- level / fade / pre-post
    lv = chain(a, a.obj("r eng-aloop-level", 1300, 3200), ["t f b"], 1300, 3225)
    to(a, lv, "v engalvl", 1400, 3250, outlet=0)
    a.c(lv, 1, stat, 0)
    to(a, a.obj("r eng-aloop-fade", 1500, 3200), "v engafb", 1500, 3225)
    pp = chain(a, a.obj("r eng-aloop-post", 1650, 3200), ["t f f"], 1650, 3225)
    to(a, pp, "v engapost", 1750, 3250, outlet=1)
    to(a, pp, "s eng-apost", 1650, 3250)
    # loop level follows play / stop
    to(a, chain(a, a.obj("r $0-astat", 1900, 3200),
                ["expr if((engastate == 3) || (engastate == 4), engalvl, 0)"], 1900, 3225), "s $0-alvlsig", 1900, 3250)
    # ---------- status toast
    ts = chain(a, a.obj("r $0-astat", 20, 3450), ["v engastate", "change -1", "sel 0 1 2 3 4 5"], 20, 3475)
    for i, txt in enumerate(("Audio loop clear", "Audio: waits for the loop start", "Audio REC",
                             "Audio PLAY", "Audio DUB", "Audio stop")):
        a.c(msg_to(a, ts, f"list {txt}", 20 + i * 130, 3525, outlet=i), 0, toast, 0)
    return a


def aloop():
    c = Canvas("audio-looper", w=600, h=200)
    c.comment("Audio looper (see sec_aloop.py): signal part + control part", 20, 5)
    c.sub(dsp(), 20, 40)
    c.sub(control(), 20, 80)
    return c

"""Audio looper: up to 6 stacked stereo layers, so sounds from different engines can be layered.

Keys (high octave):  A tap = record > play > overdub > play ...   A held 1 s = clear
                     A# = undo (removes the newest layer)          B = stop / start
Hold A + knob:  1 speed & direction (tape style: centre normal, left reverse)  2 pitch -12..+12 (speed unchanged)
                3 loop level  4 layer fade (older layers fade a little each pass)
Hold B + knob:  Pre (records the synth before the effects; the loop then plays through delay/reverb) / Post
If a MIDI loop is playing, recording waits for the MIDI loop start and lasts exactly one MIDI cycle.

Layers: engaL<j> / engaR<j>. One writer (two tabwrite~) records the newest layer. A layer is always written for at
least one whole pass (after the overdub ends it keeps writing silence until the pass is complete), so it never keeps
leftovers from an earlier, undone take.
States (engastate): 0 empty, 1 armed (waits for the MIDI loop start), 2 REC, 3 PLAY, 4 DUB, 5 STOP.
"""
from pdgen import Canvas
from sec_core import chain, to, msg_to, setv

NL = 6
MAXSEC = 45
MAXA = 44100 * MAXSEC
RECOV = 1024          # overview of the first take, one value per 50 ms


def arrays():
    out = []
    for j in range(NL):
        out += [(f"engaL{j}", MAXA), (f"engaR{j}", MAXA), (f"engov{j}", 128)]
    out += [("engaon", NL), ("engag", NL), ("engaage", NL), ("engrecov", RECOV), ("engscope", 1024), ("engscy", 128)]
    return out


VALUES = ("engastate engalen engalenms engaspd engapitch engalvl engafb engapost engasr engamaxms engaw engak "
          "engatail engasync engacnt engaph engview engatop engarecn engapk").split()


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
    pL, pR = a.obj("r~ eng-tap-postL", 270, 30), a.obj("r~ eng-tap-postR", 400, 30)
    ins = []
    for p, x in ((pL, 150), (pR, 330)):
        o = a.obj("expr~ $v1 * (1 - $v3) + $v2 * $v3", x, 110)
        a.c(dry, 0, o, 0)
        a.c(p, 0, o, 1)
        a.c(post, 0, o, 2)
        ins.append(o)
    inL, inR = ins
    # playhead
    ph = a.obj("phasor~", 600, 110)
    a.c(a.obj("r $0-afreq", 600, 80), 0, ph, 0)
    a.c(a.obj("r $0-aphase", 680, 80), 0, ph, 1)
    idx = a.obj("*~ 0", 600, 140)
    a.c(ph, 0, idx, 0)
    a.c(a.obj("r $0-alen", 680, 115), 0, idx, 1)
    sn = a.obj("snapshot~", 750, 140)
    a.c(ph, 0, sn, 0)
    a.c(a.obj("r $0-asnap", 830, 115), 0, sn, 0)
    to(a, sn, "v engaph", 750, 165)
    # layers
    sums = []
    for side in "LR":
        acc = None
        for j in range(NL):
            x = 20 + j * 160 + (0 if side == "L" else 1000)
            rd = a.obj(f"tabread4~ enga{side}{j}", x, 220)
            a.c(idx, 0, rd, 0)
            g = smooth_msg(a, f"$0-ag{j}", 60, x + 80, 195) if side == "L" else gains[j]
            if side == "L":
                gains_tmp.append(g)
            m = mul2(a, rd, g, x, 270)
            acc = m if acc is None else add2(a, acc, m, x, 295)
        sums.append(acc)
    sumL, sumR = sums
    # pitch shifter: two crossfaded delay taps per side; bypassed at 0 semitones
    rate = chain(a, a.obj("r $0-apsrate", 1300, 330), ["sig~"], 1300, 355)
    win = chain(a, a.obj("r $0-apswin", 1450, 330), ["sig~"], 1450, 355)
    pph = to(a, rate, "phasor~", 1300, 380)
    byp = smooth_msg(a, "$0-apson", 40, 1600, 330)
    shifted = []
    for side, src, x in (("L", sumL, 20), ("R", sumR, 650)):
        to(a, src, f"delwrite~ $0-aps{side} 400", x, 360)
        taps = []
        for k, dx in ((0, 0), (0.5, 300)):
            p = to(a, pph, f"+~ {k}", x + dx, 410)
            w = to(a, p, "wrap~", x + dx, 435)
            d = mul2(a, w, win, x + dx, 460)
            rd = to(a, d, f"vd~ $0-aps{side}", x + dx, 485)
            wnd = chain(a, w, ["-~ 0.5", "*~ 0.5", "cos~"], x + dx + 120, 485)
            taps.append(mul2(a, rd, wnd, x + dx, 560))
        sh = add2(a, taps[0], taps[1], x, 590)
        mx = a.obj("expr~ $v1 + ($v2 - $v1) * $v3", x, 620)
        a.c(src, 0, mx, 0)
        a.c(sh, 0, mx, 1)
        a.c(byp, 0, mx, 2)
        shifted.append(mx)
    lvl = smooth_msg(a, "$0-alvlsig", 50, 1300, 620)
    oL, oR = mul2(a, shifted[0], lvl, 20, 680), mul2(a, shifted[1], lvl, 650, 680)
    # routing: Pre -> mono into the effects input; Post -> stereo after the effects
    pre = a.obj("expr~ ($v1 + $v2) * 0.5 * (1 - $v3)", 20, 720)
    a.c(oL, 0, pre, 0)
    a.c(oR, 0, pre, 1)
    a.c(post, 0, pre, 2)
    to(a, pre, "s~ eng-aret-pre", 20, 745)
    for o, side, x in ((oL, "L", 300), (oR, "R", 450)):
        to(a, mul2(a, o, post, x, 720), f"s~ eng-aret-{side}", x, 745)
    # writer: newest layer = input x gate + what is already there x k (k = 0 during the first pass)
    gate = smooth_msg(a, "$0-agatesig", 8, 1100, 800)
    ksig = chain(a, a.obj("r $0-aksig", 1250, 800), ["sig~"], 1250, 825)
    for side, src, x in (("L", inL, 20), ("R", inR, 500)):
        rd = a.obj(f"tabread4~ enga{side}0", x + 200, 880)
        a.c(idx, 0, rd, 0)
        a.c(a.obj(f"r $0-awset{side}", x + 200, 855), 0, rd, 0)
        wr = a.obj("expr~ $v1 * $v2 + $v3 * $v4", x, 920)
        a.c(src, 0, wr, 0)
        a.c(gate, 0, wr, 1)
        a.c(rd, 0, wr, 2)
        a.c(ksig, 0, wr, 3)
        tw = a.obj(f"tabwrite~ enga{side}0", x, 950)
        a.c(wr, 0, tw, 0)
        a.c(a.obj(f"r $0-awset{side}", x + 120, 925), 0, tw, 0)
        a.c(a.obj("r $0-awcmd", x + 250, 925), 0, tw, 0)
    # input level for the waveform overview
    lv = chain(a, add2(a, inL, inR, 1100, 1000), ["env~ 2048 1024"], 1100, 1030)
    to(a, lv, "v engapk", 1100, 1080)
    return a


gains_tmp = []
gains = gains_tmp


def control():
    a = Canvas("aloop-control", w=2600, h=3600)
    a.comment("Audio looper control. See sec_aloop.py.", 20, 5)
    stat = a.obj("s $0-astat", 20, 3550)
    toast = a.obj("s $0-toast", 200, 3550)

    # ---------- start-up
    lbt = chain(a, a.obj("loadbang", 20, 30), ["t b b b"], 20, 55)
    sr = chain(a, lbt, ["samplerate~", "t f f"], 20, 80, outlet=2)
    to(a, sr, "v engasr", 120, 105, outlet=1)
    to(a, to(a, sr, f"expr min({MAXA}, $f1 * {MAXSEC}) / $f1 * 1000", 20, 105), "v engamaxms", 20, 130)
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
    send(a, to(a, ul, "expr engaw", 1300, 300, outlet=0), "1 $1", "$0-asetgain", 1300, 325)

    # ---------- loop wrap: playhead to the start, writer to the start, fade older layers, schedule the next
    wr = chain(a, a.obj("r $0-awrap", 20, 450), ["t b b"], 20, 475)
    wtm = a.obj("timer", 120, 525)               # two wraps within 20 ms (own clock + MIDI loop) count once
    a.c(wr, 0, wtm, 1)
    wok = chain(a, wtm, ["moses 20"], 120, 550)
    wgo = a.obj("t b b b b", 20, 600)
    a.c(wok, 1, wgo, 0)
    a.c(wgo, 3, wtm, 0)
    send(a, wgo, "0", "$0-aphase", 20, 625, outlet=3)
    wsel = chain(a, wgo, ["expr (engastate == 4) || engatail", "sel 1"], 150, 625, outlet=2)
    send(a, wsel, "start 0", "$0-awcmd", 150, 675)
    # fade: every on layer except the one being written loses (1 - fade)
    fg = chain(a, wgo, ["expr engafb < 0.999", "sel 1"], 350, 625, outlet=1)
    fu = to(a, msg_to(a, fg, str(NL), 350, 675), "until", 350, 700)
    fz = msg_to(a, fg, "0", 450, 675)
    fcn = a.obj("f", 350, 725)
    a.c(fz, 0, fcn, 1)
    a.c(fu, 0, fcn, 0)
    a.c(to(a, fcn, "+ 1", 400, 750), 0, fcn, 1)
    fx = to(a, fcn, "expr if(engaon[$f1] && !(($f1 == engaw) && ((engastate == 4) || engatail)), $f1, -1); "
                    "engag[$f1] * engafb", 350, 775)
    fpk = a.obj("pack 0 0", 350, 825)
    a.c(fx, 1, fpk, 1)
    a.c(to(a, fx, "moses 0", 350, 800), 1, fpk, 0)
    send(a, fpk, "$2 $1", "$0-asetgain", 350, 850)
    # next wrap
    nx = a.obj("delay", 600, 675)
    a.c(chain(a, wgo, ["expr if(engalen > 0, engalenms / max(0.05, abs(engaspd)), -1)", "moses 0"], 600, 625,
              outlet=0), 1, nx, 0)
    to(a, nx, "s $0-awrap", 600, 700)
    a.c(msg_to(a, a.obj("r $0-awstop", 700, 650), "stop", 700, 675), 0, nx, 0)
    a.c(msg_to(a, a.obj("r $0-awstopnext", 800, 650), "stop", 800, 675), 0, nx, 0)
    # a MIDI loop cycle re-aligns a synced audio loop at normal speed
    to(a, chain(a, a.obj("r $0-cycle", 900, 450),
                ["expr engasync && ((engastate == 3) || (engastate == 4)) && (engaspd == 1) && (englspd == 1)", "sel 1"],
                900, 475), "s $0-awrap", 900, 525)

    # ---------- start writing a new layer at the playhead: [s $0-awbegin]
    wb = chain(a, a.obj("r $0-awbegin", 1300, 450), ["t b b b b b"], 1300, 475)
    setv(a, wb, "engak", 0, 1400, 500, outlet=4)
    send(a, wb, "0", "$0-aksig", 1450, 500, outlet=4)
    to(a, wb, "s $0-asnap", 1550, 500, outlet=3)
    st0 = to(a, wb, "expr int(engaph * engalen + 64) % max(1, engalen)", 1600, 525, outlet=2)
    send(a, st0, "start $1", "$0-awcmd", 1600, 550)
    p1 = a.obj("delay", 1300, 550)
    a.c(to(a, wb, "expr engalenms", 1300, 525), 0, p1, 0)
    a.c(msg_to(a, a.obj("r $0-awcancel", 1400, 525), "stop", 1400, 550), 0, p1, 0)
    # first pass complete: from now on the layer adds to itself; a finishing tail ends here
    p1t = to(a, p1, "t b b b", 1300, 575)
    setv(a, p1t, "engak", 1, 1400, 600, outlet=2)
    send(a, p1t, "1", "$0-aksig", 1450, 600, outlet=1)
    to(a, chain(a, p1t, ["expr engatail", "sel 1"], 1300, 600), "s $0-awend", 1300, 650)
    # stop writing: [s $0-awend]
    we = chain(a, a.obj("r $0-awend", 1700, 450), ["t b b b"], 1700, 475)
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
    to(a, s5, "s $0-awrap", 1500, 1675, outlet=1)
    a.c(s5, 0, stat, 0)

    # ---------- record the first take: [s $0-arecstart]
    rs = chain(a, a.obj("r $0-arecstart", 20, 1850), ["t b b b b b b b b b"], 20, 1875)
    to(a, rs, "s $0-afree", 20, 1900, outlet=8)
    to(a, rs, "s $0-ause", 100, 1900, outlet=7)
    send(a, rs, "1", "$0-adsp", 180, 1900, outlet=7)
    for i, (nm, v) in enumerate((("engastate", 2), ("engalen", 0), ("engaspd", 1), ("engatail", 0), ("engak", 0),
                                 ("engarecn", 0))):
        setv(a, rs, nm, v, 280 + i * 60, 1900, outlet=6)
    send(a, rs, "0", "$0-afreq", 650, 1900, outlet=5)
    send(a, rs, "0", "$0-alen", 720, 1900, outlet=5)
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
    send(a, re, "stop", "$0-awcmd", 500, 2175, outlet=5)
    send(a, re, "0", "$0-agatesig", 580, 2175, outlet=5)
    send(a, re, "0", "$0-aovrun", 660, 2175, outlet=5)
    to(a, re, "s $0-arecbins", 740, 2175, outlet=4)
    setv(a, re, "engastate", 3, 840, 2175, outlet=3)
    to(a, to(a, re, "expr engalvl", 920, 2175, outlet=2), "s $0-alvlsig", 920, 2200)
    to(a, to(a, re, "expr engaspd * engasr / max(1, engalen)", 1000, 2175, outlet=2), "s $0-afreq", 1000, 2200)
    to(a, re, "s $0-awrap", 1150, 2175, outlet=1)
    a.c(re, 0, stat, 0)

    # ---------- overdub start (normal speed only): [s $0-adubstart]
    ds = chain(a, a.obj("r $0-adubstart", 20, 2350), ["t b b"], 20, 2375)
    to(a, chain(a, ds, ["expr engaspd != 1", "sel 1"], 120, 2400, outlet=1), "s $0-aspeed1", 120, 2450)
    dt = chain(a, ds, ["expr engatail", "sel 1 0"], 20, 2400)
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
        send(a, cl, "0 0", f"$0-ag{j}", 700 + j * 50, 3050, outlet=4)
    for i, nm in enumerate(("engastate", "engalen", "engasync", "engatail", "engacnt", "engak")):
        setv(a, cl, nm, 0, 20 + i * 60, 3100, outlet=3)
    send(a, cl, "0", "$0-afreq", 400, 3100, outlet=2)
    send(a, cl, "0", "$0-alvlsig", 470, 3100, outlet=2)
    send(a, cl, "0", "$0-adsp", 540, 3100, outlet=1)
    a.c(cl, 0, stat, 0)

    # ---------- speed (hold A + knob 1): [s eng-aloop-speed] v
    sp_ = chain(a, a.obj("r eng-aloop-speed", 20, 3200), ["t f f"], 20, 3225)
    # an overdub ends before the speed changes (overdubs record at normal speed)
    to(a, chain(a, sp_, ["expr (engastate == 4) && ($f1 != 1)", "sel 1"], 150, 3250, outlet=1), "s $0-adubend", 150, 3300)
    spd = to(a, sp_, "t b f", 20, 3250)
    to(a, spd, "v engaspd", 100, 3275, outlet=1)
    spt = to(a, spd, "t b b b", 20, 3275)
    to(a, spt, "s $0-asnap", 20, 3300, outlet=2)
    to(a, to(a, spt, "expr if(engalen > 0, engaspd * engasr / engalen, 0)", 100, 3300, outlet=1), "s $0-afreq", 100, 3325)
    rem = chain(a, spt, ["expr if((engalen > 0) && ((engastate == 3) || (engastate == 4)), "
                         "if(engaspd > 0, 1 - engaph, engaph) * engalenms / max(0.05, abs(engaspd)), -1)", "moses 0"],
                300, 3300)
    rd = a.obj("delay", 400, 3375)
    a.c(rem, 1, rd, 0)
    to(a, rd, "s $0-awrap", 400, 3400)
    a.c(msg_to(a, a.obj("r $0-awstop", 500, 3350), "stop", 500, 3375), 0, rd, 0)
    # the regular wrap clock waits for this one
    to(a, to(a, rem, "t b", 250, 3375, outlet=1), "s $0-awstopnext", 250, 3400)
    # speed back to 1 for an overdub
    send(a, a.obj("r $0-aspeed1", 700, 3200), "1", "eng-aloop-speed", 700, 3225)
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
    gains_tmp.clear()
    c.sub(dsp(), 20, 40)
    c.sub(control(), 20, 80)
    return c

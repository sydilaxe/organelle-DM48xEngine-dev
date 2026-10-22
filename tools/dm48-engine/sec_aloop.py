"""Audio looper: up to 6 stacked stereo layers, so sounds from different engines can be layered.

Keys (high octave):  A tap = record > play > overdub > play ...   A held 1 s = clear
                     A# = undo (remove the newest layer)          B = stop / start
Hold A + knob:  1 speed & direction (tape style)  2 pitch -12..+12 (speed unchanged)  3 level  4 layer fade
Hold B + knob 1: Pre (records the synth before the effects; the loop then goes through delay/reverb)
                 / Post (records the finished sound)
If a MIDI loop is playing, recording starts at the MIDI loop's start and lasts exactly one MIDI cycle.

Each layer is written for at least one full pass, so it never holds leftovers from an undone layer.
States (engastate): 0 empty, 1 armed (waits for the MIDI loop start), 2 REC, 3 PLAY, 4 DUB, 5 STOP.
"""
from pdgen import Canvas
from sec_core import chain, to, msg_to, setv

NL = 6                 # layers
MAXSEC = 45            # seconds per layer
MAXA = 44100 * MAXSEC


def arrays():
    """(name, size) for gen_main"""
    out = []
    for j in range(NL):
        out += [(f"engaL{j}", MAXA), (f"engaR{j}", MAXA), (f"engov{j}", 128)]
    out += [("engaon", NL), ("engag", NL), ("engaage", NL), ("engscope", 1024), ("engscy", 128)]
    return out


VALUES = ("engastate engalen engalenms engaspd engapost engafb engalvl engasr engaw engak engagate engasync "
          "engatail engacnt engaph engapitch engview engatop").split()


def aloop():
    a = Canvas("audio-looper", w=2400, h=2000)
    a.comment("Audio looper: 6 stereo layers (engaL0..5 / engaR0..5), playhead = phasor~ x length, "
              "one writer (tabwrite~) for the newest layer. See the docstring in sec_aloop.py.", 20, 5)
    stat = a.obj("s $0-astat", 20, 1950)
    toast = a.obj("s $0-toast", 200, 1950)

    # ---------------- signals ----------------
    post = chain(a, a.obj("r eng-apost", 20, 40), ["$1 30", "line~"], 20, 65)
    a.items[len(a.items) - 2] = ("msg", (20, 65, "$1 30"))
    dry = a.obj("r~ eng-tap-pre", 150, 40)
    pL, pR = a.obj("r~ eng-tap-postL", 270, 40), a.obj("r~ eng-tap-postR", 400, 40)
    inL = a.obj("expr~ $v1 * (1 - $v3) + $v2 * $v3", 150, 120)
    inR = a.obj("expr~ $v1 * (1 - $v3) + $v2 * $v3", 330, 120)
    for o, p in ((inL, pL), (inR, pR)):
        a.c(dry, 0, o, 0)
        a.c(p, 0, o, 1)
        a.c(post, 0, o, 2)
    ph = a.obj("phasor~", 600, 120)
    a.c(a.obj("r $0-afreq", 600, 90), 0, ph, 0)
    a.c(a.obj("r $0-aphase", 680, 90), 0, ph, 1)
    idx = a.obj("*~ 0", 600, 150)
    a.c(ph, 0, idx, 0)
    a.c(a.obj("r $0-alen", 680, 125), 0, idx, 1)
    # layers
    sumL = sumR = None
    for j in range(NL):
        x = 20 + j * 200
        rl, rr = a.obj(f"tabread4~ engaL{j}", x, 220), a.obj(f"tabread4~ engaR{j}", x + 100, 220)
        a.c(idx, 0, rl, 0)
        a.c(idx, 0, rr, 0)
        g = chain(a, a.obj(f"r $0-ag{j}", x + 100, 245), ["line~"], x + 100, 270)
        gl, gr = a.obj("*~", x, 300), a.obj("*~", x + 100, 300)
        a.c(rl, 0, gl, 0)
        a.c(rr, 0, gr, 0)
        a.c(g, 0, gl, 1)
        a.c(g, 0, gr, 1)
        if sumL is None:
            sumL, sumR = gl, gr
        else:
            sumL, sumR = (to(a, sumL, "+~", x, 330), to(a, sumR, "+~", x + 100, 330))
            a.c(gl, 0, sumL, 1)
            a.c(gr, 0, sumR, 1)
    # pitch shifter (two crossfaded delay taps), bypassed at 0
    shifted = []
    for side, src, x in (("L", sumL, 20), ("R", sumR, 700)):
        a.c(src, 0, a.obj(f"delwrite~ $0-aps{side} 400", x, 400), 0)
    psr = chain(a, a.obj("r $0-apsrate", 1400, 380), ["sig~"], 1400, 405)
    pph = to(a, psr, "phasor~", 1400, 430)
    pwin = chain(a, a.obj("r $0-apswin", 1550, 380), ["sig~"], 1550, 405)
    for side, x, src in (("L", 20, sumL), ("R", 700, sumR)):
        taps = []
        for k in (0, 0.5):
            p = to(a, pph, f"+~ {k}", x + (300 if k else 0), 460) if k else pph
            w = to(a, p, "wrap~", x + (300 if k else 0), 485)
            d = a.obj("*~", x + (300 if k else 0), 510)
            a.c(w, 0, d, 0)
            a.c(pwin, 0, d, 1)
            rd = a.obj(f"vd~ $0-aps{side}", x + (300 if k else 0), 535)
            a.c(d, 0, rd, 0)
            win = chain(a, w, ["-~ 0.5", "*~ 0.5", "cos~"], x + 150 + (300 if k else 0), 535)
            m = a.obj("*~", x + (300 if k else 0), 610)
            a.c(rd, 0, m, 0)
            a.c(win, 0, m, 1)
            taps.append(m)
        sh = add2(a, taps[0], taps[1], x, 640)
        byp = chain(a, a.obj("r $0-apson", x + 200, 640), ["$1 40", "line~"], x + 200, 665)
        a.items[len(a.items) - 2] = ("msg", (x + 200, 665, "$1 40"))
        mx = a.obj("expr~ $v1 + ($v2 - $v1) * $v3", x, 700)
        a.c(src, 0, mx, 0)
        a.c(sh, 0, mx, 1)
        a.c(byp, 0, mx, 2)
        shifted.append(mx)
    lvl = chain(a, a.obj("r $0-alvlsig", 1400, 700), ["$1 50", "line~"], 1400, 725)
    a.items[len(a.items) - 2] = ("msg", (1400, 725, "$1 50"))
    oL = mul2(a, shifted[0], lvl, 20, 760)
    oR = mul2(a, shifted[1], lvl, 700, 760)
    # routing: pre -> mono into the effects input, post -> stereo after the effects
    pre = a.obj("expr~ ($v1 + $v2) * 0.5 * (1 - $v3)", 20, 800)
    a.c(oL, 0, pre, 0)
    a.c(oR, 0, pre, 1)
    a.c(post, 0, pre, 2)
    to(a, pre, "s~ eng-aret-pre", 20, 825)
    for o, side, x in ((oL, "L", 300), (oR, "R", 500)):
        q = a.obj("*~", x, 800)
        a.c(o, 0, q, 0)
        a.c(post, 0, q, 1)
        to(a, q, f"s~ eng-aret-{side}", x, 825)
    # writer: newest layer = input x gate + what is already there x k (k = 0 on the first pass)
    gate = chain(a, a.obj("r $0-agatesig", 1100, 880), ["$1 8", "line~"], 1100, 905)
    a.items[len(a.items) - 2] = ("msg", (1100, 905, "$1 8"))
    ks = chain(a, a.obj("r $0-aksig", 1250, 880), ["sig~"], 1250, 905)
    for side, src, x in (("L", inL, 20), ("R", inR, 500)):
        rd = a.obj(f"tabread4~ engaL0" if side == "L" else "tabread4~ engaR0", x + 200, 940)
        a.c(idx, 0, rd, 0)
        a.c(a.obj(f"r $0-awset{side}", x + 200, 915), 0, rd, 0)
        wr = a.obj("expr~ $v1 * $v2 + $v3 * $v4", x, 980)
        a.c(src, 0, wr, 0)
        a.c(gate, 0, wr, 1)
        a.c(rd, 0, wr, 2)
        a.c(ks, 0, wr, 3)
        tw = a.obj(f"tabwrite~ enga{side}0", x, 1010)
        a.c(wr, 0, tw, 0)
        a.c(a.obj(f"r $0-awset{side}", x + 100, 985), 0, tw, 0)
        a.c(a.obj("r $0-awcmd", x + 200, 985), 0, tw, 0)
    # phase snapshot (control): [s $0-asnap] bang -> [v engaph]
    sn = a.obj("snapshot~", 600, 180)
    a.c(ph, 0, sn, 0)
    a.c(a.obj("r $0-asnap", 680, 155), 0, sn, 0)
    to(a, sn, "v engaph", 600, 205)
    # overview while writing: every 50 ms, level of the input at the playhead bin
    ovm = a.obj("metro 50", 1600, 980)
    a.c(a.obj("r $0-aovrun", 1600, 955), 0, ovm, 0)
    envs = chain(a, add2(a, inL, inR, 1700, 1000), ["env~ 2048 1024"], 1700, 1030)
    ovv = a.obj("f", 1700, 1080)
    a.c(envs, 0, ovv, 1)
    ovt = to(a, ovm, "t b b", 1600, 1005)
    a.c(ovt, 1, a.obj("s $0-asnap", 1650, 1030), 0)
    a.c(ovt, 0, ovv, 0)
    ovx = to(a, ovv, "expr int(min(127, max(0, engaph * 128))); min(1, dbtorms($f1) * 3) * engagate", 1700, 1105)
    ovw = a.obj("expr max($f1, $f2)", 1850, 1130)
    ovi = a.obj("f", 1700, 1155)
    ovt2 = to(a, ovx, "t f f", 1700, 1130)
    a.c(ovx, 1, ovw, 1)
    a.c(ovt2, 1, ovi, 1)
    old = chain(a, ovt2, ["tabread engov0"], 1850, 1100, outlet=0)
    a.c(a.obj("r $0-aovset", 1950, 1075), 0, old, 0)
    oldk = to(a, old, "expr $f1 * engak", 1850, 1120)
    a.c(oldk, 0, ovw, 0)
    tw2 = a.obj("tabwrite engov0", 1850, 1180)
    a.c(a.obj("r $0-aovset", 1950, 1155), 0, tw2, 0)
    a.c(ovw, 0, tw2, 0)
    a.c(ovt2, 1, tw2, 1)
    a.items[ovi] = ("text", (1700, 1155, "-"))

    # ---------------- control ----------------
    lb = a.obj("loadbang", 1100, 40)
    lbt = to(a, lb, "t b b b", 1100, 65)
    sr = chain(a, lbt, ["samplerate~", "t f f"], 1100, 90, outlet=2)
    to(a, sr, "v engasr", 1200, 115, outlet=1)
    to(a, to(a, sr, f"expr min({MAXA}, $f1 * {MAXSEC}) / $f1 * 1000", 1100, 115), "v engamaxms", 1100, 140)
    for nm, v in (("engaspd", 1), ("engafb", 1), ("engalvl", 0.8), ("engapost", 0), ("engapitch", 0), ("engview", 0)):
        setv(a, lbt, nm, v, 1300 + len(nm) * 3, 90, outlet=1)
    msg_to(a, lbt, "; " + "; ".join(f"$0-ag{j} 0" for j in range(NL)).replace("$0", "\\$0"), 1500, 90, outlet=0)
    for nm, v in (("eng-apost", 0), ("$0-alvlsig", 0.8), ("$0-apson", 0), ("$0-agatesig", 0), ("$0-aksig", 0)):
        to(a, msg_to(a, lbt, str(v), 1700 + len(nm) * 4, 115, outlet=0), f"s {nm}", 1700 + len(nm) * 4, 140)

    # helpers: play frequency from speed + length; schedule the next loop wrap
    def freq_msg(src, x, y, outlet=0):
        return to(a, to(a, src, "expr if(engalen > 0, engaspd * engasr / engalen, 0)", x, y, outlet=outlet),
                  "s $0-afreq", x, y + 25)

    # wrap: phase back to 0 (or 1 in reverse is the same point), restart a writer that is running, schedule the next
    wrap = a.obj("r $0-awrap", 20, 1100)
    wt = to(a, wrap, "t b b b b b", 20, 1125)
    to(a, msg_to(a, wt, "0", 20, 1150, outlet=4), "s $0-aphase", 20, 1175)
    wst = chain(a, wt, ["expr engatail + (engastate == 4)", "sel 0"], 120, 1150, outlet=3)
    a.items[len(a.items) - 1] = ("obj", (120, 1175, "moses 1"))
    a.c(msg_to(a, wst, "start 0", 160, 1200, outlet=1), 0, a.obj("s $0-awcmd", 160, 1225), 0)
    # layer fade: older layers lose (1 - fade) per pass
    fd = a.obj("expr engafb", 300, 1150)
    a.c(wt, 2, fd, 0)
    fdt = to(a, fd, "moses 0.999", 300, 1175)
    fu = to(a, msg_to(a, fdt, str(NL), 300, 1200), "until", 300, 1225)
    fc = a.obj("f", 300, 1250)
    a.c(fu, 0, fc, 0)
    a.c(to(a, fc, "+ 1", 340, 1275), 0, fc, 1)
    a.c(msg_to(a, fdt, "0", 360, 1200), 0, fc, 1)
    fdx = to(a, fc, "expr if(engaon[$f1] && ($f1 != engaw || engastate < 4), $f1, -1); "
                   "engag[$f1] * engafb", 300, 1300)
    fdp = a.obj("pack 0 0", 300, 1350)
    a.c(fdx, 1, fdp, 1)
    a.c(to(a, fdx, "moses 0", 300, 1325), 1, fdp, 0)
    fdt2 = to(a, fdp, "t a a", 300, 1375)
    to(a, msg_to(a, fdt2, "$2 $1", 300, 1400), "s $0-asetgain", 300, 1425)
    # the next wrap
    nx = a.obj("delay", 500, 1175)
    a.c(to(a, wt, "expr if(engalen > 0, engalenms / max(0.05, abs(engaspd)), -1)", 500, 1150, outlet=1), 0,
        to(a, a.obj("moses 0", 500, 1150), "t b", 0, 0) if False else nx, 0)
    a.c(nx, 0, wrap, 0) if False else None
    to(a, nx, "s $0-awrap", 500, 1200)
    a.c(msg_to(a, a.obj("r $0-awstop", 600, 1125), "stop", 600, 1150), 0, nx, 0)
    # a MIDI loop cycle re-aligns a synced loop at normal speed
    mc = chain(a, a.obj("r $0-cycle", 700, 1100), ["expr engasync && (engastate >= 3) && (engastate <= 4) && (engaspd == 1)", "sel 1"],
               700, 1125)
    to(a, mc, "s $0-awrap", 700, 1175)

    # set layer gain: [s $0-asetgain] "gain layer"
    sg = chain(a, a.obj("r $0-asetgain", 900, 1100), ["unpack 0 0"], 900, 1125)
    sgv = a.obj("f", 900, 1175)
    a.c(sg, 0, sgv, 1)
    sgt = to(a, sg, "t f f", 980, 1150, outlet=1)
    a.c(sgt, 0, sgv, 0)
    sgx = a.obj("expr $f2; $f1", 900, 1225)
    sgp = a.obj("pack 0 0", 900, 1200)
    a.c(sgt, 1, sgp, 1)
    a.c(sgv, 0, sgp, 0)
    sgo = to(a, sgp, "t a a", 900, 1225)
    a.items[sgx] = ("text", (900, 1250, "-"))
    tabw = a.obj("tabwrite engag", 1000, 1275)
    sgl = to(a, sgo, "unpack 0 0", 1000, 1250, outlet=1)
    a.c(sgl, 1, tabw, 1)
    a.c(sgl, 0, tabw, 0)
    rt = a.obj("route " + " ".join(str(j) for j in range(NL)), 900, 1300)
    a.c(msg_to(a, sgo, "$2 $1", 900, 1250), 0, rt, 0)
    for j in range(NL):
        to(a, msg_to(a, rt, "$1 60", 900 + j * 60, 1325, outlet=j), f"s $0-ag{j}", 900 + j * 60, 1350)

    # select the write layer: [s $0-awlayer] j
    wl = chain(a, a.obj("r $0-awlayer", 1300, 1100), ["t f f f"], 1300, 1125)
    to(a, wl, "v engaw", 1450, 1150, outlet=2)
    for side in ("L", "R"):
        to(a, msg_to(a, wl, f"set enga{side}$1", 1300 + (100 if side == "R" else 0), 1150, outlet=1),
           f"s $0-awset{side}", 1300 + (100 if side == "R" else 0), 1175)
    to(a, msg_to(a, wl, "set engov$1", 1500, 1150), "s $0-aovset", 1500, 1175)

    # ---- start writing a layer: [s $0-awbegin] (k = 0 for one pass, then 1)
    wb = chain(a, a.obj("r $0-awbegin", 20, 1500), ["t b b b b b"], 20, 1525)
    setv(a, wb, "engak", 0, 120, 1550, outlet=4)
    to(a, msg_to(a, wb, "0", 170, 1550, outlet=4), "s $0-aksig", 170, 1575)
    to(a, wb, "s $0-asnap", 250, 1550, outlet=3)
    sto = to(a, wb, "expr int(engaph * engalen + 64) % max(1, engalen)", 300, 1575, outlet=2)
    to(a, msg_to(a, sto, "start $1", 300, 1600), "s $0-awcmd", 300, 1625)
    to(a, msg_to(a, wb, "1", 450, 1575, outlet=1), "s $0-aovrun", 450, 1600)
    pd1 = a.obj("delay", 20, 1600)
    a.c(to(a, wb, "expr engalenms / max(0.05, abs(engaspd))", 20, 1575), 0, pd1, 0)
    a.c(msg_to(a, a.obj("r $0-awbegin-cancel", 100, 1575), "stop", 100, 1600), 0, pd1, 0)
    p1t = to(a, pd1, "t b b", 20, 1625)
    setv(a, p1t, "engak", 1, 100, 1650, outlet=1)
    to(a, msg_to(a, p1t, "1", 150, 1650, outlet=1), "s $0-aksig", 150, 1675)
    # first pass done: a finishing tail ends here
    tl = chain(a, p1t, ["expr engatail", "sel 1"], 20, 1650)
    to(a, tl, "s $0-awend", 20, 1700)
    # end writing: [s $0-awend]
    we = chain(a, a.obj("r $0-awend", 300, 1700), ["t b b b"], 300, 1725)
    setv(a, we, "engatail", 0, 300, 1750, outlet=2)
    to(a, msg_to(a, we, "stop", 400, 1750, outlet=1), "s $0-awcmd", 400, 1775)
    to(a, msg_to(a, we, "0", 500, 1750), "s $0-aovrun", 500, 1775)
    to(a, msg_to(a, we, "0", 600, 1750), "s $0-agatesig", 600, 1775)

    # ---- find a free layer -> [v engaw] (-1 if none): [s $0-afree]
    ff = chain(a, a.obj("r $0-afree", 1300, 1500), ["t b b b"], 1300, 1525)
    setv(a, ff, "engaw", -1, 1450, 1550, outlet=2)
    fun = to(a, msg_to(a, ff, str(NL), 1300, 1550, outlet=1), "until", 1300, 1575)
    fct = a.obj("f", 1300, 1600)
    a.c(msg_to(a, ff, "0", 1400, 1575, outlet=1), 0, fct, 1)
    a.c(fun, 0, fct, 0)
    a.c(to(a, fct, "+ 1", 1350, 1625), 0, fct, 1)
    to(a, chain(a, fct, ["expr if((engaon[$f1] == 0) && (engaw < 0), $f1, -1)", "moses 0"], 1300, 1650, outlet=0),
       "v engaw", 1350, 1700, outlet=1)

    # ---- use layer engaw: mark on, newest, gain 1, writer to it
    ul = chain(a, a.obj("r $0-ause", 1600, 1500), ["t b b b b"], 1600, 1525)
    to(a, to(a, ul, "expr engaw", 1600, 1550, outlet=3), "s $0-awlayer", 1600, 1575)
    tabwrite_v(a, ul, "engaw; 1", "engaon", 1700, 1550, outlet=2)
    tabwrite_v(a, ul, "engaw; engacnt + 1", "engaage", 1850, 1550, outlet=1)
    setv(a, to(a, ul, "t b", 2000, 1550, outlet=1), "engacnt", 0, 2000, 1575) if False else None
    to(a, to(a, ul, "expr engacnt + 1", 2000, 1550, outlet=1), "v engacnt", 2000, 1575)
    to(a, msg_to(a, to(a, ul, "expr engaw", 1600, 1600), "1 $1", 1600, 1625), "s $0-asetgain", 1600, 1650)

    # ---------------- state machine ----------------
    # tap (released quickly) vs clear (held 1 s): high A
    kp = chain(a, a.obj("r notesRaw", 20, 1800), ["route 81", "sel 0"], 20, 1825)
    tmr = a.obj("timer", 20, 1875)
    a.c(kp, 1, tmr, 0)                                 # press (velocity > 0): start timing
    ak = chain(a, a.obj("r eng-aloop-key", 200, 1800), ["t b b"], 200, 1825)
    a.c(ak, 1, tmr, 1)
    a.c(ak, 0, a.obj("s $0-akey2", 300, 1850), 0)
    a.items[kp - 1] = ("obj", (20, 1825, "route 81"))
    kd = chain(a, a.obj("r $0-akey2", 400, 1800), ["t b"], 400, 1825)
    dur = to(a, tmr, "v $0-akeyms", 20, 1900)
    kx = chain(a, kd, ["v $0-akeyms", "moses 900"], 400, 1850)
    to(a, kx, "s eng-aloop-tap", 400, 1900)
    to(a, kx, "s eng-aloop-clear", 500, 1900, outlet=1)

    st = chain(a, a.obj("r eng-aloop-tap", 20, 2000), ["v engastate", "sel 0 1 2 3 4 5"], 20, 2025)
    # EMPTY -> ARMED (MIDI loop playing) or REC
    e0 = chain(a, st, ["t b b", "expr (englstate == 2) || (englstate == 3)"], 20, 2050)
    a.c(len(a.items) - 2, 1, a.obj("s $0-afree", 150, 2075), 0)
    e0s = to(a, e0, "sel 1 0", 20, 2100)
    arm = to(a, e0s, "t b b", 20, 2125)
    setv(a, arm, "engastate", 1, 20, 2150, outlet=1)
    to(a, msg_to(a, arm, "list Audio: waits for the loop start", 100, 2150), "s $0-toast", 100, 2175)
    lp0 = a.obj("s $0-arecstart", 250, 2150)
    a.c(e0s, 1, lp0, 0)
    # armed: the next MIDI loop start begins recording (synced, one cycle long)
    am = chain(a, a.obj("r $0-cycle", 400, 2050), ["expr engastate == 1", "sel 1"], 400, 2075)
    amt = to(a, am, "t b b", 400, 2125)
    setv(a, amt, "engasync", 1, 500, 2150, outlet=1)
    a.c(amt, 0, lp0, 0)
    # ARMED -> tap again: cancel
    ca = to(a, st, "t b b", 600, 2050, outlet=1)
    setv(a, ca, "engastate", 0, 600, 2075, outlet=1)
    a.c(ca, 0, stat, 0)

    # record start: free layer, layer on, write from 0, time it
    rs = chain(a, a.obj("r $0-arecstart", 20, 2250), ["t b b b b b b b"], 20, 2275)
    nofree = chain(a, rs, ["expr engaw < 0", "sel 1"], 20, 2300, outlet=6)
    a.c(msg_to(a, nofree, "list Audio: all 6 layers used - undo or clear", 20, 2325), 0, toast, 0)
    rgo = a.obj("spigot", 300, 2325)
    a.c(to(a, rs, "expr engaw >= 0", 380, 2300, outlet=5), 0, rgo, 1)
    a.c(rs, 4, rgo, 0)
    rg = to(a, rgo, "t b b b b b b", 300, 2350)
    setv(a, rg, "engastate", 2, 300, 2375, outlet=5)
    setv(a, rg, "engalen", 0, 350, 2375, outlet=5)
    setv(a, rg, "engaspd", 1, 400, 2375, outlet=5)
    to(a, rg, "s $0-ause", 450, 2400, outlet=4)
    to(a, msg_to(a, rg, "0", 550, 2400, outlet=3), "s $0-afreq", 550, 2425)
    to(a, msg_to(a, rg, "1", 600, 2400, outlet=2), "s $0-agatesig", 600, 2425)
    to(a, msg_to(a, rg, "0", 650, 2400, outlet=2), "s $0-aksig", 650, 2425)
    setv(a, rg, "engak", 0, 700, 2400, outlet=2)
    to(a, msg_to(a, rg, "start 0", 750, 2400, outlet=1), "s $0-awcmd", 750, 2425)
    to(a, msg_to(a, rg, "1", 850, 2400, outlet=1), "s $0-aovrun", 850, 2425)
    rtm = a.obj("timer", 300, 2450)
    a.c(rg, 0, rtm, 0)
    a.c(rg, 0, stat, 0)
    # auto end: one MIDI cycle when synced, else at the maximum length
    rend = a.obj("delay", 500, 2475)
    a.c(to(a, rg, "expr if(engasync, engllen / max(0.05, abs(englspd)), engamaxms)", 500, 2450, outlet=0), 0, rend, 0)
    to(a, rend, "s eng-aloop-tap", 500, 2500)
    a.c(msg_to(a, a.obj("r $0-arecend", 650, 2450), "stop", 650, 2475), 0, rend, 0)
    # REC -> PLAY: length = time recorded
    r2 = to(a, st, "t b b b b b b b", 900, 2050, outlet=2)
    a.c(r2, 6, a.obj("s $0-arecend", 900, 2075), 0)
    a.c(r2, 5, rtm, 1)
    a.c(to(a, rtm, "expr min($f1, engamaxms)", 1000, 2475), 0, a.obj("v engalenms", 1000, 2500), 0)
    to(a, to(a, r2, "expr max(64, int(engalenms * engasr / 1000))", 950, 2100, outlet=4), "v engalen", 950, 2125)
    to(a, to(a, r2, "expr engalen", 1100, 2100, outlet=3), "s $0-alen", 1100, 2125)
    to(a, msg_to(a, r2, "stop", 1200, 2100, outlet=3), "s $0-awcmd", 1200, 2125)
    to(a, msg_to(a, r2, "0", 1250, 2125, outlet=3), "s $0-aovrun", 1250, 2150)
    to(a, msg_to(a, r2, "0", 1300, 2100, outlet=3), "s $0-agatesig", 1300, 2125)
    setv(a, r2, "engastate", 3, 1350, 2100, outlet=2)
    freq_msg(a.obj("t b", 0, 0), 0, 0) if False else None
    to(a, to(a, r2, "expr if(engalen > 0, engaspd * engasr / engalen, 0)", 1450, 2100, outlet=1), "s $0-afreq", 1450, 2125)
    to(a, r2, "s $0-awrap", 1600, 2100, outlet=1)
    a.c(r2, 0, stat, 0)
    # PLAY -> DUB (normal speed only): a new layer, or the same one if its first pass is still finishing
    d3 = to(a, st, "t b b", 1200, 2200, outlet=3)
    sp1 = chain(a, d3, ["expr engaspd != 1", "sel 1"], 1300, 2225, outlet=1)
    to(a, msg_to(a, sp1, "1", 1300, 2275), "s eng-aloop-speed", 1300, 2300)
    dt = chain(a, d3, ["expr engatail", "sel 1 0"], 1200, 2250)
    # same layer: just open the input again
    sl = to(a, dt, "t b b b", 1200, 2300)
    setv(a, sl, "engatail", 0, 1200, 2325, outlet=2)
    setv(a, sl, "engastate", 4, 1250, 2325, outlet=1)
    to(a, msg_to(a, sl, "1", 1300, 2350, outlet=1), "s $0-agatesig", 1300, 2375)
    a.c(sl, 0, stat, 0)
    # new layer
    nl = to(a, dt, "t b b b", 1450, 2300, outlet=1)
    a.c(nl, 2, a.obj("s $0-afree", 1450, 2325), 0)
    ok = chain(a, nl, ["expr engaw >= 0", "sel 1 0"], 1550, 2325, outlet=1)
    a.c(msg_to(a, ok, "list Audio: all 6 layers used - undo or clear", 1650, 2350, outlet=1), 0, toast, 0)
    ng = to(a, ok, "t b b b b", 1550, 2375)
    to(a, ng, "s $0-ause", 1550, 2400, outlet=3)
    to(a, msg_to(a, ng, "1", 1650, 2400, outlet=2), "s $0-agatesig", 1650, 2425)
    to(a, ng, "s $0-awbegin", 1700, 2425, outlet=2)
    setv(a, ng, "engastate", 4, 1800, 2400, outlet=1)
    a.c(ng, 0, stat, 0)
    a.c(nl, 0, stat, 0) if False else None
    # DUB -> PLAY: close the input; keep writing (silence) until the layer's first pass is complete
    d4 = to(a, st, "t b b b b", 1900, 2200, outlet=4)
    to(a, msg_to(a, d4, "0", 1900, 2225, outlet=3), "s $0-agatesig", 1900, 2250)
    setv(a, d4, "engastate", 3, 2000, 2225, outlet=2)
    kk = chain(a, d4, ["expr engak", "sel 1 0"], 2100, 2225, outlet=1)
    to(a, kk, "s $0-awend", 2100, 2275)
    setv(a, kk, "engatail", 1, 2200, 2275, outlet=1)
    a.c(d4, 0, stat, 0)
    # STOP -> PLAY (from the start)
    s5 = to(a, st, "t b b b", 2200, 2050, outlet=5)
    setv(a, s5, "engastate", 3, 2200, 2075, outlet=2)
    to(a, to(a, s5, "expr engalvl", 2300, 2075, outlet=1), "s $0-alvlsig", 2300, 2100)
    to(a, s5, "s $0-awrap", 2300, 2125, outlet=1)
    a.c(s5, 0, stat, 0)

    # ---- stop / start (high B)
    ss = chain(a, a.obj("r eng-aloop-stopstart", 20, 2600), ["v engastate", "sel 3 4 5"], 20, 2625)
    sst = a.obj("t b b b b", 20, 2675)
    a.c(ss, 0, sst, 0)
    dd = to(a, ss, "t b b", 120, 2650, outlet=1)        # stop while dubbing: end the dub first
    a.c(dd, 1, a.obj("s eng-aloop-tap", 120, 2675), 0)
    a.c(dd, 0, sst, 0)
    to(a, msg_to(a, sst, "0", 20, 2700, outlet=3), "s $0-alvlsig", 20, 2725)
    to(a, sst, "s $0-awstop", 120, 2700, outlet=2)
    setv(a, sst, "engastate", 5, 200, 2700, outlet=1)
    a.c(sst, 0, stat, 0)
    a.c(ss, 2, a.obj("s eng-aloop-tap", 300, 2650), 0)

    # ---- undo (high A#): remove the newest layer
    ud = chain(a, a.obj("r eng-aloop-undo", 600, 2600), ["t b b b b b"], 600, 2625)
    setv(a, ud, "engatop", -1, 800, 2650, outlet=4)
    uun = to(a, msg_to(a, ud, str(NL), 600, 2650, outlet=3), "until", 600, 2675)
    uc = a.obj("f", 600, 2700)
    a.c(msg_to(a, ud, "0", 700, 2675, outlet=3), 0, uc, 1)
    a.c(uun, 0, uc, 0)
    a.c(to(a, uc, "+ 1", 650, 2725), 0, uc, 1)
    to(a, chain(a, uc, ["expr if(engaon[$f1] && ((engatop < 0) || (engaage[$f1] > engaage[engatop])), $f1, -1)",
                         "moses 0"], 600, 2750), "v engatop", 650, 2800, outlet=1)
    ux = chain(a, ud, ["expr engatop", "moses 0"], 900, 2650, outlet=2)
    a.c(msg_to(a, ux, "list Audio: nothing to undo", 900, 2700), 0, toast, 0)
    ut = to(a, ux, "t f f f f", 1000, 2700, outlet=1)
    # the newest layer being written? stop the writer first
    uw = chain(a, ut, ["expr ($f1 == engaw) && ((engastate == 4) || (engatail == 1) || (engastate == 2))", "sel 1"],
               1300, 2725, outlet=3)
    uwt = to(a, uw, "t b b b", 1300, 2750)
    to(a, uwt, "s $0-awend", 1300, 2775, outlet=2)
    to(a, uwt, "s $0-awbegin-cancel", 1400, 2775, outlet=1)
    setv(a, uwt, "engastate", 3, 1500, 2775, outlet=0)
    to(a, msg_to(a, ut, "0 $1", 1000, 2750, outlet=2), "s $0-asetgain", 1000, 2775)
    tabwrite_v(a, ut, "$f1; 0", "engaon", 1150, 2750, outlet=1, from_float=True)
    # last layer gone -> empty
    le = chain(a, ud, ["delay 1", "expr engaon[0] + engaon[1] + engaon[2] + engaon[3] + engaon[4] + engaon[5]",
                       "sel 0"], 1200, 2650, outlet=0)
    a.items[le - 1] = ("obj", (1200, 2675, "expr " + " + ".join(f"engaon[{j}]" for j in range(NL))))
    to(a, le, "s eng-aloop-clear", 1200, 2725)
    uu = to(a, ud, "delay 2", 1450, 2650)
    a.c(uu, 0, stat, 0)

    # ---- clear (high A held)
    cl = chain(a, a.obj("r eng-aloop-clear", 20, 2900), ["t b b b b b b b"], 20, 2925)
    to(a, cl, "s $0-awend", 20, 2950, outlet=6)
    to(a, cl, "s $0-awbegin-cancel", 100, 2950, outlet=6)
    to(a, cl, "s $0-arecend", 200, 2950, outlet=6)
    to(a, cl, "s $0-awstop", 300, 2950, outlet=5)
    msg_to(a, cl, "; engaon const 0; engag const 0; engaage const 0" +
           "".join(f"; engov{j} const 0" for j in range(NL)), 400, 2950, outlet=4)
    msg_to(a, cl, "; " + "; ".join(f"\\$0-ag{j} 0" for j in range(NL)), 700, 2950, outlet=3)
    for i, nm in enumerate(("engastate", "engalen", "engasync", "engatail", "engacnt")):
        setv(a, cl, nm, 0, 20 + i * 60, 3000, outlet=2)
    to(a, msg_to(a, cl, "0", 400, 3000, outlet=1), "s $0-afreq", 400, 3025)
    a.c(cl, 0, stat, 0)

    # ---- settings from combos
    # speed: [s eng-aloop-speed] v  (re-schedule the next wrap from the current phase)
    spd = chain(a, a.obj("r eng-aloop-speed", 20, 3100), ["t b f"], 20, 3125)
    to(a, spd, "v engaspd", 120, 3150, outlet=1)
    spt = to(a, spd, "t b b b", 20, 3150)
    to(a, spt, "s $0-asnap", 20, 3175, outlet=2)
    to(a, to(a, spt, "expr if(engalen > 0, engaspd * engasr / engalen, 0)", 100, 3175, outlet=1), "s $0-afreq", 100, 3200)
    rem = to(a, spt, "expr if((engalen > 0) && (engastate >= 3) && (engastate <= 4), "
                     "if(engaspd > 0, (1 - engaph), engaph) * engalenms / max(0.05, abs(engaspd)), -1)", 300, 3175)
    rmo = to(a, rem, "moses 0", 300, 3200)
    a.c(rmo, 0, a.obj("s $0-awstop", 300, 3225), 0) if False else None
    rmd = a.obj("delay", 400, 3250)
    a.c(to(a, rmo, "t f b", 400, 3225, outlet=1), 0, rmd, 0)
    a.c(msg_to(a, len(a.items) - 2, "stop", 500, 3250, outlet=1), 0, a.obj("s $0-awstop", 500, 3275), 0)
    to(a, rmd, "s $0-awrap", 400, 3275)
    a.c(msg_to(a, a.obj("r $0-awstop", 600, 3225), "stop", 600, 3250), 0, rmd, 0)
    # pitch: [s eng-aloop-pitch] semitones
    pt = chain(a, a.obj("r eng-aloop-pitch", 900, 3100), ["t f f f"], 900, 3125)
    to(a, pt, "v engapitch", 1100, 3150, outlet=2)
    to(a, to(a, pt, "expr 60 + 4 * abs($f1)", 1000, 3150, outlet=1), "s $0-apswin", 1000, 3175)
    to(a, to(a, pt, "expr (1 - pow(2, $f1 / 12)) * 1000 / (60 + 4 * abs($f1))", 900, 3150), "s $0-apsrate", 900, 3175)
    to(a, to(a, pt, "!= 0", 1100, 3175, outlet=2), "s $0-apson", 1100, 3200)
    # level / fade / pre-post
    lv = chain(a, a.obj("r eng-aloop-level", 1300, 3100), ["t f f"], 1300, 3125)
    to(a, lv, "v engalvl", 1400, 3150, outlet=1)
    to(a, chain(a, lv, ["expr if((engastate == 3) || (engastate == 4), $f1, 0)"], 1300, 3150), "s $0-alvlsig", 1300, 3200)
    to(a, a.obj("r eng-aloop-fade", 1500, 3100), "v engafb", 1500, 3125)
    pp = chain(a, a.obj("r eng-aloop-post", 1650, 3100), ["t f f"], 1650, 3125)
    to(a, pp, "v engapost", 1750, 3150, outlet=1)
    to(a, pp, "s eng-apost", 1650, 3150)
    # loop level follows play/stop
    lv2 = chain(a, a.obj("r $0-astat", 1900, 3100), ["expr if((engastate == 3) || (engastate == 4), engalvl, 0)"], 1900, 3125)
    to(a, lv2, "s $0-alvlsig", 1900, 3150)

    # ---- status toast
    ts = chain(a, a.obj("r $0-astat", 20, 3300), ["v engastate", "sel 0 1 2 3 4 5"], 20, 3325)
    for i, txt in enumerate(("Audio loop clear", "Audio: waits for the loop start", "Audio REC",
                             "Audio PLAY", "Audio DUB", "Audio stop")):
        to(a, msg_to(a, ts, f"list {txt}", 20 + i * 120, 3375, outlet=i), "s $0-toast", 20 + i * 120, 3400)
    return a


def add2(c, a, b, x, y):
    o = c.obj("+~", x, y)
    c.c(a, 0, o, 0)
    c.c(b, 0, o, 1)
    return o


def mul2(c, a, b, x, y):
    o = c.obj("*~", x, y)
    c.c(a, 0, o, 0)
    c.c(b, 0, o, 1)
    return o


def tabwrite_v(c, src, expr_text, table, x, y, outlet=0, from_float=False):
    """src -> [expr index; value] -> tabwrite table (index first)"""
    ex = to(c, src, f"expr {expr_text}", x, y, outlet=outlet)
    val = c.obj("f", x + 100, y + 50)
    c.c(ex, 1, val, 1)
    t = to(c, ex, "t b f", x, y + 25)
    tw = c.obj(f"tabwrite {table}", x, y + 75)
    c.c(t, 1, tw, 1)
    c.c(t, 0, val, 0)
    c.c(val, 0, tw, 0)
    return ex

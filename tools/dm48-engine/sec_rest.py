"""Engine manager, tuning library, audio/FX, small glue."""
from pdgen import Canvas
from sec_ui import NOTE_NAMES
from sec_core import chain, to, msg_to, setv
from sec_ui import LIB

MAXBYTES, MAXEV = 65536, 4096


def engine_manager():
    e = Canvas("engine-manager", w=1600, h=900)
    e.comment("Lists engines/*.pd, loads the chosen one into every voice, remembers each engine's knob values", 20, 5)
    # ---- scan
    st = chain(e, e.obj("r $0-scan", 20, 30), ["t b b b"], 20, 55)
    msg_to(e, st, "; englist clear", 200, 80, outlet=2)
    g = chain(e, msg_to(e, st, "dir", 20, 80, outlet=1), ["pdcontrol"], 20, 105)
    gl = chain(e, msg_to(e, g, "symbol $1/engines/*.pd", 20, 130), ["file glob", "list split 1", "file splitext",
                                                                      "list split 1", "file splitname"], 20, 155)
    nm = to(e, gl, "list split 1", 20, 280)
    to(e, nm, "text insert englist 1e+06", 20, 330, outlet=1)
    ss = to(e, st, "t b b", 300, 80)
    msg_to(e, ss, "; englist sort", 380, 105, outlet=1)
    to(e, to(e, ss, "text size englist", 300, 105), "v engcount", 300, 130)
    # ---- knob 1 on the ENGINE page picks an engine (shown at once, loaded when the knob rests)
    kx = chain(e, e.obj("r $0-k1p5", 600, 30),
               ["expr if(engcount > 0, min(int($f1 * engcount), engcount - 1), 0)", "change -1", "text get englist"],
               600, 55)
    kxs = msg_to(e, kx, "symbol $1", 600, 135)
    to(e, msg_to(e, kxs, "1 Engine $1", 750, 160), "s $0-disp5", 750, 185)
    kd = e.obj("symbol", 600, 185)
    kxt = to(e, kxs, "t b s", 650, 135)
    e.c(kxt, 1, kd, 1)
    kdl = to(e, kxt, "delay 350", 650, 160)
    e.c(kdl, 0, kd, 0)
    to(e, kd, "s $0-engsel-name", 600, 210)
    # ---- select by name (settings or knob); unknown names fall back to the first engine.
    # Switching while an engine sounds MORPHS: the new engine loads into the free slot (A/B) of every voice,
    # takes over the current notes, and the two crossfade over the morph time. A choice made during a morph waits.
    sn = chain(e, e.obj("r $0-engsel-name", 20, 380), ["t s s"], 20, 405)
    tse = to(e, sn, "text search englist", 120, 430, outlet=1)
    idx = chain(e, tse, ["max 0", "t b f"], 120, 455)
    to(e, idx, "v engpend", 200, 480, outlet=1)
    gb = chain(e, idx, ["expr if(engmorph, 1, engloaded && (engpend == engsel))", "sel 0"], 120, 480)
    go = to(e, gb, "t b b b b", 120, 530)
    to(e, to(e, go, "expr engpend", 400, 555, outlet=3), "v engsel", 400, 580)
    nb = chain(e, go, ["expr if(engloaded, 1 - engbus, 0)", "t f f"], 300, 555, outlet=2)
    to(e, nb, "v engbus", 380, 605, outlet=1)
    onv = chain(e, nb, ["sel 0 1"], 300, 605)
    setv(e, onv, "engslA", 1, 300, 630, outlet=0)
    setv(e, onv, "engslB", 1, 350, 630, outlet=1)
    cn = msg_to(e, to(e, to(e, go, "expr engsel", 120, 555, outlet=1), "text get englist", 120, 580), "symbol $1", 120, 605)
    fade = to(e, go, "expr engloaded", 20, 555)
    fs = to(e, fade, "sel 0 1", 20, 580)
    first = to(e, fs, "t b b", 20, 605)
    setv(e, first, "engloaded", 1, 20, 630, outlet=1)
    to(e, msg_to(e, to(e, first, "expr engbus", 60, 630), "$1 0", 60, 655), "s eng-xfade", 60, 680)
    mo = to(e, fs, "t b b b", 150, 680, outlet=1)
    setv(e, mo, "engmorph", 1, 250, 705, outlet=2)
    mx = to(e, mo, "expr engbus; engmorphms", 150, 705, outlet=1)
    mpk = e.obj("pack 0 0", 150, 730)
    e.c(mx, 1, mpk, 1)
    e.c(mx, 0, mpk, 0)
    to(e, mpk, "s eng-xfade", 150, 755)
    mdl = e.obj("delay", 300, 755)
    e.c(to(e, mo, "expr engmorphms + 60", 300, 730), 0, mdl, 0)
    # morph done: the old slot stops; a choice that waited now loads
    dn = to(e, mdl, "t b b b", 300, 780)
    od = chain(e, dn, ["expr engbus", "sel 0 1"], 450, 805, outlet=2)
    setv(e, od, "engslB", 0, 450, 830, outlet=0)
    setv(e, od, "engslA", 0, 500, 830, outlet=1)
    to(e, dn, "s eng-slupd", 600, 830, outlet=2) if False else None
    sl2 = to(e, od, "t b", 0, 0) if False else None
    setv(e, dn, "engmorph", 0, 350, 830, outlet=1)
    to(e, dn, "s eng-slupd", 600, 805, outlet=1)
    pend = chain(e, dn, ["expr engpend != engsel", "sel 1"], 300, 855)
    to(e, msg_to(e, to(e, to(e, pend, "expr engpend", 300, 880), "text get englist", 300, 905), "symbol $1", 300, 930),
       "s $0-engsel-name", 300, 955)
    # after the new slot is switched on (set above), the voices are told
    to(e, go, "s eng-slupd", 200, 580, outlet=1)
    t4 = to(e, cn, "t s s s s", 120, 600)
    # 3: name for display + saving
    to(e, t4, "s $0-curname", 400, 625, outlet=3)
    to(e, msg_to(e, t4, "1 Engine $1", 520, 625, outlet=3), "s $0-disp5", 520, 650)
    # 2: descriptor engines/NAME.txt -> knob names + defaults
    dt = to(e, t4, "t b s", 300, 650, outlet=2)
    msg_to(e, dt, "; engdesc clear; engdesc read engines/$1.txt", 380, 675, outlet=1)
    sz = chain(e, dt, ["text size engdesc", "t f f"], 300, 700)
    nmo = to(e, sz, "moses 1", 300, 750, outlet=1)
    dnames = msg_to(e, nmo, "P1 P2 P3 P4", 300, 775)
    gn = to(e, msg_to(e, nmo, "0", 400, 775, outlet=1), "text get engdesc", 400, 800)
    un = e.obj("unpack s s s s", 300, 850)
    e.c(dnames, 0, un, 0)
    e.c(gn, 0, un, 0)
    for k in range(4):
        to(e, un, f"s $0-pname{k + 1}", 300 + k * 90, 875, outlet=k)
    dmo = to(e, sz, "moses 2", 600, 725)
    dflt = e.obj("list", 600, 850)
    e.c(msg_to(e, dmo, "0.5 0.5 0.5 0.5", 600, 775), 0, dflt, 1)
    e.c(to(e, msg_to(e, dmo, "1", 720, 775, outlet=1), "text get engdesc", 720, 800), 0, dflt, 1)
    # 1: stored values for this engine, or its defaults
    pt = to(e, t4, "t b s", 900, 650, outlet=1)
    pmo = chain(e, pt, ["text search engparams", "moses 0"], 980, 675, outlet=1)
    e.c(to(e, pmo, "t b", 980, 725), 0, dflt, 0)
    pv = chain(e, pmo, ["text get engparams", "list split 1"], 1080, 725, outlet=1)
    vals = e.obj("unpack 0 0 0 0", 900, 850)
    e.c(dflt, 0, vals, 0)
    e.c(pv, 1, vals, 0)
    for k in range(4):
        to(e, vals, f"s $0-pv{k + 1}", 900 + k * 80, 875, outlet=k)
    # 0: load into the voices, then re-send the knob values to the new engine
    lt = to(e, t4, "t b s", 120, 650)
    ltt = to(e, lt, "t s b", 200, 675, outlet=1)
    lpk = e.obj("pack s s", 200, 725)
    e.c(ltt, 0, lpk, 0)
    lsel = chain(e, ltt, ["expr engbus", "sel 0 1"], 260, 700, outlet=1)
    for i, X in enumerate("AB"):
        e.c(msg_to(e, lsel, f"symbol {X}", 260 + i * 70, 725, outlet=i), 0, lpk, 1)
    to(e, msg_to(e, lpk, "$2 symbol engines/$1", 200, 750), "s eng-load", 200, 775)
    to(e, lt, "s $0-refresh0", 120, 700)
    # ---- remember PLAY knob values per engine: [s $0-pstore] bang
    ps = chain(e, e.obj("r $0-pstore", 1200, 30), ["symbol", "t s s"], 1200, 55)
    e.c(e.obj("r $0-curname", 1300, 30), 0, ps - 1, 1)
    ix = chain(e, ps, ["text search engparams", "t f f"], 1300, 105, outlet=1)
    ins = e.obj("spigot", 1200, 300)
    sett = e.obj("spigot", 1300, 300)
    e.c(to(e, ix, "< 0", 1300, 155, outlet=1), 0, ins, 1)
    e.c(to(e, ix, ">= 0", 1360, 155, outlet=1), 0, sett, 1)
    tset = e.obj("text set engparams", 1300, 325)
    e.c(ix, 0, tset, 1)
    lb = to(e, ps, "t s b", 1200, 180)
    vx = to(e, lb, "expr engpv1; engpv2; engpv3; engpv4", 1250, 205, outlet=1)
    pk = e.obj("pack s 0 0 0 0", 1200, 250)
    for k in (3, 2, 1, 0):
        e.c(vx, k, pk, k + 1)
    e.c(lb, 0, pk, 0)
    e.c(pk, 0, ins, 0)
    e.c(pk, 0, sett, 0)
    to(e, ins, "text insert engparams 1e+06", 1200, 325)
    e.c(sett, 0, tset, 0)
    return e


def library():
    """Tuning librarian: tunings/*.mid -> DM48X (Tuning editor > Receive tuning)."""
    lb = Canvas("library", w=1600, h=1300)
    lb.comment("Sends tunings/*.mid to the DM48X. Notes are played in file order (format 0 and 1 MIDI files).", 20, 5)

    def B(x):
        return f"dmxb[{x}]"

    def VLQ(x):
        x = f"({x})"
        b0, b1, b2, b3 = B(x), B(f"{x}+1"), B(f"{x}+2"), B(f"{x}+3")
        return (f"if({b0} < 128, {b0}, if({b1} < 128, ({b0} & 127) * 128 + {b1}, "
                f"if({b2} < 128, (({b0} & 127) * 128 + ({b1} & 127)) * 128 + {b2}, "
                f"((({b0} & 127) * 128 + ({b1} & 127)) * 128 + ({b2} & 127)) * 128 + {b3})))")

    def VLEN(x):
        x = f"({x})"
        return f"if({B(x)} < 128, 1, if({B(x + '+1')} < 128, 2, if({B(x + '+2')} < 128, 3, 4)))"

    def BE32(x):
        return f"{B(x)} * 16777216 + {B(x + '+1')} * 65536 + {B(x + '+2')} * 256 + {B(x + '+3')}"

    # ---- scan tunings/
    st = chain(lb, lb.obj("r $0-scanlib", 20, 30), ["t b b b"], 20, 55)
    msg_to(lb, st, "; engfiles clear", 200, 80, outlet=2)
    dts = chain(lb, msg_to(lb, st, "dir", 20, 80, outlet=1), ["pdcontrol", "t s s"], 20, 105)
    glob = lb.obj("file glob", 20, 180)
    lb.c(msg_to(lb, dts, "symbol $1/tunings/*.mid", 20, 155, outlet=1), 0, glob, 0)
    lb.c(msg_to(lb, dts, "symbol $1/tunings/*.MID", 180, 155), 0, glob, 0)
    to(lb, to(lb, glob, "list split 1", 20, 205), "text insert engfiles 1e+06", 20, 230)
    sz = chain(lb, st, ["t b b", "text size engfiles"], 350, 80)
    lb.c(st, 0, sz - 1, 0)
    lb.conns.remove((st, 0, sz - 1, 0))
    to(lb, sz, "v dmxcount", 350, 130)
    msg_to(lb, sz - 1, "; engfiles sort", 450, 105, outlet=1)
    # ---- knob 1 selects
    ks = chain(lb, lb.obj("r $0-k1p6", 600, 30),
               ["expr if(dmxcount > 0, min(int($f1 * dmxcount), dmxcount - 1), 0)", "change -1", "t b f"], 600, 55)
    to(lb, ks, "v dmxsel", 680, 130, outlet=1)
    to(lb, ks, "s $0-libdraw", 600, 130)
    to(lb, lb.obj("r $0-refresh6", 750, 105), "s $0-libdraw", 750, 130)
    # ---- draw
    disp = lb.obj("s $0-disp6", 20, 700)
    rt = chain(lb, lb.obj("r $0-libdraw", 20, 300), ["t b b b b b"], 20, 325)
    lb.c(msg_to(lb, to(lb, rt, "v dmxcount", 20, 350, outlet=4), "1 Tunings ($1)", 20, 375), 0, disp, 0)
    for row in range(3):
        x = 200 + row * 330
        ix = to(lb, rt, f"expr min(max(dmxsel - 1, 0), max(dmxcount - 3, 0)) + {row}", x, 350, outlet=3 - row)
        it = to(lb, ix, "t f f f", x, 375)
        vx = to(lb, it, "expr $f1 < dmxcount", x + 200, 400, outlet=2)
        sp = lb.obj("spigot", x, 450)
        lb.c(vx, 0, sp, 1)
        lb.c(msg_to(lb, to(lb, vx, "sel 0", x + 200, 425), f"{row + 2} -", x + 200, 450), 0, disp, 0)
        msel = chain(lb, it, ["expr $f1 == dmxsel", "sel 1 0"], x + 100, 400, outlet=1)
        pk = lb.obj("pack s s", x, 600)
        lb.c(msg_to(lb, msel, "symbol >", x + 100, 450), 0, pk, 1)
        lb.c(msg_to(lb, msel, "symbol .", x + 160, 450, outlet=1), 0, pk, 1)
        lb.c(it, 0, sp, 0)
        sn = chain(lb, sp, ["text get engfiles", "file splitext", "list split 1", "file splitname"], x, 475)
        lb.c(to(lb, sn, "list split 1", x, 575), 1, pk, 0)
        lb.c(sn, 1, pk, 0)
        lb.c(msg_to(lb, pk, f"{row + 2} $2 $1", x, 625), 0, disp, 0)
    stl = lb.obj("list", 20, 600)
    lb.c(lb.obj("r $0-libstat", 100, 575), 0, stl, 1)
    lb.c(rt, 0, stl, 0)
    lb.c(to(lb, stl, "list prepend 5", 20, 625), 0, disp, 0)
    lb.c(to(lb, lb.obj("r $0-libstat", 200, 650), "list prepend 5", 200, 675), 0, disp, 0)
    lb.c(msg_to(lb, lb.obj("loadbang", 350, 575), "Aux: send to DM48X", 350, 600), 0, stl, 1)
    sstat = lb.obj("s $0-libstat", 800, 1250)

    # ---- send (Aux on the LIBRARY page)
    ag = lb.obj("spigot", 1100, 55)
    lb.c(lb.obj("r aux", 1100, 30), 0, ag, 0)
    lb.c(lb.obj(f"r $0-g{LIB}", 1170, 30), 0, ag, 1)
    hs = chain(lb, ag, ["sel 1", "expr dmxcount > 0", "sel 1 0"], 1100, 80)
    lb.c(msg_to(lb, hs, "No tunings found", 1250, 155, outlet=1), 0, sstat, 0)
    go = to(lb, hs, "t b b b", 1100, 180)
    stopm = msg_to(lb, go, "stop", 1300, 205, outlet=2)
    lb.c(msg_to(lb, go, "Sending...", 1360, 205, outlet=2), 0, sstat, 0)
    setv(lb, go, "engsending", 1, 1550, 205, outlet=2)
    setv(lb, go, "engrxmute", 1, 1650, 205, outlet=2)
    to(lb, go, "s $0-outcheck", 1600, 205, outlet=2)
    # any other status = finished: echo back on
    nd = chain(lb, lb.obj("r $0-libstat", 1300, 1200), ["route Sending..."], 1300, 1225)
    ndt = to(lb, nd, "t b b", 1400, 1250, outlet=1)
    setv(lb, ndt, "engsending", 0, 1450, 1275, outlet=1)
    # keep ignoring what the DM48X sends (echoed tuning notes, a breath jump as it restarts) for a moment longer
    setv(lb, to(lb, ndt, "delay 600", 1600, 1275, outlet=1), "engrxmute", 0, 1600, 1300)
    to(lb, ndt, "s $0-outcheck", 1400, 1300)
    setv(lb, go, "dmxn", 0, 1450, 205, outlet=2)
    setv(lb, go, "dmxc", 0, 1500, 205, outlet=2)
    bt = chain(lb, go, ["v dmxsel", "text get engfiles"], 1100, 205, outlet=1)
    fh = chain(lb, msg_to(lb, bt, f"open $1, {MAXBYTES}, close", 1100, 255), ["file handle", "t a a"], 1100, 280)
    to(lb, to(lb, fh, "list length", 1200, 330, outlet=1), "v dmxn", 1200, 355)
    to(lb, fh, "array set dmxb", 1100, 330)
    hs2 = chain(lb, go, ["expr (dmxn > 22) && (dmxb[0] == 77) && (dmxb[1] == 84) && (dmxb[2] == 104) && (dmxb[3] == 100)",
                         "sel 1 0"], 1100, 400)
    lb.c(msg_to(lb, hs2, "Not a MIDI file", 1300, 450, outlet=1), 0, sstat, 0)
    pinit = to(lb, hs2, "t b b b b", 1100, 450)
    to(lb, to(lb, pinit, "expr if((dmxb[12] < 128) && (dmxb[12] * 256 + dmxb[13] > 0), dmxb[12] * 256 + dmxb[13], 480)",
              1350, 500, outlet=3), "v dmxd", 1350, 525)
    ptt = chain(lb, pinit, [f"expr 8 + {BE32('4')}", "t f f"], 1200, 500, outlet=2)
    to(lb, ptt, "v dmxe", 1260, 550, outlet=1)
    to(lb, ptt, "v dmxp", 1200, 550)
    z3 = msg_to(lb, pinit, "0", 1100, 500, outlet=2)
    for i, nm in enumerate(("dmxk", "dmxr")):
        to(lb, z3, f"v {nm}", 1100 + i * 50, 525)
    until = to(lb, msg_to(lb, pinit, "200000", 1000, 500, outlet=1), "until", 1000, 525)
    # one parse step
    step = Canvas("parse-step", w=1500, h=900)
    cs = chain(step, step.obj("inlet", 20, 20),
               [f"expr if((dmxp >= dmxe) || (dmxc >= {MAXEV}), if((dmxp + 8 > dmxn) || (dmxc >= {MAXEV}), 0, 1), 2)",
                "sel 0 1 2"], 20, 45)
    to(step, cs, "outlet", 20, 860)
    c1 = to(step, cs, "t b b b", 200, 100, outlet=1)
    to(step, to(step, c1, f"expr dmxp + 8 + {BE32('dmxp+4')}", 400, 130, outlet=2), "v dmxe", 400, 155)
    to(step, to(step, c1, "expr if((dmxb[dmxp] == 77) && (dmxb[dmxp+1] == 84) && (dmxb[dmxp+2] == 114) && "
                          "(dmxb[dmxp+3] == 107), dmxp + 8, dmxe)", 300, 185, outlet=1), "v dmxp", 300, 210)
    zz = msg_to(step, c1, "0", 200, 185)
    to(step, zz, "v dmxk", 200, 210)
    to(step, zz, "v dmxr", 250, 235)
    c2 = to(step, cs, "t b b b b b b b", 20, 300, outlet=2)
    to(step, to(step, c2, f"expr dmxk + {VLQ('dmxp')}", 700, 330, outlet=6), "v dmxk", 700, 355)
    to(step, to(step, c2, f"expr dmxp + {VLEN('dmxp')}", 600, 380, outlet=5), "v dmxp", 600, 405)
    to(step, to(step, c2, "expr if(dmxb[dmxp] >= 128, dmxb[dmxp], dmxr)", 500, 430, outlet=4), "v dmxst", 500, 455)
    to(step, to(step, c2, "expr if(dmxst < 240, dmxst, dmxr)", 400, 480, outlet=3), "v dmxr", 400, 505)
    to(step, to(step, c2, "expr dmxp + (dmxb[dmxp] >= 128)", 300, 530, outlet=2), "v dmxp", 300, 555)
    wr = chain(step, c2, ["expr ((dmxst & 240) == 144) || ((dmxst & 240) == 128)", "sel 1", "t b b b b b"],
               200, 580, outlet=1)
    cvt = chain(step, wr, ["v dmxc", "t f f f f"], 800, 655, outlet=4)
    for i, (arr, src) in enumerate((("dmxt", "dmxk"), ("dmxs", "dmxst"), ("dmx1", "dmxb[dmxp]"), ("dmx2", "dmxb[dmxp+1]"))):
        x = 300 + i * 120
        vx = to(step, wr, f"expr {src}", x, 705, outlet=3 if i < 2 else (2 if i == 2 else 1))
        tw = to(step, vx, f"tabwrite {arr}", x, 730)
        step.c(cvt, i, tw, 1)
    to(step, to(step, wr, "expr dmxc + 1", 200, 760), "v dmxc", 200, 785)
    adv = ("expr if(dmxst < 128, dmxe, if(dmxst == 255, if(dmxb[dmxp] == 47, dmxe, dmxp + 1 + "
           + VLEN("dmxp+1") + " + " + VLQ("dmxp+1") + "), if((dmxst == 240) || (dmxst == 247), dmxp + "
           + VLEN("dmxp") + " + " + VLQ("dmxp") + ", dmxp + if(((dmxst & 240) == 192) || ((dmxst & 240) == 208), 1, 2))))")
    to(step, to(step, c2, adv, 20, 810), "v dmxp", 20, 835)
    ps = lb.sub(step, 1000, 550)
    lb.c(until, 0, ps, 0)
    lb.c(ps, 0, until, 1)
    gs = chain(lb, pinit, ["v dmxc", "moses 1"], 1100, 600)
    lb.c(msg_to(lb, gs, "No notes in file", 1250, 650), 0, sstat, 0)
    pstart = to(lb, gs, "t b b", 1100, 650, outlet=1)
    setv(lb, pstart, "dmxi", 0, 1160, 675, outlet=1)
    play = Canvas("play-step", w=1000, h=500)
    pin = play.obj("inlet", 20, 20)
    more = to(play, pin, "expr dmxi < dmxc", 20, 45)
    msl = to(play, more, "sel 1 0", 20, 70)
    to(play, msl, "outlet", 300, 450, outlet=1)
    pt = to(play, msl, "t b b b b", 20, 100)
    ev = to(play, pt, "expr dmx1[dmxi]; if((dmxs[dmxi] & 240) == 128, 0, dmx2[dmxi]); (dmxs[dmxi] & 15) + 1",
            400, 130, outlet=3)
    evp = play.obj("pack 0 0 0", 400, 160)
    for k in (2, 1, 0):
        play.c(ev, k, evp, k)
    to(play, evp, "noteout", 400, 190)
    to(play, evp, "s dmx-sent", 500, 190)
    dl = play.obj("delay", 20, 300)
    play.c(to(play, pt, "expr if(dmxi + 1 < dmxc, max(5, min(30, (dmxt[dmxi+1] - dmxt[dmxi]) * 500 / dmxd)), 0)",
              200, 230, outlet=2), 0, dl, 1)
    to(play, to(play, pt, "expr dmxi + 1", 100, 260, outlet=1), "v dmxi", 100, 285)
    play.c(pt, 0, dl, 0)
    play.c(dl, 0, more, 0)
    play.c(play.obj("inlet", 200, 20), 0, dl, 0)
    pl = lb.sub(play, 1100, 700)
    lb.c(pstart, 0, pl, 0)
    lb.c(stopm, 0, pl, 1)
    pdn = to(lb, pl, "t b b", 1100, 725)
    done = to(lb, pdn, "v dmxc", 1100, 750, outlet=1)
    lb.c(msg_to(lb, done, "Sent! $1 notes", 1100, 800), 0, sstat, 0)
    # a tuning named "... D" / "... Bb" / "... F#" sets the synth's TUNE key, so just intonation matches the harp
    nm = chain(lb, bt, ["file splitext", "list split 1", "list fromsymbol", "list prepend 0 0 0", "t a a"], 1700, 230)
    spl = lb.obj("list split", 1700, 330)
    lb.c(chain(lb, nm, ["list length", "- 3"], 1800, 255, outlet=1), 0, spl, 1)
    lb.c(nm, 0, spl, 0)
    N = lambda c: f"(({c} == 65) * 9 + ({c} == 66) * 11 + ({c} == 68) * 2 + ({c} == 69) * 4 + ({c} == 70) * 5 + ({c} == 71) * 7)"
    L = lambda c: f"(({c} >= 65) && ({c} <= 71))"
    kx = (f"expr if({L('$f3')} && ($f2 == 32), {N('$f3')}, if(($f3 == 98) && {L('$f2')} && ($f1 == 32), ({N('$f2')} + 11) % 12, "
          f"if(($f3 == 35) && {L('$f2')} && ($f1 == 32), ({N('$f2')} + 1) % 12, -1)))")
    to(lb, chain(lb, spl, [kx], 1700, 355, outlet=1), "v dmxkey", 1700, 380)
    kk = chain(lb, pdn, ["expr dmxkey", "moses 0"], 1250, 750)
    kt = to(lb, kk, "t f f", 1300, 800, outlet=1)
    to(lb, kt, "s $0-key", 1400, 825, outlet=1)
    kn = chain(lb, msg_to(lb, kt, "get $1 1", 1300, 825), [f"list store {NOTE_NAMES}"], 1300, 850)
    lb.c(msg_to(lb, kn, "Sent! Synth key $1", 1300, 875), 0, sstat, 0)
    return lb


def allpass(c, x, y, src, name, ms, g=0.6):
    rd = c.obj(f"delread~ {name} {ms}", x + 120, y)
    gm = to(c, rd, f"*~ {g}", x + 120, y + 25)
    w = c.obj("+~", x, y + 50)
    c.c(src, 0, w, 0)
    c.c(gm, 0, w, 1)
    to(c, w, f"delwrite~ {name} 50", x + 120, y + 75)
    ng = to(c, w, f"*~ {-g}", x, y + 100)
    o = c.obj("+~", x, y + 125)
    c.c(ng, 0, o, 0)
    c.c(rd, 0, o, 1)
    return o


def mul(c, a, b, x, y, ao=0, bo=0):
    o = c.obj("*~", x, y)
    c.c(a, ao, o, 0)
    c.c(b, bo, o, 1)
    return o


def add(c, a, b, x, y, ao=0, bo=0):
    o = c.obj("+~", x, y)
    c.c(a, ao, o, 0)
    c.c(b, bo, o, 1)
    return o


def smooth(c, recv, ms, x, y, scale=None):
    """[r recv] -> (scale) -> [$1 ms( -> [line~]"""
    objs = [scale] if scale else []
    last = chain(c, c.obj(f"r {recv}", x, y), objs, x, y + 25)
    return to(c, msg_to(c, last, f"$1 {ms}", x, y + 25 + 25 * len(objs)), "line~", x, y + 50 + 25 * len(objs))


def audio():
    a = Canvas("audio-fx", w=1800, h=1400)
    a.comment("Engine params -> signals, vibrato, then master FX: ping-pong delay, reverb (with freeze), limiter", 20, 5)
    for k in range(1, 5):
        to(a, smooth(a, f"eng-p{k}", 30, 20 + (k - 1) * 110, 30), f"s~ eng-p{k}~", 20 + (k - 1) * 110, 105)
    # per-slot knob values: the PLAY knobs go to the slot of the current engine (engbus 0 = A, 1 = B)
    for k in range(1, 5):
        rk = a.obj(f"r eng-p{k}", 1300 + (k - 1) * 120, 30)
        for i, X in enumerate("AB"):
            g = chain(a, rk, [f"expr if(engbus == {i}, $f1, -1)", "moses 0"], 1300 + (k - 1) * 120 + i * 60, 55 + i * 50)
            to(a, g, f"s eng-{X}-p{k}", 1300 + (k - 1) * 120 + i * 60, 105 + i * 50, outlet=1)
            to(a, smooth(a, f"eng-{X}-p{k}", 30, 1300 + (k - 1) * 120 + i * 60, 160 + i * 100),
               f"s~ eng-{X}-p{k}~", 1300 + (k - 1) * 120 + i * 60, 235 + i * 100)
    xfl = chain(a, a.obj("r eng-xfade", 1800, 30), ["line~"], 1800, 55)
    to(a, xfl, "s~ eng-xf~", 1800, 80)
    for i, nm in enumerate(("bamt", "body")):
        to(a, smooth(a, f"eng-{nm}", 30, 480 + i * 110, 30), f"s~ eng-{nm}~", 480 + i * 110, 105)
    srs = chain(a, a.obj("loadbang", 720, 30), ["samplerate~", "/ 2.5", "sig~"], 720, 55)
    to(a, srs, "s~ eng-sawk", 720, 130)
    lfo = to(a, a.obj("r eng-vibrate", 850, 30), "osc~ 5.5", 850, 55)
    to(a, mul(a, lfo, smooth(a, "eng-vibdepth", 50, 950, 30), 850, 130), "s~ eng-vib", 850, 155)
    # ---- dry
    lvl = smooth(a, "eng-level", 50, 200, 200, scale="* 1.4")
    dry0 = mul(a, to(a, a.obj("r~ eng-dry", 20, 200), "*~ 0.5", 20, 225), lvl, 20, 300)
    # audio looper: "pre" records here and plays back into the effects
    to(a, dry0, "s~ eng-tap-pre", 120, 325)
    dry = add(a, dry0, a.obj("r~ eng-aret-pre", 120, 300), 20, 325)
    # ---- delay (stereo ping-pong): input -> L, L -> R, R -> L
    dtm = smooth(a, "eng-dtime", 150, 400, 200)
    thr = smooth(a, "eng-throw", 30, 550, 200)
    fb = smooth(a, "eng-dfb", 50, 700, 200)
    tfb = smooth(a, "eng-throwfb", 50, 620, 300)
    fbe = a.obj("expr~ min(1.05, max($v1, $v2 * $v3))", 700, 300)
    a.c(fb, 0, fbe, 0)
    a.c(thr, 0, fbe, 1)
    a.c(tfb, 0, fbe, 2)
    dmix = smooth(a, "eng-dmix", 50, 850, 200)
    dmx = a.obj("expr~ max($v1, $v2 * 0.6)", 850, 300)
    a.c(dmix, 0, dmx, 0)
    a.c(thr, 0, dmx, 1)
    dL = a.obj("delread4~ $0-dl", 300, 400)
    dR = a.obj("delread4~ $0-dr", 500, 400)
    a.c(dtm, 0, dL, 0)
    a.c(dtm, 0, dR, 0)
    toneL = chain(a, dL, ["lop~ 4500", "hip~ 60"], 300, 425)
    toneR = chain(a, dR, ["lop~ 4500", "hip~ 60"], 500, 425)
    fR = mul(a, toneR, fbe, 300, 480)
    inL = add(a, dry, fR, 300, 505)
    to(a, inL, "delwrite~ $0-dl 2000", 300, 530)
    fL = mul(a, toneL, fbe, 500, 480)
    to(a, fL, "delwrite~ $0-dr 2000", 500, 530)
    dOutL = mul(a, toneL, dmx, 300, 570)
    dOutR = mul(a, toneR, dmx, 500, 570)
    # ---- reverb: 4 combs + 2 allpasses per side, freeze holds the tail
    frz = smooth(a, "eng-freeze", 80, 900, 400)
    ingain = to(a, frz, "*~ -1", 900, 475)
    ingain = to(a, ingain, "+~ 1", 900, 500)
    rin = add(a, dry, add(a, dOutL, dOutR, 300, 620), 20, 650)
    rin = mul(a, rin, ingain, 20, 675)
    rin = to(a, rin, "*~ 0.5", 20, 700)
    # 8-line feedback delay network (after VerbRack): input diffusion -> 8 modulated delays mixed by a
    # Hadamard matrix; each line loses treble faster than bass (lows ring 1.3x longer). Size = decay time.
    LENS = [37.3, 43.1, 49.7, 56.9, 63.7, 71.3, 79.1, 87.7]
    for i, (ms, g) in enumerate(((4.77, 0.6), (3.59, 0.6), (12.73, 0.55), (9.31, 0.55))):
        rin = allpass(a, 1300, 400 + i * 150, rin, f"$0-rd{i}", ms, g)
    # loop gains at control rate: T60 = 1.2 .. 15 s from Size; freeze = hold (no loss, no input)
    gsrc = a.obj("expr engrsize; engfreeze", 1600, 300)
    for nm, rcv, x in (("engrsize", "eng-rsize", 1600), ("engfreeze", "eng-freeze", 1700)):
        tv = to(a, a.obj(f"r {rcv}", x, 250), "t b f", x, 275)
        to(a, tv, f"v {nm}", x + 40, 300, outlet=1)
        a.c(tv, 0, gsrc, 0)
    T60 = "(1.2 + engrsize * engrsize * 14)"
    gx = []
    for i, L in enumerate(LENS):
        gx.append(f"if(engfreeze > 0.5, 0.9998, exp(-6.9078 * {L} / 1000 / {T60}))")
        gx.append(f"if(engfreeze > 0.5, 0.9998, exp(-6.9078 * {L} / 1000 / ({T60} * 1.3)))")
    ge = a.obj("expr " + "; ".join(gx), 1600, 330)
    a.c(gsrc, 0, ge, 0)
    gl = []
    for j in range(16):
        gl.append(to(a, msg_to(a, ge, "$1 80", 1600 + j * 45, 360, outlet=j), "line~", 1600 + j * 45, 385))
    lfo = to(a, a.obj("r eng-rmod", 1300, 1000), "phasor~ 0.31", 1300, 1025)
    ins = []
    for i, L in enumerate(LENS):
        x = 20 + i * 210
        ph = to(a, lfo, f"+~ {i / 8}", x + 100, 1060)
        md = to(a, to(a, ph, "cos~", x + 100, 1085), f"*~ {0.35 if i % 2 == 0 else -0.35}", x + 100, 1110)
        tm = to(a, md, f"+~ {L}", x + 100, 1135)
        rd = a.obj(f"delread4~ $0-fdn{i}", x, 1160)
        a.c(tm, 0, rd, 0)
        hi = to(a, rd, "lop~ 5500", x, 1185)
        lo = to(a, rd, "lop~ 250", x + 70, 1185)
        dmp = a.obj("expr~ $v1 * $v3 + $v2 * ($v4 - $v3)", x, 1210)
        a.c(hi, 0, dmp, 0)
        a.c(lo, 0, dmp, 1)
        a.c(gl[2 * i], 0, dmp, 2)
        a.c(gl[2 * i + 1], 0, dmp, 3)
        ins.append(dmp)
    # Hadamard 8x8 in three butterfly stages
    v = [(n, 0) for n in ins]
    for stage, step in enumerate((1, 2, 4)):
        nv = [None] * 8
        for i in range(8):
            if i & step:
                continue
            bf = a.obj("expr~ ($v1 + $v2)" + ("*0.35355" if step == 4 else "") + "; ($v1 - $v2)" +
                       ("*0.35355" if step == 4 else ""), 20 + i * 210, 1250 + stage * 30)
            a.c(v[i][0], v[i][1], bf, 0)
            a.c(v[i + step][0], v[i + step][1], bf, 1)
            nv[i], nv[i + step] = (bf, 0), (bf, 1)
        v = nv
    outsL, outsR = [], []
    for i in range(8):
        x = 20 + i * 210
        w = a.obj(f"expr~ $v1 + $v2 * {0.45 if i % 2 == 0 else -0.45}", x, 1350)
        a.c(v[i][0], v[i][1], w, 0)
        a.c(rin, 0, w, 1)
        to(a, w, f"delwrite~ $0-fdn{i} 300", x, 1375)
    lsum = a.obj("expr~ ($v1 - $v2 + $v3 - $v4) * 0.85", 20, 1420)
    rsum = a.obj("expr~ ($v1 - $v2 + $v3 - $v4) * 0.85", 400, 1420)
    for j in range(4):
        a.c(ins[2 * j], 0, lsum, j)
        a.c(ins[2 * j + 1], 0, rsum, j)
    apL, apR = lsum, rsum
    rmix = smooth(a, "eng-rmix", 50, 1000, 700, scale="* 0.6")
    wet = smooth(a, "eng-wetonly", 100, 1150, 700)
    dryg = to(a, to(a, wet, "*~ -1", 1150, 775), "+~ 1", 1150, 800)
    # ---- mix + limiter
    sides = []
    for s_, ap, dout, x in (("L", apL, dOutL, 20), ("R", apR, dOutR, 400)):
        dd = mul(a, dry, dryg, x, 1100)
        rv = mul(a, ap, rmix, x + 100, 1100)
        m1 = add(a, dd, dout, x, 1125)
        sd = add(a, m1, rv, x, 1150)
        # audio looper: "post" records the finished sound here and plays back after the effects
        to(a, sd, f"s~ eng-tap-post{s_}", x + 200, 1150)
        sides.append(add(a, sd, a.obj(f"r~ eng-aret-{s_}", x + 200, 1175), x, 1175))
    # level detector on L+R, gain = min(1, threshold / level)
    det = add(a, sides[0], sides[1], 800, 1175)
    to(a, det, "s~ eng-scope", 950, 1200)       # for the OLED scope
    gr = chain(a, det, ["env~ 1024 256", "expr if($f1 > 92, $f1 - 92, 0)", "expr pow(10, -$f1 / 20)",
                        "pack 0 30", "line~"], 800, 1200)
    for i, (s_, x) in enumerate((("L", 20), ("R", 400))):
        g = mul(a, sides[i], gr, x, 1200)
        yc = to(a, g, "clip~ -1.5 1.5", x, 1225)
        y2 = mul(a, yc, yc, x + 80, 1250)
        y3 = mul(a, y2, yc, x + 80, 1275)
        y3s = to(a, y3, "*~ -0.148148", x + 80, 1300)
        to(a, add(a, yc, y3s, x, 1325), f"throw~ out{s_}", x, 1350)
    return a


def glue():
    g = Canvas("glue", w=900, h=400)
    # octave = SETUP octave + key shift
    ob = to(g, g.obj("r $0-octbase", 20, 20), "v engoctb", 20, 45)
    osf = to(g, g.obj("r eng-octshift", 200, 20), "v engocts", 200, 45)
    ex = g.obj("expr engoctb + engocts", 20, 100)
    g.c(to(g, ob, "t b", 20, 70), 0, ex, 0)
    g.c(to(g, osf, "t b", 200, 70), 0, ex, 0)
    to(g, ex, "s eng-octave", 20, 125)
    # tap tempo ms -> FX page delay knob value
    to(g, to(g, g.obj("r eng-dtime-ms", 400, 20), "expr sqrt(max(0, min(1, ($f1 - 20) / 1480)))", 400, 45),
       "s $0-dtime", 400, 70)
    # toast: a short message on line 5, then back to the normal line
    tt = chain(g, g.obj("r $0-toast", 20, 200), ["t b a"], 20, 225)
    sp = to(g, tt, "spigot 1", 20, 275, outlet=1)
    g.c(g.obj("r $0-notlib", 100, 250), 0, sp, 1)
    to(g, sp, "s screenLine5", 20, 300)
    to(g, to(g, tt, "delay 1500", 150, 275), "s $0-l5", 150, 300)
    return g

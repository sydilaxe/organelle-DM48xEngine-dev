"""MIDI looper with overdub layers, variable speed and reverse.

The loop is the text 'englp', one line per event:  time layer kind ch a b
Layer 1 = first take, 2..7 = overdubs. Playback sends an event to internal channel
17 * layer + ch, so loop notes never collide with live notes or with each other.

Loop position: cur = anchor + speed * (ms since anchor), wrapped into [0, length).
Speed: 1 = normal, 0.25..4 forward, -0.25..-4 reverse. In reverse, events are visited
backwards and note-ons / note-offs swap roles.
States (englstate): 0 empty, 1 REC, 2 PLAY, 3 DUB, 4 STOP.
"""
from pdgen import Canvas
from sec_core import track_on, NCH, chain, to, msg_to, setv, tabwrite_pair

# forward: wrap into [0, len); reverse: wrap into (0, len] so a reverse cycle starts at the end, not at 0
CUR = ("expr if(engllen > 0, if(englspd > 0, (englanc + englspd * englpos) - engllen * "
       "floor((englanc + englspd * englpos) / engllen), engllen - ((engllen - englanc - englspd * englpos) - engllen * "
       "floor((engllen - englanc - englspd * englpos) / engllen))), englpos)")


def looper():
    lp = Canvas("looper", w=2000, h=1800)
    lp.comment("Loop text 'englp': time layer kind ch a b. Playback channel = 17 * layer + ch. "
               "States: 0 empty 1 REC 2 PLAY 3 DUB 4 STOP. Position = anchor + speed * elapsed.", 20, 5)

    # ---- clock: [s $0-treset] re-anchors, [s $0-cur] computes the loop position into [v englcur]
    tm = lp.obj("timer", 1700, 60)
    lp.c(lp.obj("r $0-treset", 1700, 35), 0, tm, 0)
    cb = chain(lp, lp.obj("r $0-cur", 1800, 10), ["t b b"], 1800, 35)
    lp.c(cb, 1, tm, 1)
    to(lp, tm, "v englpos", 1700, 85)
    to(lp, to(lp, cb, CUR, 1800, 110), "v englcur", 1800, 135)
    # re-anchor at the current position: [s $0-anchor]
    an = chain(lp, lp.obj("r $0-anchor", 1700, 170), ["t b b b"], 1700, 195)
    lp.c(an, 2, lp.obj("s $0-cur", 1800, 220), 0)
    to(lp, to(lp, an, "v englcur", 1700, 245, outlet=1), "v englanc", 1700, 270)
    to(lp, an, "s $0-treset", 1780, 270)

    # ---- status text + LED: [s $0-lstat] bang -> "PLAY x2", "PLAY x2 <1.5" (reverse 1.5x), ">2" (forward 2x)
    st = lp.obj("t b b b", 1500, 350)
    lp.c(lp.obj("r $0-lstat", 1500, 325), 0, st, 0)
    sls = lp.obj("s eng-loopstat", 1500, 640)
    pk = lp.obj("pack s 0 0", 1500, 480)
    sx = to(lp, st, "expr int(abs(englspd) * 10 + 0.5) / 10; if(englspd == 1, 0, if(englspd > 0, 1, 2))", 1750, 375, outlet=2)
    lp.c(sx, 0, pk, 2)
    gates = [lp.obj("spigot", 1500 + i * 110, 530) for i in range(3)]
    dsel = to(lp, sx, "t f f f", 1850, 400, outlet=1)
    for i in range(3):
        lp.c(to(lp, dsel, f"== {i}", 1850 + i * 50, 425, outlet=i), 0, gates[i], 1)
    lp.c(to(lp, st, "v engltop", 1650, 375, outlet=1), 0, pk, 1)
    lss = chain(lp, st, ["v englstate", "sel 0 1 2 3 4"], 1500, 375)
    sled = lp.obj("s led", 1950, 460)
    lp.c(msg_to(lp, lss, "list no loop", 1450, 425), 0, sls, 0)
    for i, (txt, led) in enumerate((("-", 0), ("rec", 1), ("loop", 3), ("dub", 2), ("stop", 5))):
        if i:
            lp.c(msg_to(lp, lss, f"symbol {txt}", 1500 + i * 55, 425, outlet=i), 0, pk, 0)
        lp.c(msg_to(lp, lss, str(led), 1950, 350 + i * 20, outlet=i), 0, sled, 0)
    for i, fmt in enumerate(("$1 x$2", "$1 x$2 >$3", "$1 x$2 <$3")):
        lp.c(pk, 0, gates[i], 0)
        lp.c(msg_to(lp, gates[i], fmt, 1500 + i * 110, 560), 0, sls, 0)

    # ---- recorder
    rrt = chain(lp, lp.obj("r eng-rec", 20, 40), ["t a a"], 20, 65)
    rn = to(lp, rrt, "route 0", 250, 90, outlet=1)
    track_on(lp, rn, "if($f1 < 17, $f1 * 128 + $f2, -1); $f3 > 0", "englivet", 250, 115)
    # the bend each live channel is at (raw + 1; 0 = never bent), so a new take or overdub starts from it
    to(lp, to(lp, rrt, "route 1", 600, 90, outlet=1), "expr if($f1 < 17, $f1, -1); $f2 + 1", 600, 115)
    bwx = len(lp.items) - 1
    bwm = to(lp, bwx, "moses 0", 600, 140)
    bwv = lp.obj("f", 700, 165)
    lp.c(bwx, 1, bwv, 1)
    bwt = to(lp, bwm, "t b f", 600, 165, outlet=1)
    bwr = lp.obj("tabwrite englbraw", 600, 215)
    lp.c(bwt, 1, bwr, 1)                     # index first
    lp.c(bwt, 0, bwv, 0)                     # then the value
    lp.c(bwv, 0, bwr, 0)
    rg = to(lp, rrt, "t a b", 20, 100)
    rsp = lp.obj("spigot", 20, 150)
    lp.c(to(lp, rg, "expr (englstate == 1) || (englstate == 3)", 100, 125, outlet=1), 0, rsp, 1)
    lp.c(rg, 0, rsp, 0)
    rst = to(lp, rsp, "t a b b", 20, 175)
    to(lp, rst, "s $0-cur", 150, 200, outlet=2)
    stamp = to(lp, rst, "expr englcur; if(englstate == 1, 1, engldub)", 100, 225, outlet=1)
    spk = lp.obj("pack 0 0", 100, 250)
    lp.c(stamp, 1, spk, 1)
    lp.c(stamp, 0, spk, 0)
    lpre = lp.obj("list prepend", 20, 280)
    lp.c(spk, 0, lpre, 1)
    lp.c(rst, 0, lpre, 0)
    tins = lp.obj("text insert englp 1e+06", 20, 330)
    lp.c(to(lp, lpre, "list trim", 20, 305), 0, tins, 0)

    # ---- bends at the start of a take / overdub: [s $0-bsnap] layer
    # A bend sent before recording started (the DM48X sends one only when it changes) would be missing from the
    # loop, and its notes would play unbent. Each bent live channel gets a bend event at time 0 of the layer.
    bsl = chain(lp, lp.obj("r $0-bsnap", 750, 230), ["t b b f"], 750, 255)
    bsc = lp.obj("f", 750, 330)
    lp.c(msg_to(lp, bsl, "0", 800, 280, outlet=1), 0, bsc, 1)            # reset the counter first
    lp.c(to(lp, msg_to(lp, bsl, "17", 750, 280, outlet=0), "until", 750, 305), 0, bsc, 0)
    lp.c(to(lp, bsc, "+ 1", 800, 355), 0, bsc, 1)
    bsx = lp.obj("expr if((englbraw[$f1] > 0) && (englbraw[$f1] != 8193), $f1, -1); $f2; englbraw[$f1] - 1", 750, 380)
    lp.c(bsc, 0, bsx, 0)
    lp.c(bsl, 2, bsx, 1)                                                 # the layer (cold)
    bsp = lp.obj("pack 0 0 0", 750, 430)
    lp.c(bsx, 2, bsp, 2)
    lp.c(bsx, 1, bsp, 1)
    lp.c(to(lp, bsx, "moses 0", 750, 405), 1, bsp, 0)
    lp.c(msg_to(lp, bsp, "0 $2 1 $1 $3 0", 750, 455), 0, lp.obj("text insert englp 1e+06", 750, 480), 0)

    # ---- close held live notes: [s $0-close] "pos layer"
    clu = chain(lp, lp.obj("r $0-close", 20, 400), ["unpack 0 0"], 20, 425)
    to(lp, clu, "v englclay", 120, 450, outlet=1)
    clt = to(lp, clu, "t b f", 20, 450)
    to(lp, clt, "v englcpos", 120, 475, outlet=1)
    # visit the live notes that are on (one line each in englivet)
    clc = lp.obj("f", 20, 550)
    lp.c(msg_to(lp, clt, "0", 20, 475), 0, clc, 1)
    un = chain(lp, msg_to(lp, clt, "bang", 60, 500), ["text size englivet", "until"], 60, 525)
    lp.c(un, 0, clc, 0)
    lp.c(to(lp, clc, "+ 1", 60, 575), 0, clc, 1)
    clmo = chain(lp, clc, ["text get englivet 0 1"], 20, 600)
    clx = to(lp, clmo, "expr englcpos; englclay; 0; int($f1 / 128); $f1 % 128; 0", 60, 650, outlet=0)
    clp = lp.obj("pack 0 0 0 0 0 0", 60, 675)
    for k in range(5, -1, -1):
        lp.c(clx, k, clp, k)
    lp.c(clp, 0, tins, 0)

    # ---- note-offs for sounding loop notes: [s $0-loopoff] "firstch lastch"
    # visit the loop notes that are on (englheldt), last line first: a note-off deletes its own line
    lox = chain(lp, lp.obj("r $0-loopoff", 450, 400), ["expr $f1 * 128; ($f2 + 1) * 128"], 450, 425)
    lot = to(lp, lox, "t b f", 450, 450)
    loc = lp.obj("f", 450, 525)
    lsz = chain(lp, lot, ["text size englheldt", "t f f"], 450, 475)
    lp.c(lsz, 1, loc, 1)
    lp.c(to(lp, lsz, "until", 500, 500), 0, loc, 0)
    ldn = to(lp, loc, "- 1", 500, 550)
    lp.c(ldn, 0, loc, 1)
    lkey = chain(lp, ldn, ["text get englheldt 0 1", "t f f"], 450, 575)
    lsp = lp.obj("spigot", 450, 600)
    # the range goes straight into the expr's cold inlets (an [f] in between would never send it on)
    lin = lp.obj("expr ($f1 >= $f2) && ($f1 < $f3)", 520, 600)
    lp.c(lkey, 1, lin, 0)
    lp.c(lot, 1, lin, 1)
    lp.c(lox, 1, lin, 2)
    lp.c(lin, 0, lsp, 1)
    lp.c(lkey, 0, lsp, 0)
    lom = lsp
    lox2 = to(lp, lom, "expr int($f1 / 128); $f1 % 128", 490, 625, outlet=0)
    lopk = lp.obj("pack 0 0", 490, 650)
    lp.c(lox2, 1, lopk, 1)
    lp.c(lox2, 0, lopk, 0)
    sproc = lp.obj("s eng-proc", 490, 700)
    lp.c(msg_to(lp, lopk, "0 $1 $2 0", 490, 675), 0, sproc, 0)

    # ---- player
    # cycle start: sort, count, start index (0 forward / n-1 reverse), anchor at 0 or length
    cyt = chain(lp, lp.obj("r $0-cycle", 850, 400), ["t b b b b b"], 850, 425)
    msg_to(lp, cyt, "; englp sort", 1000, 450, outlet=4)
    to(lp, to(lp, cyt, "text size englp", 900, 475, outlet=3), "v englnum", 900, 500)
    to(lp, to(lp, cyt, "expr if(englspd > 0, 0, englnum - 1)", 1000, 500, outlet=2), "v engli", 1000, 525)
    to(lp, to(lp, cyt, "expr if(englspd > 0, 0, engllen)", 1150, 500, outlet=1), "v englanc", 1150, 525)
    lp.c(cyt, 1, lp.obj("s $0-treset", 1150, 550), 0)
    to(lp, cyt, "s $0-pstep", 850, 555)
    # step
    fwd = chain(lp, lp.obj("r $0-pstep", 850, 600), ["t b b", "expr englspd > 0", "sel 1 0"], 850, 625)
    lp.c(len(lp.items) - 3, 1, lp.obj("s $0-cur", 950, 650), 0)
    # forward
    fm = chain(lp, fwd, ["expr engli < englnum", "sel 1 0"], 850, 700)
    pdl = lp.obj("delay", 850, 850)
    fw = chain(lp, fm, ["v engli", "text get englp 0 1", "expr max(0, ($f1 - englcur) / englspd)"], 850, 750)
    lp.c(fw, 0, pdl, 0)
    wdl = lp.obj("delay", 1150, 850)
    lp.c(to(lp, fm, "expr max(1, (engllen - englcur) / englspd)", 1150, 750, outlet=1), 0, wdl, 0)
    # reverse
    rm = chain(lp, fwd, ["expr engli >= 0", "sel 1 0"], 1350, 700, outlet=1)
    rw = chain(lp, rm, ["v engli", "text get englp 0 1", "expr max(0, (englcur - $f1) / abs(englspd))"], 1350, 750)
    lp.c(rw, 0, pdl, 0)
    lp.c(to(lp, rm, "expr max(1, englcur / abs(englspd))", 1550, 750, outlet=1), 0, wdl, 0)
    # fire: emit event i (in reverse, note-on <-> note-off), then i +/- 1
    ft = to(lp, pdl, "t b b", 850, 875)
    fx = chain(lp, ft, ["v engli", "text get englp",
                        "expr $f3; 17 * $f2 + $f4; $f5; if(($f3 == 0) && (englspd < 0), if($f6 > 0, 0, 90), $f6)"],
               950, 900, outlet=1)
    fpk = lp.obj("pack 0 0 0 0", 950, 975)
    for k in (3, 2, 1, 0):
        lp.c(fx, k, fpk, k)
    lp.c(fpk, 0, sproc, 0)
    fit = chain(lp, ft, ["expr engli + if(englspd > 0, 1, -1)", "t b f"], 850, 1000)
    to(lp, fit, "v engli", 920, 1050, outlet=1)
    to(lp, fit, "s $0-pstep", 850, 1050)
    # loop end reached: start the next cycle
    wsel = chain(lp, wdl, ["expr (englstate == 2) || (englstate == 3)", "sel 1"], 1150, 875)
    to(lp, wsel, "s $0-cycle", 1150, 925)
    stm = msg_to(lp, lp.obj("r $0-pstop", 1350, 875), "stop", 1350, 900)
    lp.c(stm, 0, pdl, 0)
    lp.c(stm, 0, wdl, 0)

    # ---- resync: after a speed change or undo, continue from "now" ([s $0-resync])
    ry = chain(lp, lp.obj("r $0-resync", 1350, 1000), ["t b b b b b b"], 1350, 1025)
    to(lp, ry, "s $0-pstop", 1550, 1050, outlet=5)
    msg_to(lp, ry, "; englp sort", 1550, 1075, outlet=4)
    to(lp, to(lp, ry, "text size englp", 1450, 1100, outlet=3), "v englnum", 1450, 1125)
    to(lp, ry, "s $0-cur", 1550, 1125, outlet=3)
    # count the events before the current position
    cnt = lp.obj("f", 1350, 1300)
    z0 = msg_to(lp, ry, "0", 1400, 1150, outlet=2)
    lp.c(z0, 0, cnt, 1)
    ic = lp.obj("f", 1500, 1200)
    lp.c(msg_to(lp, ry, "0", 1500, 1150, outlet=2), 0, ic, 1)
    un2 = to(lp, to(lp, ry, "v englnum", 1600, 1150, outlet=1), "until", 1600, 1175)
    lp.c(un2, 0, ic, 0)
    lp.c(to(lp, ic, "+ 1", 1550, 1225), 0, ic, 1)
    bs = chain(lp, ic, ["text get englp 0 1", "expr $f1 < englcur", "sel 1"], 1500, 1250)
    lp.c(bs, 0, cnt, 0)
    lp.c(to(lp, cnt, "+ 1", 1400, 1325), 0, cnt, 1)
    # index: forward = count, reverse = count - 1 ([f] holds count - 0 after the scan: read it)
    rd = to(lp, ry, "t b b", 1350, 1375)
    cv = lp.obj("f", 1350, 1425)
    lp.c(to(lp, cnt, "+ 1", 1250, 1325), 0, cv, 1)
    lp.c(z0, 0, cv, 1)
    lp.c(rd, 1, cv, 0)
    to(lp, to(lp, cv, "expr if(englspd > 0, $f1, $f1 - 1)", 1350, 1450), "v engli", 1350, 1475)
    to(lp, chain(lp, rd, ["expr (englstate == 2) || (englstate == 3)", "sel 1"], 1500, 1400), "s $0-pstep", 1500, 1450)

    stat = lp.obj("s $0-lstat", 20, 1750)

    # ---- tap: advance state
    tsel = chain(lp, lp.obj("r eng-loop-tap", 20, 1050), ["v englstate", "sel 0 1 2 3 4"], 20, 1075)
    # EMPTY -> REC (speed back to 1, anchor 0)
    t0 = to(lp, tsel, "t b b b b", 20, 1130)
    msg_to(lp, t0, "; englp clear", 20, 1160, outlet=3)
    setv(lp, t0, "engltop", 1, 130, 1160, outlet=3)
    setv(lp, t0, "engldub", 1, 180, 1160, outlet=3)
    setv(lp, t0, "engllen", 0, 230, 1160, outlet=3)
    setv(lp, t0, "englanc", 0, 280, 1160, outlet=3)
    setv(lp, t0, "englspd", 1, 330, 1160, outlet=3)
    setv(lp, t0, "englstate", 1, 230, 1210, outlet=2)
    send_ = msg_to(lp, t0, "1", 400, 1185, outlet=2)
    to(lp, send_, "s $0-bsnap", 400, 1210)
    to(lp, t0, "s $0-treset", 330, 1210, outlet=1)
    lp.c(t0, 0, stat, 0)
    # REC -> PLAY: length = time so far; held notes get a note-off just before the end
    t1 = to(lp, tsel, "t b b b b", 450, 1130, outlet=1)
    to(lp, t1, "s $0-cur", 580, 1155, outlet=3)
    to(lp, to(lp, t1, "expr max(100, englcur)", 450, 1180, outlet=2), "v engllen", 450, 1205)
    cpm = to(lp, t1, "expr engllen - 1; 1", 550, 1180, outlet=1)
    cpk = lp.obj("pack 0 0", 550, 1205)
    lp.c(cpm, 1, cpk, 1)
    lp.c(cpm, 0, cpk, 0)
    sclose = to(lp, cpk, "s $0-close", 550, 1230)
    t1b = to(lp, t1, "t b b", 450, 1255)
    setv(lp, t1b, "englstate", 2, 520, 1255, outlet=1)
    lp.c(t1b, 1, stat, 0)
    to(lp, t1b, "s $0-cycle", 450, 1305)
    # PLAY -> DUB
    t2 = to(lp, tsel, "t b b", 780, 1130, outlet=2)
    dxt = chain(lp, t2, ["expr min(engltop + 1, 7)", "t f f"], 780, 1160, outlet=1)
    to(lp, dxt, "v engldub", 840, 1210, outlet=1)
    to(lp, dxt, "v engltop", 780, 1210)
    to(lp, to(lp, t2, "expr engldub", 700, 1185), "s $0-bsnap", 700, 1210)
    t2b = to(lp, t2, "t b b", 900, 1160)
    setv(lp, t2b, "englstate", 3, 960, 1185, outlet=1)
    lp.c(t2b, 0, stat, 0)
    # DUB -> PLAY
    t3 = to(lp, tsel, "t b b b", 1050, 1130, outlet=3)
    to(lp, t3, "s $0-cur", 1150, 1155, outlet=2)
    c3 = to(lp, t3, "expr englcur; engldub", 1050, 1180, outlet=1)
    c3p = lp.obj("pack 0 0", 1050, 1205)
    lp.c(c3, 1, c3p, 1)
    lp.c(c3, 0, c3p, 0)
    lp.c(c3p, 0, sclose, 0)
    t3b = to(lp, t3, "t b b", 1150, 1230)
    setv(lp, t3b, "englstate", 2, 1210, 1255, outlet=1)
    lp.c(t3b, 0, stat, 0)
    # STOP -> PLAY (from the start)
    t4 = to(lp, tsel, "t b b b", 1300, 1130, outlet=4)
    setv(lp, t4, "englstate", 2, 1360, 1160, outlet=2)
    lp.c(t4, 1, stat, 0)
    to(lp, t4, "s $0-cycle", 1300, 1200)

    # ---- clear
    ct = chain(lp, lp.obj("r eng-loop-clear", 20, 1300), ["t b b b b b"], 20, 1325)
    to(lp, ct, "s $0-pstop", 120, 1350, outlet=4)
    to(lp, msg_to(lp, ct, f"17 {NCH - 1}", 20, 1350, outlet=3), "s $0-loopoff", 20, 1375)
    msg_to(lp, ct, "; englp clear", 20, 1400, outlet=2)
    from gen_voice import BEND
    msg_to(lp, ct, f"; {BEND} 17" + " 0" * (NCH - 17), 120, 1400, outlet=2)
    setv(lp, ct, "englstate", 0, 20, 1425, outlet=1)
    setv(lp, ct, "engltop", 0, 70, 1425, outlet=1)
    setv(lp, ct, "englspd", 1, 120, 1425, outlet=1)
    lp.c(ct, 0, stat, 0)

    # ---- stop / start
    sss = chain(lp, lp.obj("r eng-loop-stopstart", 400, 1300), ["v englstate", "sel 2 3 4"], 400, 1325)
    s3 = to(lp, sss, "t b b", 460, 1375, outlet=1)
    lp.c(s3, 1, t3, 0)
    sp_ = to(lp, sss, "t b b b", 400, 1410)
    lp.c(s3, 0, sp_, 0)
    to(lp, sp_, "s $0-pstop", 400, 1440, outlet=2)
    to(lp, msg_to(lp, sp_, f"17 {NCH - 1}", 500, 1440, outlet=1), "s $0-loopoff", 500, 1465)
    sp4 = to(lp, sp_, "t b b", 400, 1490)
    setv(lp, sp4, "englstate", 4, 460, 1515, outlet=1)
    lp.c(sp4, 0, stat, 0)
    lp.c(sss, 2, t4, 0)

    # ---- undo last layer
    us = chain(lp, lp.obj("r eng-loop-undo", 700, 1300), ["expr engltop > 1", "sel 1 0"], 700, 1325)
    lp.c(us, 1, ct, 0)
    ut = to(lp, us, "t b b b b b", 700, 1380)
    uo = to(lp, ut, "expr 17 * engltop; 17 * engltop + 16", 850, 1410, outlet=4)
    uop = lp.obj("pack 0 0", 850, 1435)
    lp.c(uo, 1, uop, 1)
    lp.c(uo, 0, uop, 0)
    to(lp, uop, "s $0-loopoff", 850, 1460)
    uut = chain(lp, ut, ["text size englp", "t f f"], 700, 1410, outlet=3)
    uc = lp.obj("f", 700, 1485)
    lp.c(uut, 1, uc, 1)
    lp.c(to(lp, uut, "until", 700, 1460), 0, uc, 0)
    ud = to(lp, uc, "- 1", 740, 1485)
    lp.c(ud, 0, uc, 1)
    ul = to(lp, ud, "t f f", 700, 1510)
    usp = lp.obj("spigot", 700, 1585)
    lp.c(chain(lp, ul, ["text get englp 1 1", "expr $f1 == engltop"], 800, 1535, outlet=1), 0, usp, 1)
    lp.c(ul, 0, usp, 0)
    to(lp, usp, "text delete englp", 700, 1610)
    to(lp, to(lp, ut, "expr engltop - 1", 1000, 1410, outlet=2), "v engltop", 1000, 1435)
    to(lp, to(lp, ut, "expr if(englstate == 3, 2, englstate)", 1000, 1460, outlet=2), "v englstate", 1000, 1485)
    to(lp, ut, "s $0-resync", 1000, 1510, outlet=1)
    lp.c(ut, 0, stat, 0)

    # ---- speed: [s eng-loop-speed] value (-4..-0.25, 0.25..4)
    sp = chain(lp, lp.obj("r eng-loop-speed", 1200, 1300), ["t b f b"], 1200, 1325)
    to(lp, sp, "s $0-anchor", 1300, 1350, outlet=2)        # anchor with the old speed
    to(lp, sp, "v englspd", 1250, 1350, outlet=1)
    spt = to(lp, sp, "t b b", 1200, 1375)
    to(lp, spt, "s $0-resync", 1300, 1400, outlet=1)
    lp.c(spt, 0, stat, 0)

    # ---- Aux (not on the LIBRARY page) and footswitch: tap vs hold
    ra = lp.obj("r aux", 20, 1550)
    ag = to(lp, ra, "spigot 1", 20, 1575)
    lp.c(lp.obj("r $0-notlib", 100, 1550), 0, ag, 1)
    ab = to(lp, ag, "sel 1 0", 20, 1600)
    lp.c(lp.obj("r fs", 150, 1575), 0, ab, 0)
    pressed = lp.obj("f", 250, 1675)
    hold = lp.obj("delay 700", 20, 1650)
    pt = to(lp, ab, "t b b", 20, 1625)
    lp.c(pt, 0, hold, 0)
    lp.c(msg_to(lp, pt, "1", 100, 1650, outlet=1), 0, pressed, 1)
    hh = to(lp, hold, "t b b", 20, 1675)
    lp.c(msg_to(lp, hh, "0", 100, 1700, outlet=1), 0, pressed, 1)
    to(lp, hh, "s eng-loop-clear", 20, 1725)
    rl = to(lp, ab, "t b", 250, 1625, outlet=1)
    lp.c(rl, 0, pressed, 0)
    rt = chain(lp, pressed, ["sel 1", "t b b b"], 250, 1700)
    lp.c(msg_to(lp, rt, "stop", 350, 1750, outlet=2), 0, hold, 0)
    lp.c(msg_to(lp, rt, "0", 400, 1750, outlet=1), 0, pressed, 1)
    to(lp, rt, "s eng-loop-tap", 250, 1775)
    return lp

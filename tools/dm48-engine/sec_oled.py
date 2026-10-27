"""OLED status strip (top 8 pixel rows, above the 5 text lines), redrawn ~12 times a second:
   [7 page tabs]  [loop bar: progress / blinking while recording]  [arp dot]  [breath meter]"""
from pdgen import Canvas
from sec_core import chain, to, msg_to, setv

OSC = "s oscOut"


def oled():
    o = Canvas("oled", w=1400, h=700)
    o.comment("Status strip on the top 8 rows: page tabs, loop progress, arp, breath. Text lines stay below.", 20, 5)
    out = o.obj(OSC, 20, 650)
    lb = chain(o, o.obj("loadbang", 20, 30), ["delay 500"], 20, 55)
    o.c(msg_to(o, lb, "/oled/gShowInfoBar 3 0", 20, 105), 0, out, 0)
    met = to(o, lb, "metro 80", 200, 105)
    fr = to(o, met, "t b b b b b b", 200, 130)
    # 5: clear the strip
    o.c(msg_to(o, fr, "/oled/gFillArea 3 0 0 128 8 0", 600, 160, outlet=5), 0, out, 0)
    # 4: page tabs (outline each, fill the current one)
    tabs = to(o, fr, "t b b", 450, 160, outlet=4)
    for i in range(8):
        o.c(msg_to(o, tabs, f"/oled/gBox 3 {i * 5} 1 4 5 1", 450 + i * 20, 185 + (i % 2) * 20, outlet=1), 0, out, 0)
    o.c(msg_to(o, to(o, tabs, "expr engpage * 5", 450, 230), "/oled/gFillArea 3 $1 1 4 5 1", 450, 255), 0, out, 0)
    # 3: loop bar 46..93
    lpb = to(o, fr, "t b b b", 200, 300, outlet=3)
    to(o, lpb, "s $0-cur", 300, 325, outlet=2)
    st = chain(o, lpb, ["v englstate", "sel 0 1 2 3 4"], 200, 350, outlet=1)
    box = o.msg("/oled/gBox 3 46 1 48 6 1", 400, 400)
    o.c(box, 0, out, 0)
    for i in (1, 2, 3, 4):
        o.c(st, i, box, 0)
    # REC: blink a full bar
    bl = o.obj("f", 200, 425)
    o.c(st, 1, bl, 0)
    o.c(to(o, bl, "== 0", 240, 425), 0, bl, 1)
    rs = to(o, bl, "sel 1", 200, 450)
    o.c(msg_to(o, rs, "/oled/gFillArea 3 46 1 48 6 1", 200, 475), 0, out, 0)
    # PLAY / DUB: fill to the position (DUB also shows a marker every 1/4)
    pp = o.obj("t b", 300, 425)
    o.c(st, 2, pp, 0)
    o.c(st, 3, pp, 0)
    pw = chain(o, pp, ["expr int(48 * englcur / max(1, engllen))", "max 1"], 300, 450)
    o.c(msg_to(o, pw, "/oled/gFillArea 3 46 1 $1 6 1", 300, 500), 0, out, 0)
    dm = o.obj("t b", 450, 425)
    o.c(st, 3, dm, 0)
    for q in (1, 2, 3):
        o.c(msg_to(o, dm, f"/oled/gInvertArea 3 {46 + q * 12} 2 1 4", 450 + q * 40, 450), 0, out, 0)
    # 3b: audio loop: a 1-pixel line under the loop bar (playhead while playing, full while recording)
    al = chain(o, lpb, ["expr engastate", "sel 2 3 4 1"], 450, 560, outlet=0)
    o.c(msg_to(o, al, "/oled/gFillArea 3 46 7 48 1 1", 450, 600), 0, out, 0)
    o.c(msg_to(o, al, "/oled/gFillArea 3 46 7 2 1 1", 650, 600, outlet=3), 0, out, 0)
    alp = o.obj("t b", 550, 585)
    o.c(al, 1, alp, 0)
    o.c(al, 2, alp, 0)
    o.c(alp, 0, o.obj("s $0-asnap", 600, 610), 0)
    o.c(msg_to(o, chain(o, alp, ["expr max(1, int(48 * engaph))"], 550, 610), "/oled/gFillArea 3 46 7 $1 1 1", 550, 640),
        0, out, 0)
    # 2: arp dot at 97
    ar = chain(o, fr, ["v engarpon", "sel 1"], 700, 300, outlet=2)
    o.c(msg_to(o, ar, "/oled/gFillArea 3 97 2 3 4 1", 700, 350), 0, out, 0)
    # 1: breath meter 102..127
    bw = chain(o, fr, ["v engarpbr", "expr int(25 * $f1 / 127)", "max 1"], 900, 300, outlet=1)
    bb = to(o, fr, "t b", 1000, 300, outlet=1)
    o.c(msg_to(o, bb, "/oled/gBox 3 102 1 26 6 1", 1000, 325), 0, out, 0)
    o.c(msg_to(o, bw, "/oled/gFillArea 3 102 2 $1 4 1", 900, 375), 0, out, 0)
    # 0: show it
    o.c(msg_to(o, fr, "/oled/gFlip 3", 200, 600), 0, out, 0)
    return o


def rows():
    """PLAY-style knob rows: [s $0-gdraw] 'N bar text...' (bar 0..1, or -1 for a plain text row).
    Row N sits where the OS draws text line N (y = 9 + (N-1)*11), so line 5 and the top strip still fit."""
    r = Canvas("screen-rows", w=1200, h=700)
    r.comment("Row N: [N] [bar 37px] text   (PLAY style)  -- or full-width text when bar = -1", 20, 5)
    out = r.obj(OSC, 20, 650)
    rg0 = r.obj("r $0-gdraw", 20, 30)
    rg = r.obj("spigot 1", 20, 42)                 # closed while the scope / loop view is shown
    r.c(rg0, 0, rg, 0)
    r.c(r.obj("r $0-rowson", 120, 30), 0, rg, 1)
    t = to(r, rg, "t a a", 20, 55)
    import os
    if os.environ.get("DBG"):
        to(r, rg, "print GDRAW", 200, 30)
    txt = r.obj("list", 400, 130)
    r.c(to(r, t, "list split 2", 400, 80, outlet=1), 1, txt, 1)
    nv = chain(r, t, ["list split 2", "unpack 0 0"], 20, 80)
    to(r, nv, "v enggv", 120, 130, outlet=1)
    nt = to(r, nv, "t b f", 20, 130)
    to(r, nt, "v enggn", 120, 155, outlet=1)
    dr = to(r, nt, "t b b b b", 20, 155)
    # 3: clear the row
    r.c(msg_to(r, to(r, dr, "expr 9 + (enggn - 1) * 11", 600, 180, outlet=3),
               "/oled/gFillArea 3 0 $1 128 11 0", 600, 205), 0, out, 0)
    # 2: number + bar (only when bar >= 0)
    bg = chain(r, dr, ["expr enggv >= 0", "sel 1"], 300, 180, outlet=2)
    bt = to(r, bg, "t b b b", 300, 230)
    nm = to(r, bt, "expr 10 + (enggn - 1) * 11; enggn", 450, 255, outlet=2)
    npk = r.obj("pack 0 0", 450, 280)
    r.c(nm, 1, npk, 1)
    r.c(nm, 0, npk, 0)
    r.c(msg_to(r, npk, "/oled/gPrintln 3 0 $1 8 1 $2", 450, 305), 0, out, 0)
    r.c(msg_to(r, to(r, bt, "expr 10 + (enggn - 1) * 11", 300, 330, outlet=1), "/oled/gBox 3 11 $1 37 8 1", 300, 355), 0, out, 0)
    fw = to(r, bt, "expr int(min(1, max(0, enggv)) * 35); 11 + (enggn - 1) * 11", 150, 380)
    fpk = r.obj("pack 0 0", 150, 405)
    r.c(fw, 1, fpk, 1)
    r.c(fw, 0, fpk, 0)
    r.c(msg_to(r, fpk, "/oled/gFillArea 3 12 $2 $1 6 1", 150, 430), 0, out, 0)
    # 1: text (x 52 next to a bar, x 2 for a plain row)
    pre = to(r, dr, "expr if(enggv >= 0, 52, 2); 10 + (enggn - 1) * 11", 20, 480, outlet=1)
    ppk = r.obj("pack 0 0", 20, 505)
    r.c(pre, 1, ppk, 1)
    r.c(pre, 0, ppk, 0)
    lp = r.obj("list prepend", 20, 555)
    r.c(msg_to(r, ppk, "/oled/gPrintln 3 $1 $2 8 1", 20, 530), 0, lp, 1)
    r.c(dr, 0, txt, 0)
    r.c(txt, 0, lp, 0)
    r.c(to(r, lp, "list trim", 20, 580), 0, out, 0)
    return r


def scope():
    """High G# cycles the screen: pages > SCOPE (live output) > LOOP (audio loop waveform + playhead) > pages.
    Draws rows y 9..52 (the page rows); the top strip and line 5 stay."""
    c = Canvas("scope-view", w=1600, h=1100)
    c.comment("Screen views: 0 pages, 1 scope, 2 audio loop waveform. Waveforms go out as one gWaveform message.", 20, 5)
    out = c.obj(OSC, 20, 1050)
    # next view (the loop view only when there is an audio loop; not on the LIBRARY page)
    nv = chain(c, c.obj("r eng-view-next", 20, 30),
               ["expr if(engpage == 6, 0, if(engview == 0, 1, if((engview == 1) && (engastate >= 2), 2, 0)))"], 20, 55)
    vt = to(c, nv, "t f f f", 20, 80)
    to(c, vt, "v engview", 150, 105, outlet=2)
    to(c, to(c, vt, "== 0", 100, 105, outlet=1), "s $0-rowson", 100, 130)
    vs = to(c, vt, "sel 0 1 2", 20, 130)
    # back to the pages: redraw the page
    back = to(c, vs, "t b b", 20, 155)
    c.c(msg_to(c, back, "/oled/gFillArea 3 0 9 128 44 0", 120, 180, outlet=1), 0, out, 0)
    to(c, to(c, to(c, back, "delay 1", 20, 180), "expr engpage", 20, 205), "s eng-page", 20, 230)
    for i, nm in ((1, "SCOPE"), (2, "LOOP WAVE")):
        to(c, msg_to(c, vs, f"list {nm}  (G# next)", 150 + i * 150, 155, outlet=i), "s $0-toast",
           150 + i * 150, 180)
    # a page key leaves the view
    pk = chain(c, c.obj("r eng-page", 500, 30), ["expr engview > 0", "sel 1"], 500, 55)
    pkt = to(c, pk, "t b b", 500, 105)
    to(c, msg_to(c, pkt, "0", 600, 130, outlet=1), "v engview", 600, 155)
    to(c, msg_to(c, pkt, "1", 500, 130), "s $0-rowson", 500, 155)
    to(c, to(c, to(c, pkt, "delay 1", 650, 130), "expr engpage", 650, 155), "s eng-page", 650, 180)
    # frame clock
    met = c.obj("metro 70", 20, 300)
    c.c(chain(c, c.obj("r $0-rowson", 120, 250), ["== 0"], 120, 275), 0, met, 0)
    fr = chain(c, met, ["expr engview", "sel 1 2"], 20, 325)
    # ---- SCOPE: record 1024 samples, then (next frame) find a rising zero crossing and draw 128 points
    rec = c.obj("tabwrite~ engscope", 400, 400)
    c.c(c.obj("r~ eng-scope", 400, 375), 0, rec, 0)
    sc = c.obj("t b b", 20, 375)
    c.c(fr, 0, sc, 0)
    c.c(sc, 0, rec, 0)                                  # (2) arm the next capture
    zs = to(c, sc, "t b b b b", 120, 400, outlet=1)     # (1) draw the last capture
    setv(c, zs, "engsczero", 0, 300, 425, outlet=3)
    zu = to(c, msg_to(c, zs, "500", 120, 425, outlet=2), "until", 120, 450)
    zi = c.obj("f 1", 120, 475)
    c.c(msg_to(c, zs, "1", 200, 450, outlet=3), 0, zi, 1)
    c.c(zu, 0, zi, 0)
    c.c(to(c, zi, "+ 1", 170, 500), 0, zi, 1)
    zx = chain(c, zi, ["expr if((engsczero == 0) && (engscope[$f1 - 1] < 0) && (engscope[$f1] >= 0), $f1, -1)",
                       "moses 1"], 120, 500)
    to(c, zx, "v engsczero", 170, 550, outlet=1)
    # peak of the window for auto-scaling
    to(c, to(c, zs, "array max engscope", 400, 475, outlet=1), "v engscpk", 400, 500)
    dt = to(c, zs, "t b b b", 20, 625)
    di = c.obj("f", 20, 700)
    c.c(msg_to(c, dt, "0", 100, 650, outlet=2), 0, di, 1)
    c.c(to(c, msg_to(c, dt, "128", 20, 650, outlet=1), "until", 20, 675), 0, di, 0)
    c.c(to(c, di, "+ 1", 70, 725), 0, di, 1)
    yx = to(c, di, "expr $f1; int(min(52, max(10, 31 - 20 * engscope[engsczero + $f1 * 3] / max(0.05, engscpk))))",
            20, 725)
    yv = c.obj("f", 150, 775)
    c.c(yx, 1, yv, 1)
    yt = to(c, yx, "t b f", 20, 750)
    yw = c.obj("tabwrite engscy", 20, 800)
    c.c(yt, 1, yw, 1)
    c.c(yt, 0, yv, 0)
    c.c(yv, 0, yw, 0)
    sd = to(c, dt, "t b b", 300, 650)
    c.c(msg_to(c, sd, "/oled/gFillArea 3 0 9 128 44 0", 400, 675, outlet=1), 0, out, 0)
    send_wave(c, sd, out, 300, 700)
    # ---- LOOP: the layers' overviews (summed, scaled by each layer's gain), mirrored, with the playhead
    lp = c.obj("t b b b b b", 900, 375)
    c.c(fr, 1, lp, 0)
    c.c(lp, 4, c.obj("s $0-asnap", 1000, 400), 0)
    c.c(msg_to(c, lp, "/oled/gFillArea 3 0 9 128 44 0", 1100, 400, outlet=3), 0, out, 0)
    for half, sign, x in ((0, -1, 900), (1, 1, 1150)):
        tt = to(c, lp, "t b b b", x, 450 + half * 300, outlet=2 - half)
        li = c.obj("f", x, 525 + half * 300)
        c.c(msg_to(c, tt, "0", x + 80, 475 + half * 300, outlet=2), 0, li, 1)
        c.c(to(c, msg_to(c, tt, "128", x, 475 + half * 300, outlet=1), "until", x, 500 + half * 300), 0, li, 0)
        c.c(to(c, li, "+ 1", x + 50, 550 + half * 300), 0, li, 1)
        amp = " + ".join(f"engag[{j}] * engov{j}[$f1]" for j in range(6))
        lx = to(c, li, f"expr $f1; int({30 if sign < 0 else 32} {'-' if sign < 0 else '+'} min(1, {amp}) * 20)",
                x, 550 + half * 300)
        lv = c.obj("f", x + 130, 600 + half * 300)
        c.c(lx, 1, lv, 1)
        lt = to(c, lx, "t b f", x, 575 + half * 300)
        lw = c.obj("tabwrite engscy", x, 625 + half * 300)
        c.c(lt, 1, lw, 1)
        c.c(lt, 0, lv, 0)
        c.c(lv, 0, lw, 0)
        send_wave(c, tt, out, x + 150, 650 + half * 300)
    # playhead
    c.c(msg_to(c, to(c, lp, "expr int(engaph * 127)", 1400, 400, outlet=0), "/oled/gInvertArea 3 $1 9 1 44", 1400, 425),
        0, out, 0)
    return c


def send_wave(c, src, out, x, y):
    """engscy (128 y values) -> one /oled/gWaveform message (as the Organelle's own patches do)"""
    g = to(c, to(c, src, "array get engscy", x, y), "list prepend sendtyped /oled/gWaveform ib 3", x, y + 25)
    c.c(to(c, g, "list trim", x, y + 50), 0, out, 0)

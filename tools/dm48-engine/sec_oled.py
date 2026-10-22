"""OLED status strip (top 8 pixel rows, above the 5 text lines), redrawn ~12 times a second:
   [7 page tabs]  [loop bar: progress / blinking while recording]  [arp dot]  [breath meter]"""
from pdgen import Canvas
from sec_core import chain, to, msg_to

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
    for i in range(7):
        o.c(msg_to(o, tabs, f"/oled/gBox 3 {i * 6} 1 5 5 1", 450 + i * 20, 185 + (i % 2) * 20, outlet=1), 0, out, 0)
    o.c(msg_to(o, to(o, tabs, "expr engpage * 6", 450, 230), "/oled/gFillArea 3 $1 1 5 5 1", 450, 255), 0, out, 0)
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
    rg = r.obj("r $0-gdraw", 20, 30)
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

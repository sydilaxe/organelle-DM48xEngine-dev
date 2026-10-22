
# ---- screen: page gating + rate-limited monitor line
NPAGES = 3
sc = Canvas("screen", w=1100, h=600)
for page in range(NPAGES):
    x = 20 + page * 200
    r = sc.obj(f"r $0-disp{page}", x, 20)
    sp = sc.obj("spigot", x, 50)
    sc.c(r, 0, sp, 0)
    g = sc.obj(f"r $0-g{page}", x + 70, 20)
    sc.c(g, 0, sp, 1)
    rt = sc.obj("route 1 2 3 4", x, 80)
    sc.c(sp, 0, rt, 0)
    for ln in range(4):
        sc.c(rt, ln, sc.obj(f"s screenLine{ln + 1}", x, 110 + ln * 26), 0)
rmon = sc.obj("r mpe-mon", 650, 20)
la = sc.obj("list append", 650, 180)
sc.c(rmon, 0, la, 1)
dirty1 = sc.msg("1", 750, 50)
sc.c(rmon, 0, dirty1, 0)
dirtyf = sc.obj("f", 650, 100)
sc.c(dirty1, 0, dirtyf, 1)
met = sc.obj("metro 100", 650, 70)
sc.c(sc.obj("loadbang", 650, 45), 0, met, 0)
sc.c(met, 0, dirtyf, 0)
dsel = sc.obj("sel 1", 650, 125)
sc.c(dirtyf, 0, dsel, 0)
dt = sc.obj("t b b", 650, 150)
sc.c(dsel, 0, dt, 0)
d0 = sc.msg("0", 780, 150)
sc.c(dt, 1, d0, 0)
sc.c(d0, 0, dirtyf, 1)
sc.c(dt, 0, la, 0)
sc.c(la, 0, sc.obj("s screenLine5", 650, 210), 0)
m.sub(sc, 20, 200)

# ---- params: knobs, pages, settings
pr = Canvas("params", w=1500, h=1100)
raux = pr.obj("r aux", 20, 20)
asel = pr.obj("sel 1", 20, 45)
pr.c(raux, 0, asel, 0)
pf = pr.obj("f", 20, 70)
pp = pr.obj("+ 1", 60, 70)
pmod = pr.obj(f"mod {NPAGES}", 60, 95)
pr.c(asel, 0, pf, 0)
pr.c(pf, 0, pp, 0)
pr.c(pp, 0, pmod, 0)
pr.c(pmod, 0, pf, 1)
pset = pr.obj("t f f f", 20, 130)
pr.c(pmod, 0, pset, 0)
# gates first (right outlet), then LED, then refresh + title
for page in range(NPAGES):
    e = pr.obj(f"== {page}", 20 + page * 60, 160)
    pr.c(pset, 2, e, 0)
    pr.c(e, 0, pr.obj(f"s $0-g{page}", 20 + page * 60, 185), 0)
ledsel = pr.obj("sel 0 1 2", 220, 160)
pr.c(pset, 1, ledsel, 0)
sled = pr.obj("s led", 220, 215)
for page, col in enumerate((0, 3, 5)):
    lm = pr.msg(str(col), 220 + page * 35, 188)
    pr.c(ledsel, page, lm, 0)
    pr.c(lm, 0, sled, 0)
refsel = pr.obj("sel 0 1 2", 360, 160)
pr.c(pset, 0, refsel, 0)
smon = pr.obj("s mpe-mon", 360, 270)
titles = ("PLAY   (aux: shape)", "SHAPE  (aux: setup)", "SETUP  (aux: play)")
for page in range(NPAGES):
    tb_ = pr.obj("t b b", 360 + page * 150, 190)
    pr.c(refsel, page, tb_, 0)
    tm = pr.msg(titles[page], 360 + page * 150, 240)
    pr.c(tb_, 0, tm, 0)
    pr.c(tm, 0, smon, 0)
    pr.c(tb_, 1, pr.obj(f"s $0-refresh{page}", 400 + page * 150, 215), 0)

# knob routing: knobN on page P -> "$0-k<N>p<P>"
for k in range(1, 5):
    x = 820 + (k - 1) * 170
    rk = pr.obj(f"r knob{k}", x, 20)
    for page in range(NPAGES):
        sp = pr.obj("spigot 1" if page == 0 else "spigot", x + page * 50, 70)
        pr.c(rk, 0, sp, 0)
        pr.c(pr.obj(f"r $0-g{page}", x + page * 50, 45), 0, sp, 1)
        pr.c(sp, 0, pr.obj(f"s $0-k{k}p{page}", x + page * 50, 95 + page * 22), 0)

Y = 330
# PLAY page: knob position 0..1 is the stored value
handler(pr, 20, Y, "$0-k1p0", 0.55, ["* 95", "+ 30", "pack 0 30", "s mpe-cut-c"],
        (["* 100", "i"], "1 Cutoff $1"), 0)
handler(pr, 220, Y, "$0-k2p0", 0.35, ["expr $f1 * $f1 * 11 + 0.7", "s mpe-res"],
        (["* 100", "i"], "2 Resonance $1"), 0)
handler(pr, 420, Y, "$0-k3p0", 0.4, ["expr $f1 * $f1 * 0.025", "pack 0 30", "s mpe-detune-c"],
        (["* 100", "i"], "3 Detune $1"), 0)
handler(pr, 620, Y, "$0-k4p0", 0.3, ["s mpe-space"],
        (["* 100", "i"], "4 Space $1 %"), 0)

Y1 = 560
# SHAPE page
handler(pr, 20, Y1, "$0-bamt", 0.6, ["* 72", "pack 0 30", "s mpe-bamt-c"],
        (["* 100", "i"], "1 Breath>Filter $1"), 1)
handler(pr, 220, Y1, "$0-sub", 0.3, ["pack 0 30", "s mpe-sub-c"],
        (["* 100", "i"], "2 Sub Osc $1"), 1)
handler(pr, 420, Y1, "$0-release", 0.25, ["expr $f1 * $f1 * 2990 + 10", "s mpe-release"],
        (["expr int($f1 * $f1 * 2990 + 10)"], "3 Release $1 ms"), 1)
handler(pr, 620, Y1, "$0-curve", 1, ["s mpe-curve"], ([], "4 Breath Curve $1"), 1)
for kk, name in ((1, "bamt"), (2, "sub"), (3, "release")):
    pr.c(pr.obj(f"r $0-k{kk}p1", 20 + (kk - 1) * 200, Y1 - 50), 0,
         pr.obj(f"s $0-{name}", 20 + (kk - 1) * 200, Y1 - 25), 0)
k4m = [pr.obj("r $0-k4p1", 620, Y1 - 75), pr.obj("* 25", 620, Y1 - 50), pr.obj("+ 5.5", 670, Y1 - 50),
       pr.obj("i", 720, Y1 - 50), pr.obj("/ 10", 750, Y1 - 50), pr.obj("s $0-curve", 620, Y1 - 25)]
pr.chain(*k4m)

Y2 = 820
# SETUP page
k1m = [pr.obj("r $0-k1p2", 20, Y2 - 75), pr.obj("* 4", 20, Y2 - 50), pr.obj("+ 0.5", 70, Y2 - 50),
       pr.obj("i", 120, Y2 - 50), pr.obj("- 2", 150, Y2 - 50), pr.obj("s $0-octave", 20, Y2 - 25)]
pr.chain(*k1m)
handler(pr, 20, Y2, "$0-octave", 0, ["* 12", "s mpe-octave"], ([], "1 Octave $1"), 2)
for kk, name, dflt, line in ((2, "noterange", 48, "2 Note Bend $1 st"), (3, "globrange", 2, "3 Ch1 Bend $1 st")):
    x = 220 if kk == 2 else 420
    a = pr.obj(f"r $0-k{kk}p2", x, Y2 - 100)
    b = pr.obj("* 5.99", x, Y2 - 75)
    c_ = pr.obj("i", x + 60, Y2 - 75)
    g = pr.msg("get $1 1", x + 90, Y2 - 75)
    ls = pr.obj("list store 1 2 3 12 24 48", x, Y2 - 50)
    s_ = pr.obj(f"s $0-{name}", x, Y2 - 25)
    pr.chain(a, b, c_, g, ls, s_)
    handler(pr, x, Y2, f"$0-{name}", dflt, [f"s mpe-{name}"], ([], line), 2)
k4s = [pr.obj("r $0-k4p2", 620, Y2 - 75), pr.obj("* 70", 620, Y2 - 50), pr.obj("+ 20.5", 670, Y2 - 50),
       pr.obj("i", 730, Y2 - 50), pr.obj("/ 10", 760, Y2 - 50), pr.obj("s $0-vibrate", 620, Y2 - 25)]
pr.chain(*k4s)
handler(pr, 620, Y2, "$0-vibrate", 5.5, ["s mpe-vibrate"], ([], "4 Vibrato Rate $1 Hz"), 2)

# settings save / load
SAVED = ("bamt", "sub", "release", "curve", "octave", "noterange", "globrange", "vibrate")
sx, sy = 900, 330
rss = pr.obj("r saveState", sx, sy)
svt = pr.obj("t " + " ".join(["b"] * len(SAVED)), sx, sy + 30)
pr.c(rss, 0, svt, 0)
spk = pr.obj("pack " + " ".join(["0"] * len(SAVED)), sx, sy + 120)
for i, nm_ in enumerate(SAVED):
    vv = pr.obj(f"v $0-sv-{nm_}", sx + i * 70, sy + 70)
    pr.c(svt, i, vv, 0)  # outlet 0 fires last -> pack's hot inlet last
    pr.c(vv, 0, spk, i)
    pr.c(pr.obj(f"r $0-{nm_}", sx + i * 70, sy + 250), 0,
         pr.obj(f"v $0-sv-{nm_}", sx + i * 70, sy + 275), 0)
dollars = " ".join(f"${i + 1}" for i in range(len(SAVED)))
spm = pr.msg(f"clear, add {dollars}, write /tmp/state/settings.txt", sx, sy + 150)
pr.c(spk, 0, spm, 0)
tf = pr.obj("textfile", sx, sy + 180)
pr.c(spm, 0, tf, 0)
lb = pr.obj("loadbang", sx + 500, sy)
lbt = pr.obj("t b b b", sx + 500, sy + 30)
pr.c(lb, 0, lbt, 0)
rd = pr.msg("read settings.txt, rewind, bang", sx + 500, sy + 60)
pr.c(lbt, 1, rd, 0)
pr.c(rd, 0, tf, 0)
lu = pr.obj("unpack " + " ".join(["0"] * len(SAVED)), sx, sy + 330)
pr.c(tf, 0, lu, 0)
for i, nm_ in enumerate(SAVED):
    pr.c(lu, i, pr.obj(f"s $0-{nm_}", sx + i * 70, sy + 360), 0)
# defaults: page 0, PLAY knobs, apply stored SHAPE/SETUP defaults, vibrato depth 0
defs = pr.msg("0", sx + 500, sy + 100)
pr.c(lbt, 2, defs, 0)
pr.c(defs, 0, pf, 1)
initb = pr.obj("t b b b b b b b", sx + 500, sy + 130)
pr.c(lbt, 2, initb, 0)
pr.c(initb, 0, pr.obj("s $0-refresh2", sx + 500, sy + 220), 0)
pr.c(initb, 1, pr.obj("s $0-refresh1", sx + 620, sy + 220), 0)
for i, (nm_, val) in enumerate((("$0-k1p0", 0.55), ("$0-k2p0", 0.35), ("$0-k3p0", 0.4), ("$0-k4p0", 0.3),
                                 ("mpe-vibdepth", 0))):
    msg_ = pr.msg(str(val), sx + 500 + i * 60, sy + 160)
    pr.c(initb, 6 - i, msg_, 0)
    pr.c(msg_, 0, pr.obj(f"s {nm_}", sx + 500 + i * 60, sy + 185), 0)
showp = pr.msg("0", sx + 800, sy + 60)
pr.c(lbt, 0, showp, 0)
pr.c(showp, 0, pset, 0)
m.sub(pr, 20, 230)

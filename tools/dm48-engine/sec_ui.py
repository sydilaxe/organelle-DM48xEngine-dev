"""Pages, knobs, screen and saved settings."""
from pdgen import Canvas
from gen_voice import JUST
from sec_core import chain, to, msg_to, setv, NOTE_NAMES

PAGES = ["PLAY", "SHAPE", "FX", "SETUP", "TUNE", "ENGINE", "LIBRARY"]
P = {n: i for i, n in enumerate(PAGES)}
LIB = P["LIBRARY"]


def handler(c, x, y, entry, default, apply_objs, disp_objs, disp_msg, page, bar="$f1"):
    """[r entry] -> [f] (page refresh re-outputs it) -> apply chain + a PLAY-style screen row:
    'N bar text...' to [s $0-row<page>] (bar 0..1 from the expr 'bar', or -1 = text only)."""
    st = c.obj(f"f {default}", x, y + 25)
    c.c(c.obj(f"r {entry}", x, y), 0, st, 0)
    c.c(c.obj(f"r $0-refresh{page}", x + 80, y), 0, st, 0)
    tt = to(c, st, "t f f", x, y + 50)
    if apply_objs:
        chain(c, tt, apply_objs, x + 100, y + 75, outlet=1)
    n, text = disp_msg.split(" ", 1)
    t2 = to(c, tt, "t f f", x, y + 75)
    lp = c.obj("list prepend", x, y + 175)
    bv = to(c, t2, f"expr {bar}" if bar else "expr -1", x + 60, y + 100, outlet=1)
    c.c(msg_to(c, bv, f"{n} $1", x + 60, y + 125), 0, lp, 1)
    last = chain(c, t2, disp_objs, x, y + 100) if disp_objs else t2
    dm = c.msg(text, x, y + 100 + 25 * len(disp_objs))
    c.c(last, 0, dm, 0)
    c.c(dm, 0, lp, 0)
    to(c, to(c, lp, "list trim", x, y + 200), f"s $0-row{page}", x, y + 225)
    return st


# (page, knob) -> where its current value (0..1) lives. These knobs move relative to the value (no jumps).
REL_CUR = {(0, 1): "engpv1", (0, 2): "engpv2", (0, 3): "engpv3", (0, 4): "engpv4",
           (1, 1): "engcurbamt", (1, 2): "engcurbody", (1, 3): "engcurrelease",
           (2, 1): "engcurdtime", (2, 2): "engcurdfb", (2, 3): "engcurdmix", (2, 4): "engcurrmix",
           (5, 3): "engcurlevel"}


def knob_map(c, page, k, objs, dest, x, y):
    """[r $0-k<k>p<page>] -> objs -> [s dest]"""
    last = chain(c, c.obj(f"r $0-k{k}p{page}", x, y), objs, x, y + 25)
    to(c, last, f"s {dest}", x, y + 25 + 25 * len(objs))


import json, os
_AS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "astral_scales.json")))
JI = {
    0: [0] * 12,
    1: [0, 0.1173, 0.0391, 0.1564, -0.1369, -0.0196, -0.0978, 0.0196, 0.1369, -0.1564, 0.1760, -0.1173],
    2: [0, 0.1173, 0.0391, -0.3313, -0.1369, -0.2918, -0.0978, 0.0196, 0.1369, -0.1564, -0.3117, -0.1173],
}
# scale library: Equal, Just, Just 7, then Astral's 75 scales (cents, relative to the Key)
_ALL = {"Equal 12-TET": JI[0], "Just 5-limit": JI[1], "Just 7": JI[2]}
for _i, _n in enumerate(_AS["names"][1:], 1):
    _ALL[_n] = [c / 100 for c in _AS["cents"][_i * 12:_i * 12 + 12]]
_PRE = lambda *p: [n for n in _AS["names"][1:] if n.startswith(p)]
FAMILIES = [
    ("Western", ["Equal 12-TET", "Just 5-limit", "Just 7", "JI Major 5-limit", "JI Minor 5-limit", "JI Major 7-limit",
                 "Harm Ser 8-16", "Pyth Major"]),
    ("Temperament", _PRE("1/4comma", "Werck")),
    ("Gamelan", _PRE("Slen", "Pelog", "Bali")),
    ("African", _PRE("Timbila", "Banyoro", "Volans", "Mandinka", "Ethiop")),
    ("Japanese", _PRE("Hirajoshi", "Shakuh")),
    ("Chinese", _PRE("Chin") + ["Palace Mode"]),
    ("SE-Asian", _PRE("Dan Tranh", "Burm", "Thai", "Saung")),
    ("Maqam", _PRE("Zalzal", "al-Urmawi", "Huzzam", "Segah", "Turk", "Rast", "Bayati", "Hijaz", "1/4tone")),
    ("Indian", _PRE("Ind Mode", "Raga", "Bhairav", "Todi", "Darbari", "N Ind")),
    ("Byzantine", ["Chrys Diat", "Athan Chrom."]),
]
SCALE_NAMES = [n for _, ns in FAMILIES for n in ns]
assert sorted(SCALE_NAMES) == sorted(_ALL), set(_ALL) ^ set(SCALE_NAMES)
SCALE_TABLE = [v for n in SCALE_NAMES for v in _ALL[n]]
NSCALES = len(SCALE_NAMES)
FAM_START, FAM_COUNT, FAM_OF = [], [], []
for _fi, (_f, _ns) in enumerate(FAMILIES):
    FAM_START.append(len(FAM_OF)); FAM_COUNT.append(len(_ns)); FAM_OF += [_fi] * len(_ns)
SAVED = ["bamt", "body", "release", "curve", "dtime", "dfb", "dmix", "rmix",
         "octave", "noterange", "globrange", "vibrate", "tuning", "key", "mode", "level", "mout", "beat"]
DEFAULTS = [0.6, 0.3, 0.3, 1, 0.45, 0.4, 0.2, 0.35, 0, 48, 2, 5.5, 1, 0, 0, 0.6, 2, 500]


def ui():
    u = Canvas("pages", w=1800, h=1500)
    # ---- page select
    pt = chain(u, u.obj("r eng-page", 20, 20), ["t f f f f f"], 20, 45)
    to(u, pt, "v engpage", 200, 70, outlet=4)
    for i in range(len(PAGES)):
        to(u, to(u, pt, f"== {i}", 20 + i * 60, 100, outlet=3), f"s $0-g{i}", 20 + i * 60, 125)
    to(u, to(u, pt, f"!= {LIB}", 450, 100, outlet=3), "s $0-notlib", 450, 125)
    pn = chain(u, msg_to(u, pt, "get $1 1", 550, 100, outlet=2), [f"list store {' '.join(p + ':' for p in PAGES)}"], 550, 125)
    to(u, pn, "s $0-pagename", 550, 175)
    rs = to(u, pt, "sel " + " ".join(str(i) for i in range(len(PAGES))), 20, 175, outlet=1)
    for i in range(len(PAGES)):
        to(u, rs, f"s $0-refresh{i}", 20 + i * 90, 205 + (i % 2) * 25, outlet=i)
    to(u, pt, "s $0-l5", 20, 260)
    # ---- screen rows 1-4 per page (PLAY style: number, bar, text) ; LIBRARY uses plain text lines
    for i in range(len(PAGES)):
        x = 20 + i * 180
        if i == LIB:
            sp = u.obj("spigot", x, 320)
            u.c(u.obj(f"r $0-disp{i}", x, 295), 0, sp, 0)
            u.c(u.obj(f"r $0-g{i}", x + 70, 295), 0, sp, 1)
            rt = to(u, sp, "route 1 2 3 4 5", x, 345)
            for k in range(5):
                to(u, rt, f"s screenLine{k + 1}", x, 370 + k * 22, outlet=k)
            continue
        # plain "N text" -> "N -1 text"
        dt = to(u, u.obj(f"r $0-disp{i}", x, 295), "t a a", x, 320)
        rest = u.obj("list", x + 60, 395)
        u.c(to(u, dt, "list split 1", x + 60, 345, outlet=1), 1, rest, 1)
        nn = chain(u, dt, ["list split 1", "t b f"], x, 345)
        lp = u.obj("list prepend", x, 420)
        u.c(msg_to(u, nn, "$1 -1", x + 40, 395, outlet=1), 0, lp, 1)
        u.c(nn, 0, rest, 0)
        u.c(rest, 0, lp, 0)
        rr = u.obj(f"s $0-row{i}", x, 470)
        import os
        if os.environ.get("DBG"):
            to(u, u.obj(f"r $0-row{i}", x + 100, 470), f"print ROW{i}", x + 100, 495)
            to(u, u.obj(f"r $0-disp{i}", x + 200, 470), f"print DISP{i}", x + 200, 495)
        u.c(to(u, lp, "list trim", x, 445), 0, rr, 0)
        sp = u.obj("spigot", x, 520)
        u.c(u.obj(f"r $0-row{i}", x, 495), 0, sp, 0)
        u.c(u.obj(f"r $0-g{i}", x + 70, 495), 0, sp, 1)
        to(u, sp, "s $0-gdraw", x, 545)
    # ---- line 5: page name + loop state (not on LIBRARY)
    l5 = u.obj("list append", 1300, 100)
    ls = u.obj("list", 1400, 75)
    lst = to(u, u.obj("r eng-loopstat", 1400, 20), "t b a", 1400, 45)
    u.c(lst, 1, ls, 1)                       # store first, then redraw
    to(u, lst, "s $0-l5", 1500, 70)
    pnl = u.obj("list", 1300, 75)
    u.c(u.obj("r $0-pagename", 1300, 20), 0, pnl, 1)
    l5t = chain(u, u.obj("r $0-l5", 1300, 0), ["t b b"], 1250, 45)
    u.items[l5t - 1] = ("obj", (1200, 20, "r $0-l5"))
    u.c(l5t, 1, ls, 0)
    u.c(ls, 0, l5, 1)
    u.c(l5t, 0, pnl, 0)
    u.c(pnl, 0, l5, 0)
    l5s = to(u, l5, "spigot 1", 1300, 125)
    u.c(u.obj("r $0-notlib", 1380, 100), 0, l5s, 1)
    to(u, l5s, "s screenLine5", 1300, 150)
    # ---- knobs -> per page
    for k in range(1, 5):
        x = 1300 + (k - 1) * 120
        # remember where the knob physically is (after this move is handled)
        kpos = to(u, u.obj(f"r knob{k}", x, 125), "t f f", x, 140)
        to(u, kpos, f"v engkl{k}", x + 60, 160)
        kt = to(u, kpos, "t f b", x, 175, outlet=1)
        held = to(u, kt, "expr engheld >= 0", x + 60, 200, outlet=1)
        free = u.obj("spigot", x, 200)
        cmb = u.obj("spigot", x + 60, 250)
        u.c(held, 0, cmb, 1)
        u.c(to(u, held, "== 0", x + 60, 225), 0, free, 1)
        u.c(kt, 0, free, 0)
        u.c(kt, 0, cmb, 0)
        to(u, to(u, cmb, f"list prepend {k}", x + 60, 275), "s $0-combo", x + 60, 300)
        rk = free
        for i in range(len(PAGES)):
            sp = u.obj("spigot", x, 325 + i * 50)
            u.c(rk, 0, sp, 0)
            u.c(u.obj(f"r $0-g{i}", x + 60, 325 + i * 50), 0, sp, 1)
            cur = REL_CUR.get((i, k))
            if cur:
                # continuous knobs pick up smoothly: the value moves from where it is and meets the knob at the end
                l = f"engkl{k}"
                sp = to(u, sp, f"expr min(1, max(0, if({l} < 0, {cur}, if($f1 > {l}, {cur} + ($f1 - {l}) * (1 - {cur}) / "
                               f"max(0.001, 1 - {l}), if($f1 < {l}, {cur} - ({l} - $f1) * {cur} / max(0.001, {l}), {cur})))))",
                        x, 340 + i * 50)
            to(u, sp, f"s $0-k{k}p{i}", x, 350 + i * 50)

    Y = 520
    # ---- PLAY: engine parameters (names come from the engine)
    for k in range(1, 5):
        x = 20 + (k - 1) * 220
        # knob moves (not engine loads) are also remembered per engine: value first, then store
        kt_ = to(u, u.obj(f"r $0-k{k}p0", x, Y - 75), "t b f", x, Y - 50)
        to(u, kt_, f"s $0-pv{k}", x + 60, Y - 25, outlet=1)
        to(u, kt_, "s $0-pstore", x, Y - 25)
        st = u.obj("f 0.5", x, Y + 25)
        u.c(u.obj(f"r $0-pv{k}", x, Y), 0, st, 0)
        u.c(u.obj("r $0-refresh0", x + 70, Y), 0, st, 0)
        tt = to(u, st, "t f f", x, Y + 50)
        to(u, tt, f"s eng-p{k}", x + 100, Y + 75, outlet=1)
        to(u, tt, f"v engpv{k}", x + 100, Y + 100, outlet=1)
        pk = u.obj("pack 0 s 0", x, Y + 125)
        u.c(u.obj(f"r $0-pname{k}", x + 60, Y + 100), 0, pk, 1)
        t3 = to(u, tt, "t f f", x, Y + 75)
        u.c(t3, 1, pk, 2)
        u.c(chain(u, t3, ["* 100", "i"], x, Y + 100), 0, pk, 0)
        to(u, msg_to(u, pk, f"{k} $3 $2 $1", x, Y + 150), "s $0-row0", x, Y + 175)
    # ---- SHAPE
    Y = 760
    for k, nm in ((1, "bamt"), (2, "body"), (3, "release")):
        to(u, u.obj(f"r $0-k{k}p1", 20 + (k - 1) * 220, Y - 50), f"s $0-{nm}", 20 + (k - 1) * 220, Y - 25)
    handler(u, 20, Y, "$0-bamt", 0.6, ["s eng-bamt"], ["* 100", "i"], "1 BrTone $1", 1)
    handler(u, 240, Y, "$0-body", 0.3, ["s eng-body"], ["* 100", "i"], "2 Body $1", 1)
    handler(u, 460, Y, "$0-release", 0.3, ["expr $f1 * $f1 * 2990 + 10", "s eng-release"],
            ["expr int($f1 * $f1 * 2990 + 10)"], "3 Rel $1ms", 1)
    knob_map(u, 1, 4, ["* 25", "+ 5.5", "i", "/ 10"], "$0-curve", 680, Y - 125)
    handler(u, 680, Y, "$0-curve", 1, ["t f f", "s eng-curve"], [], "4 Curve $1", 1, bar="($f1 - 0.5) / 2.5")
    # value for [expr] users
    to(u, u.obj("r eng-curve", 900, Y), "v engcurve", 900, Y + 25)
    # ---- FX
    Y = 960
    for k, nm in ((1, "dtime"), (2, "dfb"), (3, "dmix"), (4, "rmix")):
        to(u, u.obj(f"r $0-k{k}p2", 20 + (k - 1) * 220, Y - 50), f"s $0-{nm}", 20 + (k - 1) * 220, Y - 25)
    handler(u, 20, Y, "$0-dtime", 0.45, ["expr $f1 * $f1 * 1480 + 20", "s eng-dtime"],
            ["expr int($f1 * $f1 * 1480 + 20)"], "1 Delay $1ms", 2)
    handler(u, 240, Y, "$0-dfb", 0.4, ["* 0.92", "s eng-dfb"], ["* 100", "i"], "2 Feedback $1", 2)
    handler(u, 460, Y, "$0-dmix", 0.2, ["s eng-dmix"], ["* 100", "i"], "3 Dly Mix $1", 2)
    handler(u, 680, Y, "$0-rmix", 0.35, ["s eng-rmix"], ["* 100", "i"], "4 Reverb $1", 2)
    # ---- SETUP
    Y = 1160
    knob_map(u, 3, 1, ["* 4", "+ 0.5", "i", "- 2"], "$0-octave", 20, Y - 150)
    handler(u, 20, Y, "$0-octave", 0, ["* 12", "s $0-octbase"], [], "1 Octave $1", 3, bar="($f1 + 2) / 4")
    for k, nm, dflt, line, vname in ((2, "noterange", 48, "2 NoteBnd $1", "engnr"),
                                    (3, "globrange", 2, "3 Ch1Bend $1", "enggr")):
        x = 20 + (k - 1) * 220
        knob_map(u, 3, k, ["* 5.99", "i"], f"$0-{nm}-i", x, Y - 150)
        lsd = chain(u, msg_to(u, u.obj(f"r $0-{nm}-i", x + 100, Y - 150), "get $1 1", x + 100, Y - 125),
                    ["list store 1 2 3 12 24 48"], x + 100, Y - 100)
        to(u, lsd, f"s $0-{nm}", x + 100, Y - 50)
        handler(u, x, Y, f"$0-{nm}", dflt, [f"v {vname}"], [], line, 3, bar="log($f1) / log(48)")
    knob_map(u, 3, 4, ["* 70", "+ 20.5", "i", "/ 10"], "$0-vibrate", 680, Y - 150)
    handler(u, 680, Y, "$0-vibrate", 5.5, ["s eng-vibrate"], [], "4 Vib $1Hz", 3, bar="($f1 - 2) / 7")
    # ---- TUNE
    Y = 1360
    nf = len(FAMILIES)
    # knob 1: family -> its first scale ; knob 2: scale within the current family
    to(u, chain(u, u.obj("r $0-k1p4", 20, Y - 175), [f"* {nf - 0.01}", "i", "change -1", "expr engfamstart[$f1]"], 20, Y - 150),
       "s $0-tuning", 20, Y - 50)
    to(u, chain(u, u.obj("r $0-k2p4", 200, Y - 175),
                ["expr engfamstart[engfamof[engtunidx]] + min(int($f1 * engfamcount[engfamof[engtunidx]]), "
                 "engfamcount[engfamof[engtunidx]] - 1)", "change -1"], 200, Y - 150), "s $0-tuning", 200, Y - 100)
    tf = u.obj("f 1", 20, Y + 25)
    u.c(u.obj("r $0-tuning", 20, Y), 0, tf, 0)
    u.c(u.obj("r $0-refresh4", 90, Y), 0, tf, 0)
    tt = to(u, tf, "t f f f", 20, Y + 50)
    to(u, tt, "v engtunidx", 250, Y + 75, outlet=2)
    # copy the 12 offsets of scale idx into the tuning table
    lc = u.obj("f", 150, Y + 125)
    cb = to(u, tt, "t b b", 150, Y + 50, outlet=1)          # reset the counter first, then run 12 steps
    u.c(msg_to(u, cb, "0", 190, Y + 75, outlet=1), 0, lc, 1)
    u.c(to(u, msg_to(u, cb, "12", 150, Y + 75), "until", 150, Y + 100), 0, lc, 0)
    u.c(to(u, lc, "+ 1", 190, Y + 125), 0, lc, 1)
    ct = to(u, lc, "t f f", 150, Y + 150)
    tw = u.obj(f"tabwrite {JUST}", 150, Y + 200)
    u.c(ct, 1, tw, 1)
    u.c(to(u, ct, "expr engscales[engtunidx * 12 + $f1]", 150, Y + 175), 0, tw, 0)
    # display: family (row 1), scale name (row 2), position in family (row 4)
    td = to(u, tt, "t f f f", 20, Y + 75)
    to(u, to(u, td, "text get engscalenames", 20, Y + 100), "list prepend 2 -1", 20, Y + 125)
    u.c(len(u.items) - 1, 0, u.obj("s $0-row4", 20, Y + 150), 0)
    fn = chain(u, msg_to(u, to(u, td, "expr engfamof[$f1]", 120, Y + 100, outlet=1), "get $1 1", 120, Y + 125),
               ["list store " + " ".join(f for f, _ in FAMILIES)], 120, Y + 150)
    to(u, msg_to(u, fn, "1 -1 $1", 120, Y + 175), "s $0-row4", 120, Y + 200)
    pf = to(u, td, "expr $f1 - engfamstart[engfamof[$f1]] + 1; engfamcount[engfamof[$f1]]", 300, Y + 100, outlet=2)
    ppk = u.obj("pack 0 0", 300, Y + 125)
    u.c(pf, 1, ppk, 1)
    u.c(pf, 0, ppk, 0)
    to(u, msg_to(u, ppk, "4 -1 $1 of $2 - from Key", 300, Y + 150), "s $0-row4", 300, Y + 175)
    knob_map(u, 4, 3, ["* 11.99", "i"], "$0-key", 450, Y - 125)
    kf = u.obj("f 0", 450, Y + 25)
    u.c(u.obj("r $0-key", 450, Y), 0, kf, 0)
    u.c(u.obj("r $0-refresh4", 520, Y), 0, kf, 0)
    kt = to(u, kf, "t f f", 450, Y + 50)
    to(u, kt, "s eng-key", 550, Y + 75, outlet=1)
    kn = chain(u, msg_to(u, kt, "get $1 1", 450, Y + 75), [f"list store {NOTE_NAMES}"], 450, Y + 100)
    to(u, msg_to(u, kn, "3 Key $1", 450, Y + 150), "s $0-disp4", 450, Y + 175)
    r4 = u.obj("r $0-refresh4", 700, Y)
    for i, t in enumerate(()):
        to(u, msg_to(u, r4, t, 700, Y + 25 + i * 25), "s $0-disp4", 700, Y + 100)
    # ---- ENGINE
    Y = 1560
    knob_map(u, 5, 2, ["> 0.5"], "$0-mode", 240, Y - 75)
    mf = u.obj("f 0", 240, Y + 25)
    u.c(u.obj("r $0-mode", 240, Y), 0, mf, 0)
    u.c(u.obj("r $0-refresh5", 310, Y), 0, mf, 0)
    mt = to(u, mf, "t f f", 240, Y + 50)
    to(u, mt, "v engmode", 340, Y + 75, outlet=1)
    ms = to(u, mt, "sel 0 1", 240, Y + 75)
    for i, nm in enumerate(("MPE", "Standard")):
        to(u, msg_to(u, ms, f"2 MIDI {nm}", 240 + i * 90, Y + 100, outlet=i), "s $0-disp5", 240, Y + 150)
    to(u, u.obj("r $0-k3p5", 460, Y - 50), "s $0-level", 460, Y - 25)
    handler(u, 460, Y, "$0-level", 0.6, ["s eng-level"], ["* 100", "i"], "3 Level $1", 5)
    knob_map(u, 5, 4, ["* 2.99", "i"], "$0-mout", 1100, Y - 75)
    of = u.obj("f 2", 1100, Y + 25)
    u.c(u.obj("r $0-mout", 1100, Y), 0, of, 0)
    u.c(u.obj("r $0-refresh5", 1170, Y), 0, of, 0)
    ot = to(u, of, "t f f", 1100, Y + 50)
    to(u, to(u, ot, "v engmout", 1200, Y + 75, outlet=1), "s $0-outcheck", 1200, Y + 100)
    # message only when the knob is turned (not on refresh / load)
    os_ = chain(u, u.obj("r $0-k4p5", 1300, Y - 75), ["* 2.99", "i", "change", "sel 0 1 2"], 1300, Y - 50)
    for i, nm in enumerate(("Off", "Echo", "Echo+Clock")):
        to(u, msg_to(u, os_, f"list MIDI out {nm}", 1300 + i * 90, Y + 50, outlet=i), "s $0-toast", 1300, Y + 100)
    # the beat (tap tempo) is saved too
    to(u, u.obj("r $0-beat", 1400, Y), "v $0-sv-beat-dummy", 1400, Y + 25)
    r5 = u.obj("r $0-refresh5", 900, Y - 50)
    to(u, msg_to(u, r5, "4 MIDI in: -", 900, Y - 25), "s $0-disp5", 900, Y)
    en = u.obj("symbol", 1000, Y)
    u.c(u.obj("r $0-curname", 1080, Y - 50), 0, en, 1)
    u.c(r5, 0, en, 0)
    to(u, msg_to(u, en, "1 Engine $1", 1000, Y + 25), "s $0-disp5", 1000, Y + 50)
    # live MIDI on line 4 of the ENGINE page (10 updates a second at most)
    la = u.obj("list append", 700, Y + 100)
    u.c(u.obj("r eng-mon", 700, Y), 0, la, 1)
    dirty = u.obj("f", 800, Y + 50)
    u.c(msg_to(u, u.obj("r eng-mon", 800, Y), "1", 800, Y + 25), 0, dirty, 1)
    met = chain(u, u.obj("loadbang", 900, Y), ["metro 100"], 900, Y + 25)
    u.c(met, 0, dirty, 0)
    dt = chain(u, dirty, ["sel 1", "t b b"], 800, Y + 75)
    u.c(msg_to(u, dt, "0", 900, Y + 125, outlet=1), 0, dirty, 1)
    u.c(dt, 0, la, 0)
    to(u, to(u, la, "list prepend 4", 700, Y + 125), "s $0-disp5", 700, Y + 150)
    return u


def settings():
    s = Canvas("settings", w=1400, h=500)
    s.comment("settings.txt: " + " ".join(SAVED) + " engine-name  /  engines.txt: per-engine knob values", 20, 5)
    n = len(SAVED)
    # save
    # save to a folder: System > Save (/tmp/state, the Organelle copies it) or auto-save (the patch folder,
    # 2 s after the last change, like VerbRack)
    dest = s.obj("symbol", 20, 80)
    s.c(msg_to(s, s.obj("r saveState", 20, 30), "symbol /tmp/state", 20, 55), 0, dest, 0)
    svt = to(s, dest, "t b s s", 20, 105)
    ets = to(s, svt, "t s b", 400, 130, outlet=2)          # (an empty list can't be written: skip it)
    eg = s.obj("spigot", 400, 180)
    s.c(chain(s, ets, ["text size engparams", "> 0"], 460, 155, outlet=1), 0, eg, 1)
    s.c(ets, 0, eg, 0)
    msg_to(s, eg, "; engparams write $1/engines.txt", 400, 205)
    tb = to(s, svt, "t " + " ".join(["b"] * (n + 1)), 20, 130)
    pk = s.obj("pack " + " ".join(["0"] * n) + " s", 20, 200)
    for i, nm in enumerate(SAVED):
        v = to(s, tb, f"v $0-sv-{nm}", 20 + i * 70, 160, outlet=i)   # first value fires last (hot inlet)
        s.c(v, 0, pk, i)
        rr = s.obj(f"r $0-{nm}", 20 + i * 70, 300)
        to(s, rr, f"v $0-sv-{nm}", 20 + i * 70, 325)
        to(s, rr, f"v engcur{nm}", 20 + i * 70, 350)
    cur = to(s, tb, "symbol", 20 + n * 70, 160, outlet=n)
    s.c(s.obj("r $0-curname", 20 + n * 70, 135), 0, cur, 1)
    s.c(cur, 0, pk, n)
    dl = " ".join(f"${i + 2}" for i in range(n + 1))
    tf = s.obj("textfile", 20, 275)
    df = s.obj("list prepend", 20, 225)
    s.c(svt, 1, df, 1)
    s.c(pk, 0, df, 0)
    s.c(msg_to(s, df, f"clear, add {dl}, write $1/settings.txt", 20, 255), 0, tf, 0)
    # auto-save: any saved value, engine or engine knob changes -> wait 2 s -> write into the patch folder
    ad = s.obj("delay 2000", 800, 420)
    ag = s.obj("spigot", 800, 395)
    for j, rcv in enumerate(["$0-" + nm for nm in SAVED] + ["$0-curname", "$0-pstore"]):
        s.c(s.obj(f"r {rcv}", 800 + (j % 10) * 60, 330 + (j // 10) * 22), 0, ag, 0)
    s.c(msg_to(s, to(s, s.obj("loadbang", 1100, 330), "delay 6000", 1100, 355), "1", 1100, 380), 0, ag, 1)
    s.c(ag, 0, ad, 0)
    pdc = s.obj("pdcontrol", 800, 470)
    s.c(msg_to(s, ad, "dir", 800, 445), 0, pdc, 0)
    s.c(pdc, 0, dest, 0)
    # load: [s $0-loadsettings] bang; missing file -> defaults
    lt = chain(s, s.obj("r $0-loadsettings", 20, 380), ["t b b"], 20, 405)
    dmsg = s.msg(" ".join(str(d) for d in DEFAULTS) + " velvet", 120, 455)   # only when there is no settings file
    rd = msg_to(s, lt, "read settings.txt, rewind, bang", 20, 430)
    s.c(rd, 0, tf, 0)
    lu = s.obj("unpack " + " ".join(["0"] * n) + " s", 20, 480)
    s.c(dmsg, 0, lu, 0)
    s.c(tf, 0, lu, 0)
    s.c(tf, 1, dmsg, 0)
    for i, nm in enumerate(SAVED):
        to(s, lu, f"s $0-{nm}", 20 + i * 70, 505 + (i % 2) * 22, outlet=i)
    to(s, lu, "s $0-engsel-name", 20 + n * 70, 505, outlet=n)
    return s

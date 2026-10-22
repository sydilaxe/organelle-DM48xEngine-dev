"""Shared helpers and the input / processing sections."""
from pdgen import Canvas
from gen_voice import BEND, JUST

NVOICES = 8
LAYERS = 8                     # layer 0 = live, 1..7 = loop layers
NCH = 17 * LAYERS              # internal channels: 17 * layer + midi channel (0 = Organelle keys)
NOTE_NAMES = "C Db D Eb E F Gb G Ab A Bb B"


def chain(c, src, texts, x, y, outlet=0):
    """Connect src -> obj(texts[0]) -> obj(texts[1]) ... ; returns last id."""
    prev, o = src, outlet
    for i, t in enumerate(texts):
        n = c.obj(t, x, y + i * 25)
        c.c(prev, o, n, 0)
        prev, o = n, 0
    return prev


def to(c, src, text, x, y, outlet=0, inlet=0):
    n = c.obj(text, x, y)
    c.c(src, outlet, n, inlet)
    return n


def msg_to(c, src, text, x, y, outlet=0):
    n = c.msg(text, x, y)
    c.c(src, outlet, n, 0)
    return n


def setv(c, src, name, val, x, y, outlet=0):
    """src bang -> [val( -> [v name]"""
    mm = msg_to(c, src, str(val), x, y, outlet)
    to(c, mm, f"v {name}", x, y + 25)
    return mm


def tabwrite_pair(c, expr_text, table, x, y, src, outlet=0):
    """[expr index; value] -> tabwrite table[index] = value (index set first)."""
    ex = to(c, src, f"expr {expr_text}", x, y, outlet)
    val = c.obj("f", x + 100, y + 50)
    c.c(ex, 1, val, 1)
    t = to(c, ex, "t b f", x, y + 25)
    tw = c.obj(f"tabwrite {table}", x, y + 75)
    c.c(t, 1, tw, 1)
    c.c(t, 0, val, 0)
    c.c(val, 0, tw, 0)
    return ex


def midi_in():
    mi = Canvas("midi-in", w=1000, h=450)
    mi.comment("All MIDI becomes 'kind ch a b': 0 note (note vel), 1 bend (value), 2 pressure, 3 poly pressure (value note), 4 CC (cc value)", 20, 5)
    raw = mi.obj("s $0-raw", 20, 140)
    for i, (obj, n, fmt) in enumerate((("notein", 3, "0 $3 $1 $2"), ("bendin", 2, "1 $2 $1 0"),
                                       ("touchin", 2, "2 $2 $1 0"), ("polytouchin", 3, "3 $3 $1 $2"),
                                       ("ctlin", 3, "4 $3 $2 $1"))):
        x = 20 + i * 150
        o = mi.obj(obj, x, 30)
        p = mi.obj("pack" + " 0" * n, x, 60)
        for k in range(n):
            mi.c(o, k, p, k)
        mi.c(msg_to(mi, p, fmt, x, 90), 0, raw, 0)
    u = chain(mi, mi.obj("r $0-raw", 20, 190), ["unpack 0 0 0 0"], 20, 215)
    pk = mi.obj("pack 0 0 0 0", 20, 290)
    mi.c(u, 3, pk, 3)
    mi.c(u, 2, pk, 2)
    chm = to(mi, u, "expr if(engmode == 1, 1, $f1)", 100, 255, outlet=1)
    mi.comment("Standard MIDI mode: every channel becomes channel 1", 330, 255)
    mi.c(chm, 0, pk, 1)
    mi.c(u, 0, pk, 0)
    # while a tuning is being sent: drop incoming notes/controls from the DM48X (note-offs still pass)
    gate = mi.obj("spigot", 20, 345)
    gt = to(mi, pk, "t a a", 20, 320)
    mi.c(to(mi, gt, "expr (engrxmute == 0) || (($f1 == 0) && ($f4 == 0))", 120, 320, outlet=1), 0, gate, 1)
    mi.c(gt, 0, gate, 0)
    to(mi, gate, "s eng-in", 20, 370)
    mi.comment("While sending a tuning, the DM48X's own messages are ignored (avoids a burst of notes / pop)", 200, 370)
    return mi


def keys():
    """Organelle keyboard = function keys (the DM48 is the instrument).
    A key acts when RELEASED, unless a knob was turned while holding it (then the knob did a combo).
    Delay Throw acts while held."""
    ky = Canvas("keys", w=1500, h=800)
    ky.comment("Low octave: C play  C# library  D shape  D# panic  E fx  F setup  G tune  A engine  A# loop undo  B loop stop/start", 20, 5)
    ky.comment("High octave: C reverb freeze  C# delay throw (hold)  D octave down  D# octave up  E wet only  F tap tempo  F# arpeggiator  G breath permutations", 20, 22)
    ky.comment("Hold + turn a knob: B = loop speed/direction  C = reverb size  C# = throw feedback  E = reverb amount  F = tempo", 20, 39)
    ku = chain(ky, ky.obj("r notesRaw", 20, 70), ["unpack 0 0"], 20, 95)
    vel = ky.obj("f", 150, 145)
    ky.c(ku, 1, vel, 1)
    nt = to(ky, ku, "t f b", 20, 120)
    ky.c(nt, 1, vel, 0)            # bang: output the stored velocity first
    pr = ky.obj("spigot", 20, 200)            # presses
    rl = ky.obj("spigot", 250, 200)           # releases
    vt = to(ky, vel, "t f f", 150, 170)
    ky.c(to(ky, vt, "> 0", 150, 195, outlet=1), 0, pr, 1)
    ky.c(to(ky, vt, "== 0", 250, 170), 0, rl, 1)
    ky.c(nt, 0, pr, 0)
    ky.c(nt, 0, rl, 0)
    # press: remember the key, clear "moved"
    pt = to(ky, pr, "t f b f", 20, 225)
    to(ky, pt, "v engheld", 120, 250, outlet=2)
    setv(ky, pt, "engmoved", 0, 170, 250, outlet=1)
    th = to(ky, pt, "sel 73", 20, 250)
    to(ky, msg_to(ky, th, "1", 20, 275), "s eng-throw", 20, 300)
    to(ky, msg_to(ky, th, "list Delay THROW", 60, 275), "s $0-toast", 60, 300)
    # release: act if this is the held key and no knob was turned, then forget the key
    rt = to(ky, rl, "t b f f", 250, 225)
    act = ky.obj("spigot", 250, 300)
    ky.c(to(ky, rt, "expr ($f1 == engheld) && (engmoved == 0)", 350, 250, outlet=2), 0, act, 1)
    ky.c(rt, 1, act, 0)
    setv(ky, rt, "engheld", -1, 550, 250, outlet=0)
    # throw always ends on release
    to(ky, msg_to(ky, to(ky, rl, "sel 73", 450, 225), "0", 450, 250), "s eng-throw", 450, 275)
    fsel = to(ky, act, "sel 60 61 62 63 64 65 67 69 70 71 72 74 75 76 77 78 79 80 81 82 83", 250, 330)
    spage = ky.obj("s eng-page", 250, 420)
    for i, pg in ((0, 0), (1, 6), (2, 1), (4, 2), (5, 3), (6, 4), (7, 5)):
        ky.c(msg_to(ky, fsel, str(pg), 250 + i * 30, 360, outlet=i), 0, spage, 0)
    pn = msg_to(ky, fsel, "stop", 350, 390, outlet=3)
    to(ky, pn, "s eng-allnotesoff", 350, 420)
    to(ky, msg_to(ky, fsel, "list PANIC all notes off", 420, 390, outlet=3), "s $0-toast", 420, 420)
    to(ky, fsel, "s eng-loop-undo", 500, 450, outlet=8)
    to(ky, fsel, "s eng-loop-stopstart", 620, 450, outlet=9)
    def toggle(outlet, name, label, x):
        t = to(ky, fsel, "t b", x, 360, outlet=outlet)
        f = ky.obj("f 0", x, 385)
        ky.c(t, 0, f, 0)
        n = to(ky, f, "== 0", x + 40, 385)
        ky.c(n, 0, f, 1)
        tt = to(ky, n, "t f f", x, 410)
        to(ky, tt, f"s {name}", x + 60, 435, outlet=1)
        sl = to(ky, tt, "sel 1 0", x, 435)
        to(ky, msg_to(ky, sl, f"list {label} ON", x, 460), "s $0-toast", x, 510)
        to(ky, msg_to(ky, sl, f"list {label} off", x + 60, 485, outlet=1), "s $0-toast", x + 60, 510)
    toggle(10, "eng-freeze", "Freeze", 760)
    osh = ky.obj("f 0", 900, 430)
    dn = to(ky, to(ky, fsel, "t b", 900, 360, outlet=11), "f", 900, 385)
    up = to(ky, to(ky, fsel, "t b", 960, 360, outlet=12), "f", 960, 385)
    ky.c(osh, 0, dn, 1)
    ky.c(osh, 0, up, 1)
    ky.c(to(ky, dn, "expr if($f1 == -12, 0, -12)", 900, 410), 0, osh, 0)
    ky.c(to(ky, up, "expr if($f1 == 12, 0, 12)", 960, 435), 0, osh, 0)
    ost = to(ky, osh, "t f f", 900, 460)
    to(ky, ost, "s eng-octshift", 980, 485, outlet=1)
    os_ = to(ky, ost, "sel -12 0 12", 900, 485)
    for i, lab in enumerate(("Octave DOWN", "Octave normal", "Octave UP")):
        to(ky, msg_to(ky, os_, f"list {lab}", 900 + i * 90, 510, outlet=i), "s $0-toast", 900 + i * 90, 535)
    toggle(13, "eng-wetonly", "Wet only", 1180)
    # tap tempo: time between two taps
    toggle(15, "$0-arpstate", "Arp", 1550)
    toggle(16, "$0-perm", "Breath permute", 1700)
    # high G#: screen view (pages > scope > loop waveform); high A/A#/B: audio looper tap / undo / stop-start
    for i, nm in enumerate(("eng-view-next", "eng-aloop-key", "eng-aloop-undo", "eng-aloop-stopstart")):
        to(ky, to(ky, fsel, "t b", 1850 + i * 90, 360, outlet=17 + i), f"s {nm}", 1850 + i * 90, 385)
    # tap tempo: two taps less than 2 s apart (the first tap only arms it)
    tp = to(ky, fsel, "t b b b", 1350, 360, outlet=14)
    tmr = ky.obj("timer", 1350, 435)
    arm = ky.obj("spigot", 1350, 410)
    ky.c(tp, 2, arm, 0)
    ky.c(arm, 0, tmr, 1)
    ky.c(tp, 1, tmr, 0)
    ky.c(msg_to(ky, tp, "1", 1450, 385), 0, arm, 1)
    dis = to(ky, tp, "delay 2000", 1500, 385)
    ky.c(msg_to(ky, dis, "0", 1500, 410), 0, arm, 1)
    to(ky, to(ky, tmr, "moses 2000", 1350, 460), "s eng-dtime-ms", 1350, 485)
    return ky


def combos():
    """Hold a key and turn a knob: [r $0-combo] 'knob value' while [v engheld] holds the key's note."""
    cb = Canvas("combos", w=1200, h=500)
    cb.comment("Hold + turn any knob. B: loop speed (centre normal, left reverse faster, right forward faster)", 20, 5)
    cb.comment("C: reverb size  C#: throw feedback  E: reverb amount  F: tempo 40-200 BPM  F#: arp rate / pattern / octaves (knobs 1-3)", 20, 22)
    cu = chain(cb, cb.obj("r $0-combo", 20, 50), ["unpack 0 0"], 20, 75)
    vals = [cb.obj("f", 20 + i * 220, 200) for i in range(9)]
    for v_ in vals:
        cb.c(cu, 1, v_, 1)                    # value first (unpack: right outlet fires first)
    ct = to(cb, cu, "t b f", 300, 100)        # then the knob number
    to(cb, ct, "v engcombok", 400, 125, outlet=1)
    tb = to(cb, ct, "t b b", 300, 125)        # then: mark moved, dispatch on the held key
    setv(cb, tb, "engmoved", 1, 400, 150, outlet=1)
    rt = chain(cb, tb, ["v engheld", "sel 71 72 73 76 77 78 69 81 83"], 300, 150)
    for i, v_ in enumerate(vals):
        cb.c(rt, i, v_, 0)
    # B: speed
    sp = to(cb, vals[0], "expr if(abs($f1 - 0.5) < 0.06, 1, if($f1 > 0.5, pow(2, ($f1 - 0.56) / 0.44 * 2), "
                         "-pow(2, (0.44 - $f1) / 0.44 * 2)))", 20, 225)
    spc = chain(cb, sp, ["expr int($f1 * 10 + if($f1 > 0, 0.5, -0.5)) / 10", "change", "t f f"], 20, 250)
    to(cb, spc, "s eng-loop-speed", 100, 350, outlet=1)
    to(cb, msg_to(cb, spc, "list Loop speed $1 x", 20, 325), "s $0-toast", 20, 350)
    # C: reverb size
    rs = to(cb, vals[1], "t f f", 240, 225)
    to(cb, rs, "s eng-rsize", 300, 250, outlet=1)
    to(cb, msg_to(cb, to(cb, rs, "expr int($f1 * 100)", 240, 250), "list Reverb size $1", 240, 275), "s $0-toast", 240, 300)
    # C#: throw feedback 0.8 .. 1.05
    tf = chain(cb, vals[2], ["expr 0.8 + $f1 * 0.25", "t f f"], 460, 225)
    to(cb, tf, "s eng-throwfb", 520, 275, outlet=1)
    to(cb, msg_to(cb, to(cb, tf, "expr int($f1 * 100)", 460, 275), "list Throw feedback $1", 460, 300), "s $0-toast", 460, 325)
    # E: reverb amount (same as the FX page knob)
    rm = to(cb, vals[3], "t f f", 680, 225)
    to(cb, rm, "s $0-rmix", 740, 250, outlet=1)
    to(cb, msg_to(cb, to(cb, rm, "expr int($f1 * 100)", 680, 250), "list Reverb $1", 680, 275), "s $0-toast", 680, 300)
    # F#: arp - knob 1 rate, knob 2 pattern, knob 3 octave range
    ak = chain(cb, vals[5], ["expr engcombok; $f1", ], 1100, 225)
    akp = cb.obj("pack 0 0", 1100, 250)
    cb.c(ak, 1, akp, 1)
    cb.c(ak, 0, akp, 0)
    akr = to(cb, akp, "route 1 2 3", 1100, 275)
    ap = chain(cb, akr, ["expr int(min($f1, 0.999) * 6)", "change", "sel 0 1 2 3 4 5"], 1100, 300)
    for i, (nm, dv) in enumerate((("1/4", 1), ("1/8", 2), ("1/8T", 3), ("1/16", 4), ("1/16T", 6), ("1/32", 8))):
        to(cb, msg_to(cb, ap, str(dv), 1100 + i * 50, 375, outlet=i), "v engarpdiv", 1100 + i * 50, 400)
        to(cb, msg_to(cb, ap, f"list Arp rate {nm}", 1100 + i * 50, 425, outlet=i), "s $0-toast", 1100, 475)
    pp = chain(cb, akr, ["expr int(min($f1, 0.999) * 5)", "change", "t f f"], 1450, 300, outlet=1)
    to(cb, pp, "v engarppat", 1530, 350, outlet=1)
    pps = to(cb, pp, "sel 0 1 2 3 4", 1450, 350)
    for i, nm in enumerate(("up", "down", "up-down", "pedal", "random")):
        to(cb, msg_to(cb, pps, f"list Arp {nm}", 1450 + i * 60, 375, outlet=i), "s $0-toast", 1450, 425)
    po = chain(cb, akr, ["expr 1 + int(min($f1, 0.999) * 3)", "change", "t f f"], 1800, 300, outlet=2)
    to(cb, po, "v engarpoct", 1880, 350, outlet=1)
    to(cb, msg_to(cb, po, "list Arp octaves $1", 1800, 350), "s $0-toast", 1800, 375)
    # A (ENGINE page key): morph time 0.05 .. 8 s
    mt = chain(cb, vals[6], ["expr int(50 + $f1 * $f1 * 7950)", "t f f"], 1300, 225)
    to(cb, mt, "v engmorphms", 1400, 250, outlet=1)
    to(cb, msg_to(cb, to(cb, mt, "expr int($f1 / 100) / 10", 1300, 250), "list Morph time $1 s", 1300, 275),
       "s $0-toast", 1300, 300)
    # high A (audio looper): knob 1 speed/direction, 2 pitch, 3 level, 4 layer fade
    lk = chain(cb, vals[7], ["expr engcombok; $f1"], 20, 550)
    lkp = cb.obj("pack 0 0", 20, 575)
    cb.c(lk, 1, lkp, 1)
    cb.c(lk, 0, lkp, 0)
    lkr = to(cb, lkp, "route 1 2 3 4", 20, 600)
    asp = chain(cb, lkr, ["expr if(abs($f1 - 0.5) < 0.06, 1, if($f1 > 0.5, pow(2, ($f1 - 0.56) / 0.44 * 2), "
                          "-pow(2, (0.44 - $f1) / 0.44 * 2)))", "expr int($f1 * 10 + if($f1 > 0, 0.5, -0.5)) / 10",
                          "change", "t f f"], 20, 625)
    to(cb, asp, "s eng-aloop-speed", 120, 725, outlet=1)
    to(cb, msg_to(cb, asp, "list Audio speed $1 x", 20, 725), "s $0-toast", 20, 750)
    apc = chain(cb, lkr, ["expr int(($f1 - 0.5) * 24.99)", "change", "t f f"], 250, 625, outlet=1)
    to(cb, apc, "s eng-aloop-pitch", 350, 700, outlet=1)
    to(cb, msg_to(cb, apc, "list Audio pitch $1 st", 250, 700), "s $0-toast", 250, 725)
    alv = chain(cb, lkr, ["t f f"], 450, 625, outlet=2)
    to(cb, alv, "s eng-aloop-level", 550, 650, outlet=1)
    to(cb, msg_to(cb, to(cb, alv, "expr int($f1 * 100)", 450, 650), "list Audio level $1", 450, 675), "s $0-toast", 450, 700)
    afd = chain(cb, lkr, ["expr if($f1 > 0.97, 1, 0.5 + $f1 * 0.5)", "t f f"], 650, 625, outlet=3)
    to(cb, afd, "s eng-aloop-fade", 750, 675, outlet=1)
    afs = chain(cb, afd, ["expr int((1 - $f1) * 100)", "sel 0"], 650, 675)
    to(cb, msg_to(cb, afs, "list Layer fade off", 650, 725), "s $0-toast", 650, 750)
    to(cb, msg_to(cb, afs, "list Layer fade $1", 760, 725, outlet=1), "s $0-toast", 760, 750)
    # high B (audio looper): any knob = record Pre / Post the effects
    pp = chain(cb, vals[8], ["> 0.5", "change", "t f f"], 900, 550)
    to(cb, pp, "s eng-aloop-post", 1000, 600, outlet=1)
    pps = to(cb, pp, "sel 0 1", 900, 600)
    to(cb, msg_to(cb, pps, "list Audio loop PRE effects", 900, 625), "s $0-toast", 900, 650)
    to(cb, msg_to(cb, pps, "list Audio loop POST effects", 1050, 625, outlet=1), "s $0-toast", 1050, 650)
    # F: tempo
    to(cb, to(cb, vals[4], "expr 60000 / (40 + int($f1 * 160))", 900, 225), "s eng-dtime-ms", 900, 250)
    return cb


def process():
    pr = Canvas("process", w=1400, h=700)
    rlt = chain(pr, pr.obj("r eng-live", 20, 20), ["t a a"], 20, 45)
    to(pr, rlt, "s eng-rec", 120, 70, outlet=1)
    to(pr, rlt, "s eng-proc", 20, 70)
    rt = chain(pr, pr.obj("r eng-proc", 20, 110), ["route 0 1 2 3 4"], 20, 135)
    # ---- notes: remember which loop notes sound, then allocate a voice
    nt = to(pr, rt, "t a a", 20, 170)
    tabwrite_pair(pr, "if($f1 >= 17, $f1 * 128 + $f2, 0); $f3 > 0", "englheld", 150, 200, nt, outlet=1)
    # one voice per key, always: a repeated note-on first releases the key's voice, and a note-off for a key
    # that isn't sounding is dropped (otherwise [poly] can leave a voice stuck, e.g. after clearing the looper)
    kv = to(pr, nt, "expr $f1 * 128 + $f2; $f3", 20, 230)
    kpk = pr.obj("pack 0 0", 20, 255)
    pr.c(kv, 1, kpk, 1)
    pr.c(kv, 0, kpk, 0)
    kt = to(pr, kpk, "t a a a", 20, 280)
    poly = pr.obj(f"poly {NVOICES} 1", 20, 350)
    rtg = chain(pr, kt, ["expr if(($f2 > 0) && (engkeyon[$f1] > 0), $f1, -1)", "moses 0"], 300, 305, outlet=2)
    pr.c(msg_to(pr, rtg, "$1 0", 340, 330, outlet=1), 0, poly, 0)
    pg = pr.obj("spigot", 120, 325)
    pr.c(to(pr, kt, "expr ($f2 > 0) || (engkeyon[$f1] > 0)", 160, 305, outlet=1), 0, pg, 1)
    pr.c(kt, 1, pg, 0)
    pr.c(pg, 0, poly, 0)
    tabwrite_pair(pr, "$f1; $f2 > 0", "engkeyon", 500, 305, kt, outlet=0)
    ano = pr.obj("r eng-allnotesoff", 150, 300)
    pr.c(ano, 0, poly, 0)
    msg_to(pr, ano, "; engkeyon const 0", 600, 330)
    vp = pr.obj("pack 0 0 0", 20, 375)
    for k in range(3):
        pr.c(poly, k, vp, k)
    cl = to(pr, vp, f"clone -s 1 voice {NVOICES}", 20, 400)
    to(pr, cl, "s~ eng-dry", 20, 425)
    # ---- bend: "ch value" -> semitones in the table, then tell voices which channel moved
    bu = to(pr, rt, "unpack 0 0", 400, 170, outlet=1)
    bx = pr.obj(f"expr ($f2 - 8192) / 8192 * if($f1 == 17 * int($f1 / 17) + 1, enggr, engnr)", 400, 250)
    pr.c(bu, 1, bx, 1)                       # value first (cold)
    bch = to(pr, bu, "t f f f", 400, 200)    # channel last
    bf = pr.obj("f", 400, 325)
    pr.c(bch, 2, bf, 1)
    tw = pr.obj(f"tabwrite {BEND}", 470, 300)
    pr.c(bch, 1, tw, 1)
    pr.c(bch, 0, bx, 0)
    bt = to(pr, bx, "t b f", 400, 275)
    pr.c(bt, 1, tw, 0)
    pr.c(bt, 0, bf, 0)
    to(pr, bf, "s eng-bend", 400, 350)
    # ---- breath: pressure, poly pressure, CC 2/7/11 -> "ch note v127"
    brin = pr.obj("s $0-brin", 650, 280)
    pr.c(msg_to(pr, rt, "$1 -1 $2", 650, 170, outlet=2), 0, brin, 0)
    pr.c(msg_to(pr, rt, "$1 $3 $2", 750, 170, outlet=3), 0, brin, 0)
    ccr = chain(pr, msg_to(pr, rt, "$2 $1 $3", 850, 170, outlet=4), ["route 2 7 11 74 1 120 123"], 850, 195)
    ccb = pr.msg("$1 -1 $2", 850, 230)
    for o in (0, 1, 2):
        pr.c(ccr, o, ccb, 0)
    pr.c(ccb, 0, brin, 0)
    tbx = to(pr, ccr, "expr $f1; $f2 / 127", 960, 230, outlet=3)
    tpk = pr.obj("pack 0 0", 960, 255)
    pr.c(tbx, 1, tpk, 1)
    pr.c(tbx, 0, tpk, 0)
    to(pr, tpk, "s eng-timbre", 960, 280)
    to(pr, to(pr, ccr, "expr $f2 / 211.67", 1090, 230, outlet=4), "s eng-vibdepth", 1090, 255)
    ano = msg_to(pr, ccr, "stop", 1220, 230, outlet=5)
    pr.c(ccr, 6, ano, 0)
    to(pr, ano, "s eng-allnotesoff", 1220, 255)
    bx3 = chain(pr, pr.obj("r $0-brin", 650, 330), ["expr $f1; $f2; pow($f3 / 127, engcurve)"], 650, 355)
    bpk = pr.obj("pack 0 0 0", 650, 385)
    for k in (2, 1, 0):
        pr.c(bx3, k, bpk, k)
    to(pr, bpk, "s eng-breath", 650, 410)
    return pr


def monitor():
    mo = Canvas("monitor", w=1000, h=450)
    mo.comment("Live MIDI as text for the ENGINE page", 20, 5)
    mrt = chain(mo, mo.obj("r eng-live", 20, 30), ["route 0 1 2 3 4"], 20, 55)
    smon = mo.obj("s eng-mon", 20, 380)
    nt = to(mo, mrt, "t a a", 20, 90)
    nsp = to(mo, nt, "spigot", 20, 140)
    mo.c(to(mo, nt, "expr $f3 > 0", 120, 115, outlet=1), 0, nsp, 1)
    nu = to(mo, nsp, "unpack 0 0 0", 20, 165)
    npk = mo.obj("pack 0 s 0", 20, 330)
    mo.c(nu, 2, npk, 2)
    ntt = to(mo, nu, "t f f", 120, 190, outlet=1)
    mset = chain(mo, ntt, ["mod 12"], 250, 215, outlet=1)
    mset = chain(mo, msg_to(mo, mset, "get $1 1", 250, 240), [f"list store {NOTE_NAMES}"], 250, 265)
    mset = msg_to(mo, mset, "set $1%d", 250, 290)
    mkf = mo.obj("makefilename %s", 120, 305)
    mo.c(mset, 0, mkf, 0)
    oc = chain(mo, ntt, ["/ 12", "i", "- 1"], 120, 215)
    mo.items[oc] = ("obj", (180, 265, "- 1"))
    mo.c(oc, 0, mkf, 0)
    mo.c(mkf, 0, npk, 1)
    mo.c(nu, 0, npk, 0)
    mo.c(msg_to(mo, npk, "ch $1 $2 v$3", 20, 355), 0, smon, 0)
    b = to(mo, mrt, "expr $f1; $f2 - 8192", 400, 90, outlet=1)
    bp = mo.obj("pack 0 0", 400, 115)
    mo.c(b, 1, bp, 1)
    mo.c(b, 0, bp, 0)
    mo.c(msg_to(mo, bp, "ch $1 bend $2", 400, 140), 0, smon, 0)
    for i, fmt in ((2, "ch $1 AT $2"), (3, "ch $1 PolyAT $2"), (4, "ch $1 CC$2 $3")):
        mo.c(msg_to(mo, mrt, fmt, 400 + (i - 1) * 120, 180, outlet=i), 0, smon, 0)
    return mo

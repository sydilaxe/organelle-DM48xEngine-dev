"""voice.pd: one host voice. Note allocation data in, engine loaded dynamically into [pd $0-slot]."""
import os
from pdgen import Canvas

BEND = "engbend"   # semitones per internal channel (no hyphens: used in [expr])
JUST = "engjust"   # just-intonation offsets per pitch class


def build(out_dir):
    v = Canvas(w=1200, h=900)
    v.comment("Host voice. Input from [poly]: 'key vel', key = channel * 128 + note.", 20, 5)
    v.comment("Internal channels: 17 * loop layer + MIDI channel (0 = Organelle keys). Master = 17 * layer + 1.", 20, 22)
    i_in = v.obj("inlet", 20, 50)
    unp = v.obj("unpack 0 0", 20, 75)
    v.c(i_in, 0, unp, 0)
    velf = v.obj("f", 20, 125)
    keyt = v.obj("t b f", 110, 100)
    v.c(unp, 1, velf, 1)
    v.c(unp, 0, keyt, 0)
    split = v.obj("expr int($f1 / 128); $f1 % 128", 160, 125)
    v.c(keyt, 1, split, 0)
    v.c(keyt, 0, velf, 0)
    sel0 = v.obj("sel 0", 20, 150)
    v.c(velf, 0, sel0, 0)

    # outputs to the engine (via sends that the dynamic slot listens to)
    s_pitch = v.obj("s $0-pitch", 20, 840)
    s_level = v.obj("s $0-level", 150, 840)
    s_timb = v.obj("s $0-timbre", 280, 840)

    # --- note on
    on_t = v.obj("t b f b", 80, 180)
    v.c(sel0, 1, on_t, 0)
    act1 = v.msg("1", 160, 210)
    v.c(on_t, 2, act1, 0)
    stopm = v.msg("stop", 200, 210)
    v.c(on_t, 2, stopm, 0)
    tbr = v.msg("0.5 0", 250, 210)
    v.c(on_t, 2, tbr, 0)
    v.c(tbr, 0, s_timb, 0)
    velc = v.obj("expr pow($f1 / 127, $f2)", 80, 240)
    v.c(on_t, 1, velc, 0)
    v.c(v.obj("r eng-curve", 220, 240), 0, velc, 1)
    lvon = v.msg("$1 4", 80, 270)
    v.c(velc, 0, lvon, 0)
    v.c(lvon, 0, s_level, 0)
    PITCH = (f"expr $f2 + $f3 + {BEND}[$f1] + ($f1 != 17 * int($f1 / 17) + 1) * {BEND}[17 * int($f1 / 17) + 1]"
             f" + {JUST}[($f2 - $f4 + 120) % 12]")
    chA = v.obj("f", 20, 270)
    v.c(on_t, 0, chA, 0)
    pA = v.obj(PITCH, 20, 300)
    v.c(chA, 0, pA, 0)
    pjump = v.msg("$1 0", 20, 330)
    v.c(pA, 0, pjump, 0)
    v.c(pjump, 0, s_pitch, 0)

    # --- note off
    off_t = v.obj("t b b", 20, 380)
    v.c(sel0, 0, off_t, 0)
    act0 = v.msg("0", 120, 410)
    v.c(off_t, 1, act0, 0)
    relf = v.obj("f 200", 20, 410)
    v.c(v.obj("r eng-release", 20, 355), 0, relf, 1)
    v.c(off_t, 0, relf, 0)
    relt = v.obj("t f f", 20, 440)
    v.c(relf, 0, relt, 0)
    lvoff = v.msg("0 $1", 20, 470)
    v.c(relt, 0, lvoff, 0)
    v.c(lvoff, 0, s_level, 0)
    pad = v.obj("+ 50", 110, 470)
    v.c(relt, 1, pad, 0)
    dly = v.obj("delay 200", 110, 500)
    v.c(pad, 0, dly, 0)
    v.c(stopm, 0, dly, 0)
    swoff = v.msg("0", 110, 530)
    v.c(dly, 0, swoff, 0)

    # active flag -> engine on/off (remembered so a newly loaded engine gets it too)
    actf = v.obj("f 0", 410, 780)
    v.c(act1, 0, actf, 0)
    v.c(swoff, 0, actf, 0)
    actv = v.obj("f 0", 410, 805)
    v.c(actf, 0, actv, 0)
    # each slot runs while the voice sounds AND the slot is in use (engslA / engslB, set by the engine manager)
    swt = v.obj("t f f", 410, 830)
    v.c(actv, 0, swt, 0)
    v.c(v.obj("r eng-slupd", 500, 805), 0, actv, 0)
    to_ = lambda src, txt, x, y, o=0: (lambda n: (v.c(src, o, n, 0), n)[1])(v.obj(txt, x, y))
    to_(to_(swt, "expr $f1 && engslA", 410, 855, 1), "s $0-swA", 410, 880)
    to_(to_(swt, "expr $f1 && engslB", 530, 855, 0), "s $0-swB", 530, 880)
    # --- bend updates
    rb = v.obj("r eng-bend", 450, 50)
    bf = v.obj("expr ($f1 == $f2) || ($f1 == 17 * int($f2 / 17) + 1)", 450, 75)
    v.c(rb, 0, bf, 0)
    bs = v.obj("sel 1", 450, 100)
    v.c(bf, 0, bs, 0)
    chB = v.obj("f", 450, 125)
    v.c(bs, 0, chB, 0)
    pB = v.obj(PITCH, 450, 150)
    v.c(chB, 0, pB, 0)
    pgl = v.msg("$1 5", 450, 175)
    v.c(pB, 0, pgl, 0)
    v.c(pgl, 0, s_pitch, 0)
    for r, inl in (("r eng-octave", 2), ("r eng-key", 3)):
        o = v.obj(r, 800 + inl * 100, 125)
        v.c(o, 0, pA, inl)
        v.c(o, 0, pB, inl)

    # --- breath "ch note value" (note -1 = whole channel)
    rbr = v.obj("r eng-breath", 450, 230)
    brx = v.obj("expr if(($f1 == $f4) && (($f2 < 0) || ($f2 == $f5)) && $f6, $f3, -1)", 450, 255)
    v.c(rbr, 0, brx, 0)
    brm = v.obj("moses 0", 450, 280)
    v.c(brx, 0, brm, 0)
    brmsg = v.msg("$1 15", 510, 305)
    v.c(brm, 1, brmsg, 0)
    v.c(brmsg, 0, s_level, 0)
    # --- timbre "ch value"
    rtb = v.obj("r eng-timbre", 450, 350)
    tbx = v.obj("expr if(($f1 == $f3) && $f4, $f2, -1)", 450, 375)
    v.c(rtb, 0, tbx, 0)
    tbm = v.obj("moses 0", 450, 400)
    v.c(tbx, 0, tbm, 0)
    tbmsg = v.msg("$1 20", 510, 425)
    v.c(tbm, 1, tbmsg, 0)
    v.c(tbmsg, 0, s_timb, 0)

    for dst, inl in ((chA, 1), (chB, 1), (bf, 1), (brx, 3), (tbx, 2)):
        v.c(split, 0, dst, inl)
    for dst, inl in ((pA, 1), (pB, 1), (brx, 4)):
        v.c(split, 1, dst, inl)
    for g in (act1, act0):
        v.c(g, 0, brx, 5)
        v.c(g, 0, tbx, 3)

    # --- remember the current note state, to hand it to an engine that is morphing in
    lastp = v.obj("f", 900, 600)
    v.c(v.obj("r $0-pitch", 900, 550), 0, v.obj("list split 1", 900, 575), 0)
    v.c(len(v.items) - 1, 0, lastp, 1)
    lastl = v.obj("f", 1000, 600)
    v.c(v.obj("r $0-level", 1000, 550), 0, v.obj("list split 1", 1000, 575), 0)
    v.c(len(v.items) - 1, 0, lastl, 1)
    lastt = v.obj("f 0.5", 1100, 600)
    v.c(v.obj("r $0-timbre", 1100, 550), 0, v.obj("list split 1", 1100, 575), 0)
    v.c(len(v.items) - 1, 0, lastt, 1)

    # --- two engine slots (A, B) so one engine can morph into another: "eng-load A engines/NAME"
    rl = v.obj("r eng-load", 700, 450)
    rr = v.obj("route A B", 700, 475)
    v.c(rl, 0, rr, 0)
    for i, X in enumerate("AB"):
        x = 700 + i * 300
        lt = v.obj("t b b b s", x, 500)
        v.c(rr, i, lt, 0)
        idf = v.obj("f $0", x, 525)
        v.c(lt, 2, idf, 0)
        pk = v.obj("pack f s", x, 550)
        v.c(lt, 3, pk, 1)
        v.c(idf, 0, pk, 0)
        S = f"pd-$1-slot{X}"
        build_msg = "; ".join([
            f"{S} clear",
            f"{S} obj 10 10 r $1-pitch",
            f"{S} obj 110 10 r $1-level",
            f"{S} obj 210 10 r $1-timbre",
            f"{S} obj 10 60 $2 eng-{X}",
            f"{S} obj 10 110 throw~ $1-out{X}",
            f"{S} obj 310 10 r $1-sw{X}",
            f"{S} obj 310 40 switch~",
            f"{S} obj 10 35 r $1-pitch{X}",
            f"{S} obj 110 35 r $1-level{X}",
            f"{S} obj 210 35 r $1-timbre{X}",
            f"{S} connect 0 0 3 0",
            f"{S} connect 1 0 3 1",
            f"{S} connect 2 0 3 2",
            f"{S} connect 3 0 4 0",
            f"{S} connect 5 0 6 0",
            f"{S} connect 7 0 3 0",
            f"{S} connect 8 0 3 1",
            f"{S} connect 9 0 3 2",
        ])
        v.c(pk, 0, v.msg("; " + build_msg, x, 575), 0)
        # after building: switch state, then (if this voice is sounding) the current note, as a new note
        v.c(lt, 1, actv, 0)
        play = v.obj("spigot", x, 625)
        v.c(actf, 0, play, 1)
        v.c(lt, 0, play, 0)
        rp = v.obj("t b b b", x, 650)
        v.c(play, 0, rp, 0)
        v.c(rp, 2, lastt, 0)
        v.c(rp, 1, lastp, 0)
        v.c(rp, 0, lastl, 0)
        for src, nm, fmt, xx in ((lastt, "timbre", "$1 0", 0), (lastp, "pitch", "$1 0", 90), (lastl, "level", "$1 40", 180)):
            m = v.msg(fmt, x + xx, 700)
            v.c(src, 0, m, 0)
            v.c(m, 0, v.obj(f"s $0-{nm}{X}", x + xx, 725), 0)
        v.sub(Canvas(f"$0-slot{X}", w=500, h=200), x, 760)
    # --- output: equal-power crossfade between the slots ([r~ eng-xf~] 0 = A, 1 = B)
    xf = v.obj("r~ eng-xf~", 200, 870)
    ga = v.obj("cos~", 200, 920)
    v.c(v.obj("*~ 0.25", 200, 895), 0, ga, 0)
    v.c(xf, 0, len(v.items) - 3 + 1 if False else v.items.index(("obj", (200, 895, "*~ 0.25"))), 0)
    gb_in = v.obj("expr~ ($v1 - 1) * 0.25", 300, 895)
    v.c(xf, 0, gb_in, 0)
    gb = v.obj("cos~", 300, 920)
    v.c(gb_in, 0, gb, 0)
    oa, ob = v.obj("*~", 20, 945), v.obj("*~", 120, 945)
    v.c(v.obj("catch~ $0-outA", 20, 870), 0, oa, 0)
    v.c(v.obj("catch~ $0-outB", 120, 870), 0, ob, 0)
    v.c(ga, 0, oa, 1)
    v.c(gb, 0, ob, 1)
    osum = v.obj("+~", 20, 970)
    v.c(oa, 0, osum, 0)
    v.c(ob, 0, osum, 1)
    v.c(osum, 0, v.obj("outlet~", 20, 995), 0)
    v.save(os.path.join(out_dir, "voice.pd"))

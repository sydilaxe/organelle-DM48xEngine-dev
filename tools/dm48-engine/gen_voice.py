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
    s_sw = v.obj("s $0-sw", 410, 840)

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
    v.c(actf, 0, s_sw, 0)

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

    # --- dynamic engine slot
    rl = v.obj("r eng-load", 700, 500)
    lt = v.obj("t b b s", 700, 525)
    v.c(rl, 0, lt, 0)
    idf = v.obj("f $0", 700, 550)
    v.c(lt, 1, idf, 0)
    pk = v.obj("pack f s", 700, 575)
    v.c(lt, 2, pk, 1)
    v.c(lt, 0, actf, 0)  # after loading: tell the new engine whether this voice is sounding
    v.c(idf, 0, pk, 0)
    S = "pd-$1-slot"
    build_msg = "; ".join([
        f"{S} clear",
        f"{S} obj 10 10 r $1-pitch",
        f"{S} obj 110 10 r $1-level",
        f"{S} obj 210 10 r $1-timbre",
        f"{S} obj 10 60 $2",
        f"{S} obj 10 110 throw~ $1-out",
        f"{S} obj 310 10 r $1-sw",
        f"{S} obj 310 40 switch~",
        f"{S} connect 0 0 3 0",
        f"{S} connect 1 0 3 1",
        f"{S} connect 2 0 3 2",
        f"{S} connect 3 0 4 0",
        f"{S} connect 5 0 6 0",
    ])
    bm = v.msg("; " + build_msg, 700, 600)
    v.c(pk, 0, bm, 0)
    slot = Canvas("$0-slot", w=500, h=200)
    v.sub(slot, 700, 700)
    v.c(v.obj("catch~ $0-out", 20, 870), 0, v.obj("outlet~", 20, 895), 0)
    v.save(os.path.join(out_dir, "voice.pd"))

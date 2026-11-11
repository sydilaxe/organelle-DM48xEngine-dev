"""Breath arpeggiator. Sits between MIDI in and everything else:
   [r eng-in] -> (arp off: pass through) -> [s eng-live]
   arp on: held notes are collected and played one at a time, each on its own MPE channel.

   ARP page (low G#): rate (1/2 .. 1/32), pattern (up, down, up-down, pedal, random), octaves (1-4),
                      gate (note length, 5-100 % of a step; the note then fades at the Release rate)
   ARP-BR page (low G# again): how much breath drives volume, density, spread and ratchets (0..1 each)
   High G toggles permutations: each pass through the pattern rotates the note order,
   and every other pass is mirrored.
   Breath (latest live pressure / CC 2, 7, 11) shapes how the notes come out:
     volume  - arp notes follow the breath (0: they play at full level)
     density - soft breath plays only some steps, stronger breath fills them in
     spread  - above half breath, notes jump an octave up or down and drift off the grid
     ratchet - near full breath, some steps double
"""
from pdgen import Canvas
from sec_core import chain, to, msg_to

B = "(engarpbr / 127)"
STEP = "(engbeat / max(1, engarpdiv))"


def arp():
    a = Canvas("arpeggiator", w=1700, h=1000)
    a.comment("Breath arpeggiator. Held notes in text 'engarp' as 'note ch'. Breath = density + scatter (see README).", 20, 5)
    live = a.obj("s eng-live", 20, 950)
    inp = chain(a, a.obj("r eng-in", 20, 30), ["t a a"], 20, 55)
    # ---- breath tracker (any live channel): pressure (kind 2) or CC 2/7/11 (kind 4)
    br = to(a, inp, "route 2 4", 400, 80, outlet=1)
    to(a, to(a, br, "expr $f2", 400, 105), "v engarpbr", 400, 130)
    cc = to(a, br, "expr if(($f2 == 2) || ($f2 == 7) || ($f2 == 11), $f3, -1)", 520, 105, outlet=1)
    to(a, to(a, cc, "moses 0", 520, 130), "v engarpbr", 560, 155, outlet=1)
    # ---- arp off: everything passes. arp on: notes are captured, the rest passes.
    sw = to(a, inp, "t a a", 20, 105)
    isnote = to(a, sw, "expr ($f1 == 0) && (engarpon > 0)", 120, 130, outlet=1)
    pas = a.obj("spigot", 20, 180)
    cap = a.obj("spigot", 120, 180)
    a.c(to(a, isnote, "== 0", 120, 155), 0, pas, 1)
    a.c(isnote, 0, cap, 1)
    a.c(sw, 0, pas, 0)
    a.c(sw, 0, cap, 0)
    # arp on: breath (pressure, poly pressure, CC 2/7/11) scaled by the Volume amount: 0 = full level
    VM = "if(engarpon > 0, 127 - engarpvol * (127 - {v}), {v})"
    pr = to(a, pas, "route 2 3 4", 20, 205)
    a.c(pr, 3, live, 0)
    for o, (ex, n, fmt) in enumerate((("$f1; " + VM.format(v="$f2"), 2, "2 $1 $2"),
                                      ("$f1; " + VM.format(v="$f2") + "; $f3", 3, "3 $1 $2 $3"),
                                      ("$f1; $f2; if(($f2 == 2) || ($f2 == 7) || ($f2 == 11), " + VM.format(v="$f3") + ", $f3)",
                                       3, "4 $1 $2 $3"))):
        x = 20 + o * 30
        e = to(a, pr, "expr " + ex, x, 230 + o * 100, outlet=o)
        pk = a.obj("pack" + " 0" * n, x, 255 + o * 100)
        for k in reversed(range(n)):
            a.c(e, k, pk, k)
        a.c(msg_to(a, pk, fmt, x, 280 + o * 100), 0, live, 0)
    # ---- held notes: "0 ch note vel" -> "ch note vel" (channel arrives last = hot)
    cu = to(a, cap, "unpack 0 0 0 0", 120, 205)
    onoff = a.obj("pack 0 0 0", 120, 255)
    a.c(cu, 3, onoff, 2)
    a.c(cu, 2, onoff, 1)
    a.c(cu, 1, onoff, 0)
    t = to(a, onoff, "t a a", 120, 280)
    on, off = a.obj("spigot", 120, 330), a.obj("spigot", 250, 330)
    vt = to(a, t, "expr $f3 > 0", 200, 305, outlet=1)
    a.c(vt, 0, on, 1)
    a.c(to(a, vt, "== 0", 250, 305), 0, off, 1)
    a.c(t, 0, on, 0)
    a.c(t, 0, off, 0)
    onl = msg_to(a, to(a, on, "list split 2", 120, 355), "$2 $1", 120, 380)
    ont = to(a, onl, "t a a", 120, 405)
    addg = a.obj("spigot", 120, 455)
    a.c(chain(a, ont, ["text search engarp 0 1", "< 0"], 220, 430, outlet=1), 0, addg, 1)
    a.c(ont, 0, addg, 0)
    to(a, addg, "text insert engarp 1e+06", 120, 505)
    msg_to(a, addg, "; engarp sort", 250, 505)       # keep held notes in pitch order
    ofl = msg_to(a, to(a, off, "list split 2", 250, 355), "$2 $1", 250, 380)
    dels = chain(a, ofl, ["text search engarp 0 1", "moses 0"], 350, 405)
    to(a, dels, "text delete engarp", 390, 455, outlet=1)

    # ---- clock: one step per beat / division
    met = a.obj("metro 125", 700, 250)
    ars = to(a, a.obj("r $0-arpstate", 700, 175), "t f f", 700, 200)
    to(a, ars, "v engarpon", 800, 225, outlet=1)
    run = to(a, ars, "sel 1 0", 700, 225)
    a.c(msg_to(a, run, "bang", 700, 250), 0, met, 0)
    a.c(msg_to(a, run, "stop", 760, 250, outlet=1), 0, met, 0)
    st = to(a, met, "t b b", 700, 275)
    a.c(to(a, st, f"expr max(15, {STEP})", 850, 300, outlet=1), 0, met, 1)
    step = chain(a, st, ["text size engarp", "moses 1"], 700, 300)
    last = a.obj("list", 1150, 800)                 # the sounding arp note "ch note"
    release = msg_to(a, to(a, last, "list split 2", 1150, 825), "0 $1 $2 0", 1150, 850)
    a.c(release, 0, live, 0)
    a.c(step, 0, last, 0)                           # nothing held: release
    go = to(a, step, "t b f", 760, 350, outlet=1)
    to(a, go, "v engarpn", 860, 375, outlet=1)
    nx = chain(a, go, ["expr engarpi + 1", "t f f"], 760, 375)
    to(a, nx, "v engarpi", 900, 425, outlet=1)
    # pattern position over L = n * octaves
    L = "(engarpn * max(1, engarpoct))"
    M = f"($f1 % max(1, 2 * {L} - 2))"
    pos = to(a, nx, f"expr if(engarppat == 0, $f1 % {L}, if(engarppat == 1, {L} - 1 - $f1 % {L}, "
                    f"if(engarppat == 2, if({L} > 1, if({M} < {L}, {M}, 2 * {L} - 2 - {M}), 0), "
                    f"if(engarppat == 3, if($f1 % 2 == 0, 0, if({L} > 1, 1 + (int($f1 / 2) % ({L} - 1)), 0)), "
                    f"random(0, {L})))))", 760, 450)
    # permutation (rotate per pass, mirror every other pass), then octave
    C = f"int(engarpi / {L})"
    R = f"((($f1 % engarpn) + {C}) % engarpn)"
    li = to(a, pos, f"expr if(engperm > 0, if({C} % 2, engarpn - 1 - {R}, {R}), $f1 % engarpn); "
                    f"int($f1 / engarpn) * 12", 760, 500)
    # density: play this step?  p = 0.25 + 0.75 * min(1, breath * 1.4)
    dens = a.obj("spigot", 760, 575)
    # look up the note: [t f b b] -> density decision, octave into [f], then the list index
    sel = to(a, li, "t f b b", 760, 525)
    a.c(to(a, sel, f"expr random(0, 1000) < 1000 * (1 - engarpdens * 0.75 * (1 - min(1, {B} * 1.4)))", 1000, 550,
           outlet=2), 0, dens, 1)
    octf = a.obj("f", 900, 575)
    a.c(li, 1, octf, 1)
    a.c(sel, 1, octf, 0)
    nn = a.obj("pack 0 0 0", 760, 650)              # note, octave, ch
    a.c(octf, 0, nn, 1)
    a.c(sel, 0, dens, 0)
    gu = chain(a, dens, ["text get engarp", "unpack 0 0"], 760, 600)
    a.c(gu, 1, nn, 2)
    a.c(gu, 0, nn, 0)
    # scatter: above half breath, sometimes an octave up/down (two octaves when strong)
    S = f"(engarpspread * max(0, ({B} - 0.45) / 0.55))"
    nt = to(a, nn, f"expr $f3; $f1 + $f2 + if(random(0, 1000) < {S} * 550, (random(0, 2) * 2 - 1) * "
                   f"if({S} > 0.6, 12 * (1 + random(0, 2)), 12), 0)", 760, 675)
    npk = a.obj("pack 0 0", 760, 700)
    a.c(nt, 1, npk, 1)
    a.c(nt, 0, npk, 0)
    # scatter timing: wait a random part of the step before playing (more with breath)
    hold = a.obj("list", 760, 775)
    a.c(npk, 0, hold, 1)
    jit = a.obj("delay", 760, 750)
    a.c(to(a, npk, f"expr random(0, 1000) / 1000 * {S} * 0.35 * {STEP}", 860, 725), 0, jit, 0)
    a.c(jit, 0, hold, 0)
    play = to(a, hold, "t a a b", 760, 800)
    a.c(play, 2, last, 0)                            # release the previous arp note
    # velocity: breath at the step, by the Volume amount (0 = 127)
    vt2 = to(a, play, "t a b", 860, 825, outlet=1)
    vla = a.obj("list append", 860, 875)
    a.c(to(a, vt2, "expr max(1, int(127 - engarpvol * (127 - engarpbr)))", 940, 850, outlet=1), 0, vla, 1)
    a.c(vt2, 0, vla, 0)
    a.c(msg_to(a, vla, "0 $1 $2 $3", 860, 900), 0, live, 0)
    a.c(play, 0, last, 1)
    # note length: Gate (part of a step); ratchet near full breath: a second hit half a step later
    gate = a.obj("delay", 1300, 850)
    a.c(to(a, play, f"expr max(10, {STEP} * engarpgate)", 1300, 825, outlet=1), 0, gate, 0)
    a.c(gate, 0, last, 0)
    rat = a.obj("delay", 1000, 875)
    rx = to(a, play, f"expr if(({B} > 0.85) && (random(0, 1000) < 350 * engarprat), {STEP} / 2, -1)", 1000, 825, outlet=1)
    a.c(to(a, rx, "moses 0", 1000, 850), 1, rat, 0)
    a.c(rat, 0, hold, 0)
    # arp off: release, forget held notes, stop pending hits
    oa = chain(a, a.obj("r $0-arpstate", 1300, 175), ["sel 0", "t b b"], 1300, 200)
    a.c(oa, 1, last, 0)
    msg_to(a, oa, "; engarp clear", 1300, 275)
    stp = msg_to(a, oa, "stop", 1400, 250, outlet=1)
    for d in (gate, jit, rat):
        a.c(stp, 0, d, 0)
    return a

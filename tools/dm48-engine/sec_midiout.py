"""MIDI out: echo of everything the engine plays (live DM48 + looper) and MIDI clock."""
from pdgen import Canvas
from sec_core import chain, to, msg_to


def midi_out():
    o = Canvas("midi-out", w=1400, h=700)
    o.comment("Echo: live + loop events back out on their MIDI channel (internal channel % 17). Off while a tuning is sent.", 20, 5)
    g = o.obj("spigot", 20, 75)
    o.c(o.obj("r eng-proc", 20, 30), 0, g, 0)
    to(o, o.obj("r $0-outgate", 100, 30), "t f", 100, 50)
    o.c(len(o.items) - 1, 0, g, 1)
    rt = to(o, g, "route 0 1 2 3 4", 20, 100)
    specs = [  # (expr producing outputs right-to-left into the object's inlets, object)
        ("expr $f2; $f3; $f1 % 17", "noteout"),
        ("expr $f2 - 8192; $f1 % 17", "bendout"),
        ("expr $f2; $f1 % 17", "touchout"),
        ("expr $f2; $f3; $f1 % 17", "polytouchout"),
        ("expr $f3; $f2; $f1 % 17", "ctlout"),
    ]
    for k, (ex, obj) in enumerate(specs):
        x = 20 + k * 260
        t = to(o, rt, "t a a", x, 130, outlet=k)
        sp = o.obj("spigot", x, 180)
        o.c(to(o, t, "expr ($f1 % 17) > 0", x + 80, 155, outlet=1), 0, sp, 1)
        o.c(t, 0, sp, 0)
        e = to(o, sp, ex, x, 205)
        n = ex.count(";") + 1
        dst = o.obj(obj, x, 240)
        for i in range(n):
            o.c(e, i, dst, i)
    # gate = (MIDI out mode > 0) and not sending a tuning
    gx = o.obj("expr (engmout > 0) && (engsending == 0)", 20, 400)
    o.c(o.obj("r $0-outcheck", 20, 375), 0, gx, 0)
    to(o, gx, "s $0-outgate", 20, 425)
    return o


def clock():
    c = Canvas("midi-clock", w=1000, h=600)
    c.comment("24 clocks per beat at the tap tempo when MIDI Out = Echo+Clock. Looper PLAY sends Start, STOP / clear send Stop.", 20, 5)
    mo = c.obj("midiout", 20, 400)
    # tempo
    bt = chain(c, c.obj("r $0-beat", 300, 30), ["t f f"], 300, 55)
    to(c, bt, "v engbeat", 380, 80, outlet=1)
    met = c.obj("metro 20.833", 20, 200)
    c.c(to(c, bt, "expr $f1 / 24 / max(0.25, abs(englspd))", 300, 80), 0, met, 1)
    # the clock follows the looper speed
    c.c(to(c, c.obj("r eng-loop-speed", 500, 55), "expr engbeat / 24 / max(0.25, abs($f1))", 500, 80), 0, met, 1)
    c.c(msg_to(c, met, "248", 20, 225), 0, mo, 0)
    # run / stop with the MIDI out mode
    on = chain(c, c.obj("r $0-outcheck", 20, 30), ["expr (engmout == 2) && (engsending == 0)", "change", "sel 1 0"], 20, 55)
    c.c(msg_to(c, on, "bang", 20, 130), 0, met, 0)
    c.c(msg_to(c, on, "stop", 100, 130, outlet=1), 0, met, 0)
    # transport from the looper
    ls = chain(c, c.obj("r eng-loopstat", 600, 30), ["t b"], 600, 55)
    st = chain(c, ls, ["v englstate", "change", "t f f"], 600, 80)
    run = chain(c, st, ["expr ($f1 == 2) && (engmout == 2)", "sel 1"], 600, 155)
    tb = to(c, run, "t b b", 600, 205)
    c.c(msg_to(c, tb, "250", 600, 230, outlet=1), 0, mo, 0)   # Start
    c.c(tb, 0, met, 0)                                         # restart clock in phase
    stp = chain(c, st, ["expr (($f1 == 0) || ($f1 == 4)) && (engmout == 2)", "sel 1"], 750, 130, outlet=1)
    c.c(msg_to(c, stp, "252", 750, 180), 0, mo, 0)             # Stop
    # tap tempo also sets the clock (and shows BPM)
    tp = chain(c, c.obj("r eng-dtime-ms", 300, 300), ["t f f"], 300, 325)
    to(c, tp, "s $0-beat", 380, 350, outlet=1)
    bp = to(c, tp, "expr int(60000 / $f1 + 0.5)", 300, 350)
    to(c, msg_to(c, bp, "list Tempo $1 BPM", 300, 375), "s $0-toast", 300, 400)
    return c

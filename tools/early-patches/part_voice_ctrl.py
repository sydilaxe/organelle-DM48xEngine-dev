"""Generate the 'MPE Reed' Organelle patch (main.pd + voice.pd)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdgen import Canvas  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "MPE Reed"
os.makedirs(OUT, exist_ok=True)

BEND_TABLE = "mpebend"  # no hyphen: used inside [expr]
NVOICES = 8

# ---------------------------------------------------------------- voice.pd
v = Canvas(w=1100, h=760)
v.comment("One voice. Gets 'key vel' from [poly] where key = channel*128 + note.", 20, 10)
v.comment("Follows bend / breath / timbre sent on its own MIDI channel.", 20, 28)

v.column(20, 60)
i_in = v.obj("inlet")
unp = v.obj("unpack 0 0")
v.c(i_in, 0, unp, 0)
velf = v.obj("f", 20, 140)
keyt = v.obj("t b f", 110, 140)
v.c(unp, 1, velf, 1)
v.c(unp, 0, keyt, 0)
split = v.obj("expr int($f1/128); $f1 % 128", 160, 170)  # out0 ch, out1 note
v.c(keyt, 1, split, 0)
v.c(keyt, 0, velf, 0)
sel0 = v.obj("sel 0", 20, 200)
v.c(velf, 0, sel0, 0)

# --- note on: [t b f b]  (right bang first: gate on, switch on, stop release timer)
on_t = v.obj("t b f b", 80, 240)
v.c(sel0, 1, on_t, 0)
gate1 = v.msg("1", 160, 270)
v.c(on_t, 2, gate1, 0)
stopm = v.msg("stop", 200, 270)
v.c(on_t, 2, stopm, 0)
tb_reset = v.msg("0.5", 250, 270)  # timbre back to neutral
v.c(on_t, 2, tb_reset, 0)

velcurve = v.obj("expr pow($f1/127, $f2)", 80, 300)
v.c(on_t, 1, velcurve, 0)
rcurve = v.obj("r mpe-curve", 200, 300)
v.c(rcurve, 0, velcurve, 1)
ampon = v.msg("$1 4", 80, 330)
v.c(velcurve, 0, ampon, 0)

# pitch on note-on: jump
chA = v.obj("f", 20, 330)
v.c(on_t, 0, chA, 0)
pitchA = v.obj(f"expr $f2 + $f3 + {BEND_TABLE}[$f1] + ($f1 != 1) * {BEND_TABLE}[1]", 20, 360)
v.c(chA, 0, pitchA, 0)

# --- note off: gate off, release ramp, then switch dsp off
off_t = v.obj("t b b", 20, 420)
v.c(sel0, 0, off_t, 0)
gate0 = v.msg("0", 120, 450)
v.c(off_t, 1, gate0, 0)
relf = v.obj("f 300", 20, 450)
v.c(off_t, 0, relf, 0)
rrel = v.obj("r mpe-release", 20, 395)
v.c(rrel, 0, relf, 1)
rel_t = v.obj("t f f", 20, 480)
v.c(relf, 0, rel_t, 0)
ampoff = v.msg("0 $1", 20, 510)
v.c(rel_t, 0, ampoff, 0)
relpad = v.obj("+ 40", 110, 510)
v.c(rel_t, 1, relpad, 0)
deloff = v.obj("delay 300", 110, 570)
v.c(relpad, 0, deloff, 0)  # float into [delay] = set time and start
v.c(stopm, 0, deloff, 0)
swoff = v.msg("0", 110, 600)
v.c(deloff, 0, swoff, 0)

# --- bend updates: [r mpe-bend] gives the channel whose bend changed
rbend = v.obj("r mpe-bend", 400, 60)
bfilt = v.obj("expr ($f1 == $f2) || ($f1 == 1)", 400, 90)
v.c(rbend, 0, bfilt, 0)
bsel = v.obj("sel 1", 400, 120)
v.c(bfilt, 0, bsel, 0)
chB = v.obj("f", 400, 150)
v.c(bsel, 0, chB, 0)
pitchB = v.obj(f"expr $f2 + $f3 + {BEND_TABLE}[$f1] + ($f1 != 1) * {BEND_TABLE}[1]", 400, 180)
v.c(chB, 0, pitchB, 0)
pglide = v.msg("$1 5", 400, 210)
v.c(pitchB, 0, pglide, 0)

roct = v.obj("r mpe-octave", 700, 150)
v.c(roct, 0, pitchA, 2)
v.c(roct, 0, pitchB, 2)

# --- breath: [r mpe-breath] "ch note value" (note -1 = whole channel)
rbr = v.obj("r mpe-breath", 400, 270)
brx = v.obj("expr if(($f1 == $f4) && (($f2 < 0) || ($f2 == $f5)) && $f6, $f3, -1)", 400, 300)
v.c(rbr, 0, brx, 0)
brm = v.obj("moses 0", 400, 330)
v.c(brx, 0, brm, 0)
brmsg = v.msg("$1 15", 460, 360)
v.c(brm, 1, brmsg, 0)

# --- timbre (MPE Y / CC74): [r mpe-timbre] "ch value"
rtb = v.obj("r mpe-timbre", 400, 420)
tbx = v.obj("expr if(($f1 == $f3) && $f4, $f2, -1)", 400, 450)
v.c(rtb, 0, tbx, 0)
tbm = v.obj("moses 0", 400, 480)
v.c(tbx, 0, tbm, 0)
tbmsg = v.msg("$1 20", 460, 510)
v.c(tbm, 1, tbmsg, 0)

# distribute channel / note / gate into cold inlets
v.c(split, 0, chA, 1)
v.c(split, 0, chB, 1)
v.c(split, 0, bfilt, 1)
v.c(split, 0, brx, 3)
v.c(split, 0, tbx, 2)
v.c(split, 1, pitchA, 1)
v.c(split, 1, pitchB, 1)
v.c(split, 1, brx, 4)
v.c(gate1, 0, brx, 5)
v.c(gate0, 0, brx, 5)
v.c(gate1, 0, tbx, 3)
v.c(gate0, 0, tbx, 3)


"""Generate the MPE Super Organelle patch (main.pd, voice.pd, bsaw.pd)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdgen import Canvas  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "MPE Super"
KEY = int(sys.argv[2]) if len(sys.argv) > 2 else 0
os.makedirs(OUT, exist_ok=True)

BEND_TABLE = "mpebend"  # no hyphen: used inside [expr]
NVOICES = 6

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
pitchA = v.obj(f"expr $f2 + $f3 + {BEND_TABLE}[$f1] + ($f1 != 1) * {BEND_TABLE}[1] + mpejust[($f2 - $f4 + 120) % 12]", 20, 360)
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
pitchB = v.obj(f"expr $f2 + $f3 + {BEND_TABLE}[$f1] + ($f1 != 1) * {BEND_TABLE}[1] + mpejust[($f2 - $f4 + 120) % 12]", 400, 180)
v.c(chB, 0, pitchB, 0)
pglide = v.msg("$1 5", 400, 210)
v.c(pitchB, 0, pglide, 0)

roct = v.obj("r mpe-octave", 700, 150)
v.c(roct, 0, pitchA, 2)
v.c(roct, 0, pitchB, 2)
rkey = v.obj("r mpe-key", 800, 150)
v.c(rkey, 0, pitchA, 3)
v.c(rkey, 0, pitchB, 3)

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


# ---------------------------------------------------------------- bsaw.pd
# Band-limited saw: naive saw with the jump replaced by a smooth half-sine step
# that lasts N samples-worth of phase (N = sr / (2.5 * freq), sent in as a signal).
bs = Canvas(w=700, h=600)
bs.comment("Band-limited saw. Left: frequency (signal). Right: N = sr / (2.5 * freq).", 20, 5)
b_f = bs.obj("inlet~", 20, 30)
b_n = bs.obj("inlet~", 300, 30)
ph = bs.obj("phasor~", 20, 60)
bs.c(b_f, 0, ph, 0)
naive = bs.obj("-~ 0.5", 20, 90)
bs.c(ph, 0, naive, 0)
u1 = bs.obj("+~ 0.5", 150, 90)
bs.c(ph, 0, u1, 0)
u2 = bs.obj("wrap~", 150, 115)
u3 = bs.obj("-~ 0.5", 150, 140)
bs.chain(u1, u2, u3)
st1 = bs.obj("*~ 1e+06", 150, 170)
st2 = bs.obj("clip~ -0.5 0.5", 150, 195)
bs.chain(u3, st1, st2)
w1 = bs.obj("*~", 300, 170)
bs.c(u3, 0, w1, 0)
bs.c(b_n, 0, w1, 1)
w2 = bs.obj("clip~ -0.5 0.5", 300, 195)
w3 = bs.obj("*~ 0.5", 300, 220)
w4 = bs.obj("-~ 0.25", 300, 245)
w5 = bs.obj("cos~", 300, 270)
w6 = bs.obj("*~ 0.5", 300, 295)
bs.chain(w1, w2, w3, w4, w5, w6)
a1 = bs.obj("+~", 20, 330)
bs.c(naive, 0, a1, 0)
bs.c(st2, 0, a1, 1)
a2 = bs.obj("-~", 20, 360)
bs.c(a1, 0, a2, 0)
bs.c(w6, 0, a2, 1)
bs.c(a2, 0, bs.obj("outlet~", 20, 400), 0)
bs.save(os.path.join(OUT, "bsaw.pd"))

# --- DSP subpatch, switched off while the voice is silent
d = Canvas("dsp", w=1100, h=800)
d_ip = d.obj("inlet", 20, 20)
d_ia = d.obj("inlet", 400, 20)
d_it = d.obj("inlet", 650, 20)
d_is = d.obj("inlet", 900, 20)
sw = d.obj("switch~", 900, 60)
d.c(d_is, 0, sw, 0)

pl = d.obj("line~", 20, 60)
d.c(d_ip, 0, pl, 0)
vib = d.obj("r~ mpe-vib", 110, 60)
padd = d.obj("+~", 20, 90)
d.c(pl, 0, padd, 0)
d.c(vib, 0, padd, 1)
mt = d.obj("mtof~", 20, 115)
d.c(padd, 0, mt, 0)
f = d.obj("clip~ 1 20000", 20, 140)
d.c(mt, 0, f, 0)
# N = (sr/2.5) / f
rk = d.obj("r~ mpe-sawk", 120, 165)
nn = d.obj("/~", 120, 190)
d.c(rk, 0, nn, 0)
d.c(f, 0, nn, 1)
# detune: f*(1-d), f*(1+d)
rdt = d.obj("r~ mpe-detune", 260, 140)
dm = d.obj("*~", 260, 165)
d.c(f, 0, dm, 0)
d.c(rdt, 0, dm, 1)
flo = d.obj("-~", 200, 220)
d.c(f, 0, flo, 0)
d.c(dm, 0, flo, 1)
fhi = d.obj("+~", 300, 220)
d.c(f, 0, fhi, 0)
d.c(dm, 0, fhi, 1)
saws = []
for i, src in enumerate((f, flo, fhi)):
    s = d.obj("bsaw", 20 + i * 140, 260)
    d.c(src, 0, s, 0)
    d.c(nn, 0, s, 1)
    saws.append(s)
side = d.obj("+~", 160, 290)
d.c(saws[1], 0, side, 0)
d.c(saws[2], 0, side, 1)
sideg = d.obj("*~ 0.8", 160, 315)
d.c(side, 0, sideg, 0)
mix1 = d.obj("+~", 20, 340)
d.c(saws[0], 0, mix1, 0)
d.c(sideg, 0, mix1, 1)
# sub oscillator (sine, one octave down)
fsub = d.obj("*~ 0.5", 460, 260)
d.c(f, 0, fsub, 0)
osub = d.obj("osc~", 460, 285)
d.c(fsub, 0, osub, 0)
rsub = d.obj("r~ mpe-sub", 540, 285)
gsub = d.obj("*~", 460, 310)
d.c(osub, 0, gsub, 0)
d.c(rsub, 0, gsub, 1)
mix2 = d.obj("+~", 20, 370)
d.c(mix1, 0, mix2, 0)
d.c(gsub, 0, mix2, 1)
mixg = d.obj("*~ 0.45", 20, 395)
d.c(mix2, 0, mixg, 0)

env = d.obj("line~", 400, 60)
d.c(d_ia, 0, env, 0)
tbl = d.obj("line~", 650, 60)
d.c(d_it, 0, tbl, 0)

# cutoff (MIDI units) = cut + env*breathamt + (timbre-0.5)*24 + (pitch-60)*0.5
rcut = d.obj("r~ mpe-cut", 650, 120)
rbam = d.obj("r~ mpe-bamt", 500, 90)
eb = d.obj("*~", 400, 120)
d.c(env, 0, eb, 0)
d.c(rbam, 0, eb, 1)
c1 = d.obj("+~", 400, 150)
d.c(eb, 0, c1, 0)
d.c(rcut, 0, c1, 1)
tb1 = d.obj("-~ 0.5", 760, 90)
d.c(tbl, 0, tb1, 0)
tb2 = d.obj("*~ 24", 760, 115)
d.c(tb1, 0, tb2, 0)
c2 = d.obj("+~", 400, 180)
d.c(c1, 0, c2, 0)
d.c(tb2, 0, c2, 1)
kt1 = d.obj("-~ 60", 560, 180)
d.c(pl, 0, kt1, 0)
kt2 = d.obj("*~ 0.5", 560, 205)
d.c(kt1, 0, kt2, 0)
c3 = d.obj("+~", 400, 230)
d.c(c2, 0, c3, 0)
d.c(kt2, 0, c3, 1)
cc = d.obj("clip~ 0 135", 400, 255)
cm = d.obj("mtof~", 400, 280)
ch = d.obj("clip~ 20 8000", 400, 305)
d.chain(c3, cc, cm, ch)

# Moog-style ladder filter (Pd's bob~), with its built-in saturation
rres = d.obj("r mpe-res", 560, 400)
bob = d.obj("bob~", 20, 440)
bos = d.msg("oversample 1", 120, 415)
d.c(d.obj("loadbang", 120, 390), 0, bos, 0)
d.c(bos, 0, bob, 0)
d.c(mixg, 0, bob, 0)
d.c(ch, 0, bob, 1)
d.c(rres, 0, bob, 2)
vcf2 = bob
ysum = d.obj("*~ 1.6", 20, 650)
d.c(bob, 0, ysum, 0)
vca = d.obj("*~", 20, 690)
d.c(ysum, 0, vca, 0)
d.c(env, 0, vca, 1)
d.c(vca, 0, d.obj("outlet~", 20, 730), 0)
if os.environ.get("DBG"):
    for nm_, src in (("dbg1", mixg), ("dbg2", env), ("dbg3", ch), ("dbg4", vcf2)):
        d.c(src, 0, d.obj(f"s~ {nm_}-$1", 900, 300), 0)

dsp = v.sub(d, 20, 660)
v.c(pitchA, 0, dsp, 0)
v.c(pglide, 0, dsp, 0)
v.c(ampon, 0, dsp, 1)
v.c(ampoff, 0, dsp, 1)
v.c(brmsg, 0, dsp, 1)
v.c(tb_reset, 0, dsp, 2)
v.c(tbmsg, 0, dsp, 2)
v.c(gate1, 0, dsp, 3)
v.c(swoff, 0, dsp, 3)
lb = v.obj("loadbang", 300, 600)
lb0 = v.msg("0", 300, 630)
v.c(lb, 0, lb0, 0)
v.c(lb0, 0, dsp, 3)
vout = v.obj("outlet~", 20, 700)
v.c(dsp, 0, vout, 0)

v.save(os.path.join(OUT, "voice.pd"))

# ---------------------------------------------------------------- main.pd
m = Canvas(w=1400, h=900)
m.comment("MPE Super - big detuned-saw MPE synth for the Organelle, breath sweeps the filter (made for the Lekholm DM48)", 20, 5)
m.comment("Aux button cycles PLAY / SHAPE / SETUP knob pages. Bottom line shows incoming MIDI.", 20, 22)


def sub(name, x, y, w=1000, h=700):
    return Canvas(name, w=w, h=h), (x, y)


# ---- midi-in: raw MIDI -> internal messages (test harness sends to the same names)
mi = Canvas("midi-in", w=900, h=400)
ni = mi.obj("notein", 20, 20)
np_ = mi.obj("pack 0 0 0", 20, 60)
mi.c(ni, 0, np_, 0); mi.c(ni, 1, np_, 1); mi.c(ni, 2, np_, 2)
mi.c(np_, 0, mi.obj("s mpe-in-note", 20, 90), 0)
keys = mi.obj("r notesRaw", 20, 140)
mi.comment("Organelle keys play on channel 0", 110, 140)
kap = mi.obj("list append 0", 20, 170)
mi.c(keys, 0, kap, 0)
mi.c(kap, 0, mi.obj("s mpe-in-note", 20, 200), 0)
bi = mi.obj("bendin", 200, 20)
bp = mi.obj("pack 0 0", 200, 60)
mi.c(bi, 0, bp, 0); mi.c(bi, 1, bp, 1)
mi.c(bp, 0, mi.obj("s mpe-in-bend", 200, 90), 0)
ti = mi.obj("touchin", 340, 20)
tp = mi.obj("pack 0 0", 340, 60)
mi.c(ti, 0, tp, 0); mi.c(ti, 1, tp, 1)
mi.c(tp, 0, mi.obj("s mpe-in-at", 340, 90), 0)
pti = mi.obj("polytouchin", 480, 20)
ptp = mi.obj("pack 0 0 0", 480, 60)
mi.c(pti, 0, ptp, 0); mi.c(pti, 1, ptp, 1); mi.c(pti, 2, ptp, 2)
mi.c(ptp, 0, mi.obj("s mpe-in-pat", 480, 90), 0)
ci = mi.obj("ctlin", 640, 20)
cp = mi.obj("pack 0 0 0", 640, 60)
mi.c(ci, 0, cp, 0); mi.c(ci, 1, cp, 1); mi.c(ci, 2, cp, 2)
mi.c(cp, 0, mi.obj("s mpe-in-cc", 640, 90), 0)
m.sub(mi, 20, 50)

# ---- voices: note allocation
vc = Canvas("voices", w=900, h=500)
rn = vc.obj("r mpe-in-note", 20, 20)
nu = vc.obj("unpack 0 0 0", 20, 50)
vc.c(rn, 0, nu, 0)
chm = vc.obj("* 128", 160, 80)
vc.c(nu, 2, chm, 0)
key = vc.obj("+", 20, 110)
vc.c(chm, 0, key, 1)
vc.c(nu, 0, key, 0)
poly = vc.obj(f"poly {NVOICES} 1", 20, 150)
vc.c(nu, 1, poly, 1)
vc.c(key, 0, poly, 0)
stopr = vc.obj("r mpe-allnotesoff", 160, 120)
vc.c(stopr, 0, poly, 0)
vp = vc.obj("pack 0 0 0", 20, 190)
vc.c(poly, 0, vp, 0); vc.c(poly, 1, vp, 1); vc.c(poly, 2, vp, 2)
cl = vc.obj(f"clone -s 1 voice {NVOICES}", 20, 230)
vc.c(vp, 0, cl, 0)
vc.c(cl, 0, vc.obj("s~ mpe-dry", 20, 270), 0)
vc.comment("key = channel * 128 + note, so the same note on two channels gets two voices", 200, 190)
m.sub(vc, 20, 80)

# ---- bend: semitones per channel -> table, then tell the voices which channel moved
bd = Canvas("bend", w=900, h=500)
bd.obj(f"array define {BEND_TABLE} 17", 400, 20)
bd.obj("array define mpejust 12", 600, 20)
rb = bd.obj("r mpe-in-bend", 20, 20)
bu = bd.obj("unpack 0 0", 20, 50)
bd.c(rb, 0, bu, 0)
bch = bd.obj("t f f f", 120, 80)
bd.c(bu, 1, bch, 0)
bx = bd.obj("expr ($f1 - 8192) / 8192 * if($f2 == 1, $f3, $f4)", 20, 120)
bd.c(bu, 0, bx, 0)
bd.c(bch, 0, bx, 1)
rgr = bd.obj("r mpe-globrange", 300, 90)
bd.c(rgr, 0, bx, 2)
rnr = bd.obj("r mpe-noterange", 440, 90)
bd.c(rnr, 0, bx, 3)
bt = bd.obj("t b f", 20, 160)
bd.c(bx, 0, bt, 0)
tw = bd.obj(f"tabwrite {BEND_TABLE}", 80, 200)
bd.c(bt, 1, tw, 0)
bd.c(bch, 1, tw, 1)
bf = bd.obj("f", 20, 200)
bd.c(bch, 2, bf, 1)
bd.c(bt, 0, bf, 0)
bd.c(bf, 0, bd.obj("s mpe-bend", 20, 240), 0)
# monitor
bm = bd.obj("pack 0 0", 250, 200)
bround = bd.obj("expr int($f1 * 100 + if($f1 > 0, 0.5, -0.5)) / 100", 250, 160)
bd.c(bt, 1, bround, 0)
bd.c(bround, 0, bm, 1)
bd.c(bt, 0, bm, 0)  # wrong order otherwise; fixed below
bd.conns.pop()
bmch = bd.obj("f", 250, 230)
bd.c(bch, 2, bmch, 1)
bd.c(bt, 0, bmch, 0)
bd.c(bmch, 0, bm, 0)
bmm = bd.msg("ch $1 bend $2", 250, 260)
bd.c(bm, 0, bmm, 0)
bd.c(bmm, 0, bd.obj("s mpe-mon", 250, 290), 0)
m.sub(bd, 20, 110)

# ---- breath / CC handling
br = Canvas("breath", w=1200, h=600)
br.comment("Breath = channel pressure, poly pressure, or CC 2 / 7 / 11", 20, 5)
rat = br.obj("r mpe-in-at", 20, 30)
atm = br.msg("$1 $2 -1", 20, 60)
br.c(rat, 0, atm, 0)
br.c(rat, 0, br.msg("ch $2 AT $1", 120, 60), 0)
rpat = br.obj("r mpe-in-pat", 260, 30)
patm = br.msg("$1 $3 $2", 260, 60)
br.c(rpat, 0, patm, 0)
br.c(rpat, 0, br.msg("ch $3 PolyAT $1", 360, 60), 0)
rcc = br.obj("r mpe-in-cc", 540, 30)
ccsw = br.msg("$2 $1 $3", 540, 60)
br.c(rcc, 0, ccsw, 0)
br.c(rcc, 0, br.msg("ch $3 CC$2 $1", 640, 60), 0)
ccr = br.obj("route 2 7 11 74 1 120 123", 540, 90)
br.c(ccsw, 0, ccr, 0)
ccbr = br.msg("$1 $2 -1", 540, 130)
for o in (0, 1, 2):
    br.c(ccr, o, ccbr, 0)
mon = br.obj("s mpe-mon", 120, 100)
br.c(atm + 1, 0, mon, 0)
br.c(patm + 1, 0, mon, 0)
br.c(ccsw + 1, 0, mon, 0)
# "v ch note" -> curve -> "ch note v"
bu3 = br.obj("unpack 0 0 0", 20, 180)
br.c(atm, 0, bu3, 0)
br.c(patm, 0, bu3, 0)
br.c(ccbr, 0, bu3, 0)
bcur = br.obj("expr pow($f1 / 127, $f2)", 20, 210)
br.c(bu3, 0, bcur, 0)
rc2 = br.obj("r mpe-curve", 200, 180)
br.c(rc2, 0, bcur, 1)
bpk = br.obj("pack 0 0 0", 20, 240)
br.c(bcur, 0, bpk, 0)
br.c(bu3, 1, bpk, 1)
br.c(bu3, 2, bpk, 2)
bre = br.msg("$2 $3 $1", 20, 270)
br.c(bpk, 0, bre, 0)
br.c(bre, 0, br.obj("s mpe-breath", 20, 300), 0)
# CC74 timbre: "v ch" -> "ch v/127"
tu = br.obj("unpack 0 0", 700, 130)
br.c(ccr, 3, tu, 0)
tdiv = br.obj("/ 127", 700, 160)
br.c(tu, 0, tdiv, 0)
tpk = br.obj("pack 0 0", 700, 190)
br.c(tdiv, 0, tpk, 0)
br.c(tu, 1, tpk, 1)
tsw = br.msg("$2 $1", 700, 220)
br.c(tpk, 0, tsw, 0)
br.c(tsw, 0, br.obj("s mpe-timbre", 700, 250), 0)
# CC1 vibrato depth (any channel), 0..0.6 semitones
vu = br.obj("unpack 0 0", 850, 130)
br.c(ccr, 4, vu, 0)
vdiv = br.obj("/ 211.67", 850, 160)
br.c(vu, 0, vdiv, 0)
br.c(vdiv, 0, br.obj("s mpe-vibdepth", 850, 190), 0)
# all notes off
anm = br.msg("stop", 1000, 130)
br.c(ccr, 5, anm, 0)
br.c(ccr, 6, anm, 0)
br.c(anm, 0, br.obj("s mpe-allnotesoff", 1000, 160), 0)
m.sub(br, 20, 140)

# ---- note monitor (bottom screen line): "ch 3 E5 vel 100"
nm = Canvas("note-monitor", w=900, h=500)
rnm = nm.obj("r mpe-in-note", 20, 20)
nmt = nm.obj("t a a", 20, 50)
nm.c(rnm, 0, nmt, 0)
# right branch first: note name + velocity into the cold inlets of [pack]
nmu = nm.obj("unpack 0 0 0", 200, 80)
nm.c(nmt, 1, nmu, 0)
ntt = nm.obj("t f f", 200, 110)
nm.c(nmu, 0, ntt, 0)
nmod = nm.obj("mod 12", 300, 140)
nm.c(ntt, 1, nmod, 0)
nget = nm.msg("get $1 1", 300, 165)
nls = nm.obj("list store C Db D Eb E F Gb G Ab A Bb B", 300, 190)
nset = nm.msg("set $1%d", 300, 215)
nm.chain(nmod, nget, nls, nset)
ndiv = nm.obj("/ 12", 200, 165)
nfl = nm.obj("i", 200, 190)
nsub = nm.obj("- 1", 200, 215)
nm.c(ntt, 0, ndiv, 0)
nm.chain(ndiv, nfl, nsub)
mkf = nm.obj("makefilename %s", 200, 250)
nm.c(nset, 0, mkf, 0)
nm.c(nsub, 0, mkf, 0)
npk = nm.obj("pack 0 s 0", 20, 290)
nm.c(mkf, 0, npk, 1)
nm.c(nmu, 1, npk, 2)
# left branch second: channel, only for note-ons
nm2 = nm.obj("unpack 0 0 0", 20, 110)
nm.c(nmt, 0, nm2, 0)
nchs = nm.obj("f", 20, 250)
nm.c(nm2, 2, nchs, 1)
nmos = nm.obj("moses 1", 80, 170)
nm.c(nm2, 1, nmos, 0)
nmb = nm.obj("t b", 120, 200)
nm.c(nmos, 1, nmb, 0)
nm.c(nmb, 0, nchs, 0)
nm.c(nchs, 0, npk, 0)
npm = nm.msg("ch $1 $2 vel $3", 20, 320)
nm.c(npk, 0, npm, 0)
nm.c(npm, 0, nm.obj("s mpe-mon", 20, 350), 0)
m.sub(nm, 20, 170)

def handler(c, x, y, entry, store_default, apply_objs, disp_msg, page, refresh=True):
    """entry receive -> [f] store -> apply chain + display. Returns the store [f]."""
    ent = c.obj(f"r {entry}", x, y)
    st = c.obj(f"f {store_default}", x, y + 30)
    c.c(ent, 0, st, 0)
    if refresh:
        c.c(c.obj(f"r $0-refresh{page}", x + 60, y), 0, st, 0)
    tt = c.obj("t f f", x, y + 60)
    c.c(st, 0, tt, 0)
    prev = None
    yy = y + 90
    for i, txt in enumerate(apply_objs):
        o = c.obj(txt, x + 90, yy)
        c.c(tt if prev is None else prev, 1 if prev is None else 0, o, 0)
        prev = o
        yy += 26
    dm_ = c.msg(disp_msg[1], x, y + 90 + 26 * max(len(apply_objs), 1) + 10)
    if disp_msg[0]:
        pre = None
        yy2 = y + 90
        for txt in disp_msg[0]:
            o = c.obj(txt, x, yy2)
            c.c(tt if pre is None else pre, 0, o, 0)
            pre = o
            yy2 += 26
        c.items[dm_] = ("msg", (x, yy2, disp_msg[1]))
        c.c(pre, 0, dm_, 0)
    else:
        c.c(tt, 0, dm_, 0)
    sd = c.obj(f"s $0-disp{page}", x, c.items[dm_][1][1] + 30)
    c.c(dm_, 0, sd, 0)
    return st


def allpass(c, x, y, src, name, ms, g=0.6):
    rd_ = c.obj(f"delread~ {name} {ms}", x + 120, y)
    gm = c.obj(f"*~ {g}", x + 120, y + 26)
    c.c(rd_, 0, gm, 0)
    w = c.obj("+~", x, y + 52)
    c.c(src, 0, w, 0)
    c.c(gm, 0, w, 1)
    c.c(w, 0, c.obj(f"delwrite~ {name} 50", x + 120, y + 78), 0)
    ng = c.obj(f"*~ {-g}", x, y + 104)
    c.c(w, 0, ng, 0)
    o = c.obj("+~", x, y + 130)
    c.c(ng, 0, o, 0)
    c.c(rd_, 0, o, 1)
    return o

# ---- screen: page gating + rate-limited monitor line
NPAGES = 4
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
ledsel = pr.obj("sel 0 1 2 3", 220, 160)
pr.c(pset, 1, ledsel, 0)
sled = pr.obj("s led", 220, 215)
for page, col in enumerate((0, 3, 5, 6)):
    lm = pr.msg(str(col), 220 + page * 35, 188)
    pr.c(ledsel, page, lm, 0)
    pr.c(lm, 0, sled, 0)
refsel = pr.obj("sel 0 1 2 3", 360, 160)
pr.c(pset, 0, refsel, 0)
smon = pr.obj("s mpe-mon", 360, 270)
titles = ("PLAY   (aux: shape)", "SHAPE  (aux: setup)", "SETUP  (aux: tune)", "TUNE   (aux: play)")
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
handler(pr, 20, Y, "$0-k1p0", 0.35, ["* 66", "+ 18", "pack 0 30", "s mpe-cut-c"],
        (["* 100", "i"], "1 Cutoff $1"), 0)
handler(pr, 220, Y, "$0-k2p0", 0.35, ["* 3.7", "s mpe-res"],
        (["* 100", "i"], "2 Resonance $1"), 0)
handler(pr, 420, Y, "$0-k3p0", 0.4, ["expr $f1 * $f1 * 0.025", "pack 0 30", "s mpe-detune-c"],
        (["* 100", "i"], "3 Detune $1"), 0)
handler(pr, 620, Y, "$0-k4p0", 0.3, ["s mpe-space"],
        (["* 100", "i"], "4 Space $1 %"), 0)

Y1 = 560
# SHAPE page
handler(pr, 20, Y1, "$0-bamt", 0.6, ["* 90", "pack 0 30", "s mpe-bamt-c"],
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


Y3 = 1060
# TUNE page: just intonation + key
JI = {
    0: [0] * 12,
    # 5-limit just: 1/1 16/15 9/8 6/5 5/4 4/3 45/32 3/2 8/5 5/3 9/5 15/8
    1: [0, 0.1173, 0.0391, 0.1564, -0.1369, -0.0196, -0.0978, 0.0196, 0.1369, -0.1564, 0.1760, -0.1173],
    # 7-limit: as above but 4th = 21/16 (pure 7th over the 5th), 7/6 minor 3rd, 7/4 flat 7th
    2: [0, 0.1173, 0.0391, -0.3313, -0.1369, -0.2918, -0.0978, 0.0196, 0.1369, -0.1564, -0.3117, -0.1173],
}
NAMES = {0: "Equal", 1: "Just", 2: "Just 7"}
ktm = [pr.obj("r $0-k1p3", 20, Y3 - 75), pr.obj("* 2.99", 20, Y3 - 50), pr.obj("i", 80, Y3 - 50),
       pr.obj("s $0-tuning", 20, Y3 - 25)]
pr.chain(*ktm)
te = pr.obj("r $0-tuning", 20, Y3)
tf_ = pr.obj("f 1", 20, Y3 + 25)
pr.c(te, 0, tf_, 0)
pr.c(pr.obj("r $0-refresh3", 80, Y3), 0, tf_, 0)
tt = pr.obj("t f f", 20, Y3 + 50)
pr.c(tf_, 0, tt, 0)
tsel_a = pr.obj("sel 0 1 2", 110, Y3 + 75)
tsel_d = pr.obj("sel 0 1 2", 20, Y3 + 75)
pr.c(tt, 1, tsel_a, 0)
pr.c(tt, 0, tsel_d, 0)
tdisp = pr.obj("s $0-disp3", 20, Y3 + 200)
for i in range(3):
    vals = " ".join(str(v_) for v_ in JI[i])
    am = pr.msg(f"; mpejust 0 {vals}", 110 + i * 10, Y3 + 100 + i * 25)
    pr.c(tsel_a, i, am, 0)
    dm_ = pr.msg(f"1 Tuning {NAMES[i]}", 20, Y3 + 100 + i * 25)
    pr.c(tsel_d, i, dm_, 0)
    pr.c(dm_, 0, tdisp, 0)
# key: knob picks Bb / C / D / A, stored as pitch class
kkm = [pr.obj("r $0-k2p3", 420, Y3 - 100), pr.obj("* 3.99", 420, Y3 - 75), pr.obj("i", 480, Y3 - 75),
       pr.msg("get $1 1", 510, Y3 - 75), pr.obj("list store 10 0 2 9", 420, Y3 - 50),
       pr.obj("s $0-key", 420, Y3 - 25)]
pr.chain(*kkm)
ke = pr.obj("r $0-key", 420, Y3)
kf = pr.obj(f"f {KEY}", 420, Y3 + 25)
pr.c(ke, 0, kf, 0)
pr.c(pr.obj("r $0-refresh3", 480, Y3), 0, kf, 0)
kt = pr.obj("t f f", 420, Y3 + 50)
pr.c(kf, 0, kt, 0)
pr.c(kt, 1, pr.obj("s mpe-key", 510, Y3 + 75), 0)
ksel = pr.obj("sel 10 0 2 9", 420, Y3 + 75)
pr.c(kt, 0, ksel, 0)
for i, nm_ in enumerate(("Bb", "C", "D", "A")):
    km = pr.msg(f"2 Key {nm_}", 420 + i * 60, Y3 + 100)
    pr.c(ksel, i, km, 0)
    pr.c(km, 0, tdisp, 0)
hint = pr.msg("3 Match the harp key", 700, Y3 + 75)
hint2 = pr.msg("4 Aux: next page", 700, Y3 + 100)
r3 = pr.obj("r $0-refresh3", 700, Y3 + 50)
pr.c(r3, 0, hint, 0)
pr.c(r3, 0, hint2, 0)
pr.c(hint, 0, tdisp, 0)
pr.c(hint2, 0, tdisp, 0)

# settings save / load
SAVED = ("bamt", "sub", "release", "curve", "octave", "noterange", "globrange", "vibrate", "tuning", "key")
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
pr.c(initb, 0, pr.obj("s $0-refresh3", sx + 560, sy + 245), 0)
pr.c(initb, 1, pr.obj("s $0-refresh1", sx + 620, sy + 220), 0)
for i, (nm_, val) in enumerate((("$0-k1p0", 0.35), ("$0-k2p0", 0.35), ("$0-k3p0", 0.4), ("$0-k4p0", 0.3),
                                 ("mpe-vibdepth", 0))):
    msg_ = pr.msg(str(val), sx + 500 + i * 60, sy + 160)
    pr.c(initb, 6 - i, msg_, 0)
    pr.c(msg_, 0, pr.obj(f"s {nm_}", sx + 500 + i * 60, sy + 185), 0)
showp = pr.msg("0", sx + 800, sy + 60)
pr.c(lbt, 0, showp, 0)
pr.c(showp, 0, pset, 0)
m.sub(pr, 20, 230)

# ---- audio: smoothed params, vibrato, voices -> chorus + reverb -> out
au = Canvas("audio", w=1400, h=900)
for i, nm_ in enumerate(("cut", "detune", "bamt", "sub")):
    r = au.obj(f"r mpe-{nm_}-c", 20 + i * 130, 20)
    l = au.obj("line~", 20 + i * 130, 45)
    au.c(r, 0, l, 0)
    au.c(l, 0, au.obj(f"s~ mpe-{nm_}", 20 + i * 130, 70), 0)
# saw anti-aliasing constant: sr / 2.5
lbs = au.obj("loadbang", 600, 20)
srt = au.obj("samplerate~", 600, 45)
srd = au.obj("/ 2.5", 600, 70)
srs = au.obj("sig~", 600, 95)
au.chain(lbs, srt, srd, srs)
au.c(srs, 0, au.obj("s~ mpe-sawk", 600, 120), 0)
# vibrato (depth from CC1, rate from SETUP page)
rvr = au.obj("r mpe-vibrate", 800, 20)
lfo = au.obj("osc~ 5.5", 800, 45)
au.c(rvr, 0, lfo, 0)
rvd = au.obj("r mpe-vibdepth", 900, 20)
vdm = au.msg("$1 50", 900, 45)
vdl = au.obj("line~", 900, 70)
au.chain(rvd, vdm, vdl)
vm = au.obj("*~", 800, 100)
au.c(lfo, 0, vm, 0)
au.c(vdl, 0, vm, 1)
au.c(vm, 0, au.obj("s~ mpe-vib", 800, 125), 0)

dry = au.obj("r~ mpe-dry", 20, 170)
mg = au.obj("*~ 0.55", 20, 195)
au.c(dry, 0, mg, 0)
au.c(mg, 0, au.obj(f"delwrite~ $0-ch 60", 20, 225), 0)

# Space: chorus amount and reverb amount
rsp = au.obj("r mpe-space", 400, 170)
spt = au.obj("t f f", 400, 195)
au.c(rsp, 0, spt, 0)
chg = au.obj("expr min($f1 * 2, 1) * 0.8", 470, 220)
wetg = au.obj("* 0.6", 400, 220)
au.c(spt, 1, chg, 0)
au.c(spt, 0, wetg, 0)
chm = au.msg("$1 50", 470, 245)
wetm = au.msg("$1 50", 400, 245)
au.c(chg, 0, chm, 0)
au.c(wetg, 0, wetm, 0)
chl = au.obj("line~", 470, 270)
wetl = au.obj("line~", 400, 270)
au.c(chm, 0, chl, 0)
au.c(wetm, 0, wetl, 0)

# stereo chorus: two modulated taps per side
taps = []
for i, (rate, base, depth) in enumerate(((0.31, 11, 4), (0.43, 17, 5), (0.37, 13, 4.5), (0.29, 19, 5.5))):
    x = 20 + i * 150
    o = au.obj(f"osc~ {rate}", x, 320)
    if i % 2:
        ph = au.msg("0.5", x + 70, 295)  # second tap per side starts half a cycle later
    m1 = au.obj(f"*~ {depth}", x, 345)
    a1 = au.obj(f"+~ {base}", x, 370)
    dr = au.obj(f"delread4~ $0-ch", x, 395)
    au.chain(o, m1, a1, dr)
    if i % 2:
        au.c(ph, 0, o, 1)
        au.c(lbs, 0, ph, 0)
    taps.append(dr)
chL = au.obj("+~", 20, 430)
au.c(taps[0], 0, chL, 0)
au.c(taps[1], 0, chL, 1)
chR = au.obj("+~", 320, 430)
au.c(taps[2], 0, chR, 0)
au.c(taps[3], 0, chR, 1)

combs = [(29.7, 0.82), (37.1, 0.81), (41.1, 0.80), (43.7, 0.79)]
cout = []
for i, (ms, fb) in enumerate(combs):
    x = 20 + i * 170
    y = 520
    rd_ = au.obj(f"delread~ $0-c{i} {ms}", x, y)
    lp = au.obj("lop~ 4000", x, y + 26)
    g = au.obj(f"*~ {fb}", x, y + 52)
    sm = au.obj("+~", x, y + 78)
    wr = au.obj(f"delwrite~ $0-c{i} 100", x, y + 104)
    au.chain(rd_, lp, g)
    au.c(g, 0, sm, 1)
    au.c(mg, 0, sm, 0)
    au.c(sm, 0, wr, 0)
    cout.append(rd_)
A = au.obj("+~", 20, 660)
au.c(cout[0], 0, A, 0)
au.c(cout[2], 0, A, 1)
B = au.obj("+~", 190, 660)
au.c(cout[1], 0, B, 0)
au.c(cout[3], 0, B, 1)
Lr = au.obj("+~", 20, 690)
au.c(A, 0, Lr, 0)
au.c(B, 0, Lr, 1)
Rr = au.obj("-~", 190, 690)
au.c(A, 0, Rr, 0)
au.c(B, 0, Rr, 1)
apL = allpass(au, 20, 720, Lr, "$0-apL", 5.3)
apR = allpass(au, 400, 720, Rr, "$0-apR", 6.7)

for side, ap, chs, x in (("L", apL, chL, 800), ("R", apR, chR, 1050)):
    cm_ = au.obj("*~", x, 430)
    au.c(chs, 0, cm_, 0)
    au.c(chl, 0, cm_, 1)
    wm = au.obj("*~", x + 80, 430)
    au.c(ap, 0, wm, 0)
    au.c(wetl, 0, wm, 1)
    s1 = au.obj("+~", x, 460)
    au.c(mg, 0, s1, 0)
    au.c(cm_, 0, s1, 1)
    s2 = au.obj("+~", x, 485)
    au.c(s1, 0, s2, 0)
    au.c(wm, 0, s2, 1)
    # soft limiter: y = clip(x, -1.5, 1.5); out = y - 0.148 * y^3 (tops out at 1.0)
    cl_ = au.obj("clip~ -1.5 1.5", x, 510)
    au.c(s2, 0, cl_, 0)
    q2 = au.obj("*~", x + 80, 535)
    au.c(cl_, 0, q2, 0)
    au.c(cl_, 0, q2, 1)
    q3 = au.obj("*~", x + 80, 560)
    au.c(q2, 0, q3, 0)
    au.c(cl_, 0, q3, 1)
    q4 = au.obj("*~ -0.148148", x + 80, 585)
    au.c(q3, 0, q4, 0)
    lim = au.obj("+~", x, 610)
    au.c(cl_, 0, lim, 0)
    au.c(q4, 0, lim, 1)
    au.c(lim, 0, au.obj(f"throw~ out{side}", x, 640), 0)
m.sub(au, 20, 260)

m.comment("Open the subpatches to see how it works. SHAPE and SETUP values are saved with System > Save Patch.",
          20, 300)
m.save(os.path.join(OUT, "main.pd"))

with open(os.path.join(OUT, "settings.txt"), "w") as f:
    f.write(f"0.6 0.3 0.25 1 0 48 2 5.5 1 {KEY};\n")
print("wrote", OUT)

"""Generate 'DM48X Tunings': a Pd Organelle patch that sends .mid files to the DM48X."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdgen import Canvas  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "DM48X Tunings"
os.makedirs(OUT, exist_ok=True)
MAXBYTES = 65536
MAXEV = 4096


def B(x):
    return f"dmxb[{x}]"


def VLQ(x):
    """Value of the MIDI variable-length number starting at byte x (up to 4 bytes)."""
    x = f"({x})"
    b0, b1, b2, b3 = B(x), B(f"{x}+1"), B(f"{x}+2"), B(f"{x}+3")
    return (f"if({b0} < 128, {b0}, if({b1} < 128, ({b0} & 127) * 128 + {b1}, "
            f"if({b2} < 128, (({b0} & 127) * 128 + ({b1} & 127)) * 128 + {b2}, "
            f"((({b0} & 127) * 128 + ({b1} & 127)) * 128 + ({b2} & 127)) * 128 + {b3})))")


def VLEN(x):
    """Number of bytes in the variable-length number starting at byte x."""
    x = f"({x})"
    return f"if({B(x)} < 128, 1, if({B(x + '+1')} < 128, 2, if({B(x + '+2')} < 128, 3, 4)))"


def BE32(x):
    return f"{B(f'{x}')} * 16777216 + {B(f'{x}+1')} * 65536 + {B(f'{x}+2')} * 256 + {B(f'{x}+3')}"


m = Canvas(w=1100, h=500)
m.comment("DM48X Tunings - send .mid tuning files to the Lekholm DM48X", 20, 5)
m.comment("1) Put .mid files in this patch folder. 2) On the DM48X: Tuning editor > Receive tuning.", 20, 22)
m.comment("3) Knob 1 picks a file, Aux sends it. Then save the tuning on the DM48X.", 20, 39)
y = 70
for nm, size in (("dmxb", MAXBYTES), ("dmxt", MAXEV), ("dmxs", MAXEV), ("dmx1", MAXEV), ("dmx2", MAXEV)):
    m.obj(f"array define {nm} {size}", 600, y)
    y += 25
m.obj("text define dmxfiles", 600, y)
y = 70
for nm in ("dmxp", "dmxe", "dmxr", "dmxk", "dmxn", "dmxc", "dmxd", "dmxst", "dmxi", "dmxsel", "dmxcount"):
    m.obj(f"value {nm}", 850, y)
    y += 25

# ---------------------------------------------------------------- file list
fl = Canvas("file-list", w=800, h=500)
lb = fl.obj("loadbang", 20, 20)
lbt = fl.obj("t b b b", 20, 45)
fl.c(lb, 0, lbt, 0)
clr = fl.msg("clear", 200, 70)
fl.c(lbt, 2, clr, 0)
fl.c(clr, 0, fl.obj("text define dmxfiles-unused", 200, 95), 0)  # replaced below
fl.items[-1] = ("obj", (200, 95, "s dmxfiles-clear"))
dirm = fl.msg("dir", 20, 70)
fl.c(lbt, 1, dirm, 0)
pdc = fl.obj("pdcontrol", 20, 95)
fl.c(dirm, 0, pdc, 0)
dts = fl.obj("t s s", 20, 120)
fl.c(pdc, 0, dts, 0)
g1 = fl.msg("symbol $1/*.mid", 20, 145)
g2 = fl.msg("symbol $1/*.MID", 160, 145)
fl.c(dts, 1, g1, 0)
fl.c(dts, 0, g2, 0)
glob = fl.obj("file glob", 20, 175)
fl.c(g1, 0, glob, 0)
fl.c(g2, 0, glob, 0)
gfirst = fl.obj("list split 1", 20, 200)
fl.c(glob, 0, gfirst, 0)
ins = fl.obj("text insert dmxfiles 1e+06", 20, 225)
fl.c(gfirst, 0, ins, 0)
# count + first screen
sz = fl.obj("text size dmxfiles", 20, 280)
fl.c(lbt, 0, sz, 0)
fl.c(lbt, 2, fl.obj("s dmx-init", 120, 280), 0)
szt = fl.obj("t b f", 20, 305)
fl.c(sz, 0, szt, 0)
fl.c(szt, 1, fl.obj("v dmxcount", 80, 330), 0)
fl.c(szt, 0, fl.obj("s dmx-redraw", 20, 355), 0)
# keep the Organelle's own MIDI out (keys, knobs) away from the DM48X while this patch runs
gd = fl.obj("delay 3000", 400, 70)
fl.c(lb, 0, gd, 0)
g0 = fl.msg("0", 400, 95)
fl.c(gd, 0, g0, 0)
fl.c(g0, 0, fl.obj("s midiOutGate", 400, 120), 0)
m.sub(fl, 20, 70)
# the [text define] lives in main; clearing goes through a receive
cr = m.obj("r dmxfiles-clear", 600, 380)
m.c(cr, 0, [i for i, it in enumerate(m.items) if it[0] == "obj" and it[1][2] == "text define dmxfiles"][0], 0)

# ---------------------------------------------------------------- screen
ui = Canvas("screen", w=1100, h=700)
rk = ui.obj("r knob1", 20, 20)
selx = ui.obj("expr if(dmxcount > 0, min(int($f1 * dmxcount), dmxcount - 1), 0)", 20, 45)
ui.c(rk, 0, selx, 0)
chg = ui.obj("change -1", 20, 70)
ui.c(selx, 0, chg, 0)
ui.c(chg, 0, ui.obj("v dmxsel", 20, 95), 0)
ui.c(chg, 0, ui.obj("s dmx-redraw", 120, 95), 0)

rr = ui.obj("r dmx-redraw", 300, 20)
rt = ui.obj("t b b b b b", 300, 45)
ui.c(rr, 0, rt, 0)
hv = ui.obj("v dmxcount", 300, 80)
ui.c(rt, 4, hv, 0)
hm = ui.msg("DM48X Tunings ($1)", 300, 105)
ui.c(hv, 0, hm, 0)
ui.c(hm, 0, ui.obj("s screenLine1", 300, 130), 0)
for row in range(3):
    x = 20 + row * 330
    y = 200
    ix = ui.obj(f"expr min(max(dmxsel - 1, 0), max(dmxcount - 3, 0)) + {row}", x, y)
    ui.c(rt, 3 - row, ix, 0)
    it = ui.obj("t f f f", x, y + 25)
    ui.c(ix, 0, it, 0)
    # validity
    vx = ui.obj("expr $f1 < dmxcount", x + 200, y + 50)
    ui.c(it, 2, vx, 0)
    sp = ui.obj("spigot", x, y + 100)
    ui.c(vx, 0, sp, 1)
    vsel = ui.obj("sel 0", x + 200, y + 75)
    ui.c(vx, 0, vsel, 0)
    blank = ui.msg("-", x + 200, y + 100)
    ui.c(vsel, 0, blank, 0)
    # marker
    mx = ui.obj("expr $f1 == dmxsel", x + 100, y + 50)
    ui.c(it, 1, mx, 0)
    msel = ui.obj("sel 1 0", x + 100, y + 75)
    ui.c(mx, 0, msel, 0)
    m1 = ui.msg("symbol >", x + 100, y + 100)
    m0 = ui.msg("symbol .", x + 160, y + 100)
    ui.c(msel, 0, m1, 0)
    ui.c(msel, 1, m0, 0)
    pk = ui.obj("pack s s", x, y + 250)
    ui.c(m1, 0, pk, 1)
    ui.c(m0, 0, pk, 1)
    # name
    ui.c(it, 0, sp, 0)
    tg = ui.obj("text get dmxfiles", x, y + 125)
    ui.c(sp, 0, tg, 0)
    se = ui.obj("file splitext", x, y + 150)
    ui.c(tg, 0, se, 0)
    s1 = ui.obj("list split 1", x, y + 175)
    ui.c(se, 0, s1, 0)
    sn = ui.obj("file splitname", x, y + 200)
    ui.c(s1, 0, sn, 0)
    s2 = ui.obj("list split 1", x, y + 225)
    ui.c(sn, 0, s2, 0)
    ui.c(s2, 1, pk, 0)
    ui.c(sn, 1, pk, 0)  # no directory part: whole thing is the name
    lm = ui.msg("$2 $1", x, y + 275)
    ui.c(pk, 0, lm, 0)
    so = ui.obj(f"s screenLine{row + 2}", x, y + 300)
    ui.c(lm, 0, so, 0)
    ui.c(blank, 0, so, 0)
# status line
rs = ui.obj("r dmx-status", 800, 20)
sl = ui.obj("list", 800, 80)
ui.c(rs, 0, sl, 1)
ui.c(rt, 0, sl, 0)
ui.c(rs, 0, ui.obj("s screenLine5", 900, 110), 0)
ui.c(sl, 0, ui.obj("s screenLine5", 800, 110), 0)
lbs = ui.obj("r dmx-init", 1000, 20)
st0 = ui.msg("Aux: send to DM48X", 1000, 45)
ui.c(lbs, 0, st0, 0)
ui.c(st0, 0, sl, 1)
m.sub(ui, 20, 100)

# ---------------------------------------------------------------- send: read file, parse, play
sd = Canvas("send", w=1400, h=1000)
raux = sd.obj("r aux", 20, 20)
asel = sd.obj("sel 1", 20, 45)
sd.c(raux, 0, asel, 0)
haveany = sd.obj("expr dmxcount > 0", 20, 70)
sd.c(asel, 0, haveany, 0)
hsel = sd.obj("sel 1 0", 20, 95)
sd.c(haveany, 0, hsel, 0)
nof = sd.msg("No .mid files found", 120, 120)
sd.c(hsel, 1, nof, 0)
sstat = sd.obj("s dmx-status", 120, 950)
sd.c(nof, 0, sstat, 0)

go = sd.obj("t b b b", 20, 140)
sd.c(hsel, 0, go, 0)
# 3: stop anything playing, MIDI out gate off, LED on, status
stopm = sd.msg("stop", 300, 170)
sd.c(go, 2, stopm, 0)
gate0 = sd.msg("0", 360, 170)
sd.c(go, 2, gate0, 0)
sd.c(gate0, 0, sd.obj("s midiOutGate", 360, 195), 0)
led3 = sd.msg("3", 400, 170)
sd.c(go, 2, led3, 0)
sled = sd.obj("s led", 400, 195)
sd.c(led3, 0, sled, 0)
sending = sd.msg("Sending...", 440, 170)
sd.c(go, 2, sending, 0)
sd.c(sending, 0, sstat, 0)
# 2: read the file into dmxb
selv = sd.obj("v dmxsel", 20, 200)
sd.c(go, 1, selv, 0)
tget = sd.obj("text get dmxfiles", 20, 225)
sd.c(selv, 0, tget, 0)
om = sd.msg(f"open $1, {MAXBYTES}, close", 20, 250)
sd.c(tget, 0, om, 0)
fh = sd.obj("file handle", 20, 275)
sd.c(om, 0, fh, 0)
bt = sd.obj("t a a", 20, 300)
sd.c(fh, 0, bt, 0)
ln = sd.obj("list length", 120, 325)
sd.c(bt, 1, ln, 0)
sd.c(ln, 0, sd.obj("v dmxn", 120, 350), 0)
sd.c(bt, 0, sd.obj("array set dmxb", 20, 325), 0)
zn = sd.msg("0", 250, 250)  # file missing -> length 0 -> "not a MIDI file"
sd.c(go, 2, zn, 0)
zc = sd.msg("0", 300, 250)
sd.c(go, 2, zc, 0)
sd.c(zc, 0, sd.obj("v dmxc", 300, 275), 0)
sd.c(zn, 0, sd.obj("v dmxn", 250, 275), 0)
# 1: parse
hdr = sd.obj("expr (dmxn > 22) && (dmxb[0] == 77) && (dmxb[1] == 84) && (dmxb[2] == 104) && (dmxb[3] == 100)", 20, 400)
sd.c(go, 0, hdr, 0)
hs = sd.obj("sel 1 0", 20, 425)
sd.c(hdr, 0, hs, 0)
bad = sd.msg("Not a MIDI file", 200, 450)
sd.c(hs, 1, bad, 0)
sd.c(bad, 0, sstat, 0)
ledoff = sd.msg("0", 330, 450)
sd.c(hs, 1, ledoff, 0)
sd.c(ledoff, 0, sled, 0)
pinit = sd.obj("t b b b b", 20, 475)
sd.c(hs, 0, pinit, 0)
divx = sd.obj("expr if((dmxb[12] < 128) && (dmxb[12] * 256 + dmxb[13] > 0), dmxb[12] * 256 + dmxb[13], 480)", 600, 500)
sd.c(pinit, 3, divx, 0)
sd.c(divx, 0, sd.obj("v dmxd", 600, 525), 0)
px = sd.obj(f"expr 8 + {BE32(4)}", 400, 525)
sd.c(pinit, 2, px, 0)
ptt = sd.obj("t f f", 400, 550)
sd.c(px, 0, ptt, 0)
sd.c(ptt, 1, sd.obj("v dmxe", 460, 575), 0)
sd.c(ptt, 0, sd.obj("v dmxp", 400, 575), 0)
z3 = sd.msg("0", 300, 525)
sd.c(pinit, 2, z3, 0)
for i, nm in enumerate(("dmxc", "dmxk", "dmxr")):
    sd.c(z3, 0, sd.obj(f"v {nm}", 250 + i * 60, 550), 0)
# run the parser
runm = sd.msg("200000", 20, 525)
sd.c(pinit, 1, runm, 0)
until = sd.obj("until", 20, 550)
sd.c(runm, 0, until, 0)
step = Canvas("parse-step", w=1500, h=900)
st_in = step.obj("inlet", 20, 20)
st_out = step.obj("outlet", 20, 860)  # bang = stop
case = step.obj("expr if((dmxp >= dmxe) || (dmxc >= %d), if((dmxp + 8 > dmxn) || (dmxc >= %d), 0, 1), 2)" % (MAXEV, MAXEV), 20, 45)
step.c(st_in, 0, case, 0)
cs = step.obj("sel 0 1 2", 20, 70)
step.c(case, 0, cs, 0)
step.c(cs, 0, st_out, 0)
# case 1: chunk header
c1 = step.obj("t b b b", 200, 100)
step.c(cs, 1, c1, 0)
ex = step.obj(f"expr dmxp + 8 + {BE32('dmxp+4')}", 400, 130)
step.c(c1, 2, ex, 0)
step.c(ex, 0, step.obj("v dmxe", 400, 155), 0)
npx = step.obj("expr if((dmxb[dmxp] == 77) && (dmxb[dmxp+1] == 84) && (dmxb[dmxp+2] == 114) && (dmxb[dmxp+3] == 107), dmxp + 8, dmxe)", 300, 185)
step.c(c1, 1, npx, 0)
step.c(npx, 0, step.obj("v dmxp", 300, 210), 0)
zz = step.msg("0", 200, 185)
step.c(c1, 0, zz, 0)
step.c(zz, 0, step.obj("v dmxk", 200, 210), 0)
step.c(zz, 0, step.obj("v dmxr", 250, 235), 0)
# case 2: one event
c2 = step.obj("t b b b b b b b", 20, 300)
step.c(cs, 2, c2, 0)
e1 = step.obj(f"expr dmxk + {VLQ('dmxp')}", 700, 330)
step.c(c2, 6, e1, 0)
step.c(e1, 0, step.obj("v dmxk", 700, 355), 0)
e2 = step.obj(f"expr dmxp + {VLEN('dmxp')}", 600, 380)
step.c(c2, 5, e2, 0)
step.c(e2, 0, step.obj("v dmxp", 600, 405), 0)
e3 = step.obj("expr if(dmxb[dmxp] >= 128, dmxb[dmxp], dmxr)", 500, 430)
step.c(c2, 4, e3, 0)
step.c(e3, 0, step.obj("v dmxst", 500, 455), 0)
e4 = step.obj("expr if(dmxst < 240, dmxst, dmxr)", 400, 480)
step.c(c2, 3, e4, 0)
step.c(e4, 0, step.obj("v dmxr", 400, 505), 0)
e4b = step.obj("expr dmxp + (dmxb[dmxp] >= 128)", 300, 530)
step.c(c2, 2, e4b, 0)
step.c(e4b, 0, step.obj("v dmxp", 300, 555), 0)
# store note on / note off
isn = step.obj("expr ((dmxst & 240) == 144) || ((dmxst & 240) == 128)", 200, 580)
step.c(c2, 1, isn, 0)
isnsel = step.obj("sel 1", 200, 605)
step.c(isn, 0, isnsel, 0)
wr = step.obj("t b b b b b", 200, 630)
step.c(isnsel, 0, wr, 0)
cv = step.obj("v dmxc", 800, 655)
step.c(wr, 4, cv, 0)
cvt = step.obj("t f f f f", 800, 680)
step.c(cv, 0, cvt, 0)
tws = []
for i, (arr, src) in enumerate((("dmxt", "dmxk"), ("dmxs", "dmxst"), ("dmx1", "dmxb[dmxp]"), ("dmx2", "dmxb[dmxp+1]"))):
    x = 300 + i * 120
    vx = step.obj(f"expr {src}", x, 705)
    step.c(wr, 3 if i < 2 else (2 if i == 2 else 1), vx, 0)
    tw = step.obj(f"tabwrite {arr}", x, 730)
    step.c(vx, 0, tw, 0)
    step.c(cvt, i, tw, 1)
cinc = step.obj("expr dmxc + 1", 200, 760)
step.c(wr, 0, cinc, 0)
step.c(cinc, 0, step.obj("v dmxc", 200, 785), 0)
# advance past the event's data
adv = step.obj(
    "expr if(dmxst < 128, dmxe, if(dmxst == 255, if(dmxb[dmxp] == 47, dmxe, dmxp + 1 + "
    + VLEN("dmxp+1") + " + " + VLQ("dmxp+1") + "), if((dmxst == 240) || (dmxst == 247), dmxp + "
    + VLEN("dmxp") + " + " + VLQ("dmxp") + ", dmxp + if(((dmxst & 240) == 192) || ((dmxst & 240) == 208), 1, 2))))",
    20, 810)
step.c(c2, 0, adv, 0)
step.c(adv, 0, step.obj("v dmxp", 20, 835), 0)
pstep = sd.sub(step, 20, 575)
sd.c(until, 0, pstep, 0)
sd.c(pstep, 0, until, 1)
# 0: done parsing -> play
got = sd.obj("v dmxc", 20, 650)
sd.c(pinit, 0, got, 0)
gs = sd.obj("moses 1", 20, 675)
sd.c(got, 0, gs, 0)
non = sd.msg("No notes in file", 200, 700)
sd.c(gs, 0, non, 0)
sd.c(non, 0, sstat, 0)
sd.c(non, 0, ledoff, 0)
pstart = sd.obj("t b b", 20, 700)
sd.c(gs, 1, pstart, 0)
pz = sd.msg("0", 80, 725)
sd.c(pstart, 1, pz, 0)
sd.c(pz, 0, sd.obj("v dmxi", 80, 750), 0)
# but only if the header was valid (dmxn reset happens before; header failure leaves dmxc = 0? make sure)
play = Canvas("play-step", w=1000, h=600)
p_in = play.obj("inlet", 20, 20)
p_done = play.obj("outlet", 300, 560)
more = play.obj("expr dmxi < dmxc", 20, 45)
play.c(p_in, 0, more, 0)
msl = play.obj("sel 1 0", 20, 70)
play.c(more, 0, msl, 0)
play.c(msl, 1, p_done, 0)
pt = play.obj("t b b b b", 20, 100)
play.c(msl, 0, pt, 0)
ev = play.obj("expr dmx1[dmxi]; if((dmxs[dmxi] & 240) == 128, 0, dmx2[dmxi]); (dmxs[dmxi] & 15) + 1", 400, 130)
play.c(pt, 3, ev, 0)
evp = play.obj("pack 0 0 0", 400, 160)
play.c(ev, 0, evp, 0)
play.c(ev, 1, evp, 1)
play.c(ev, 2, evp, 2)
play.c(evp, 0, play.obj("noteout", 400, 190), 0)
play.c(evp, 0, play.obj("s dmx-sent", 500, 190), 0)
wx = play.obj("expr if(dmxi + 1 < dmxc, max(5, min(30, (dmxt[dmxi+1] - dmxt[dmxi]) * 500 / dmxd)), 0)", 200, 230)
play.c(pt, 2, wx, 0)
dl = play.obj("delay", 20, 300)
play.c(wx, 0, dl, 1)
ix = play.obj("expr dmxi + 1", 100, 260)
play.c(pt, 1, ix, 0)
play.c(ix, 0, play.obj("v dmxi", 100, 285), 0)
play.c(pt, 0, dl, 0)
play.c(dl, 0, more, 0)
pin2 = play.obj("inlet", 200, 20)  # "stop"
play.c(pin2, 0, dl, 0)
pl = sd.sub(play, 20, 775)
sd.c(pstart, 0, pl, 0)
sd.c(stopm, 0, pl, 1)
doneb = sd.obj("t b b", 20, 820)
sd.c(pl, 0, doneb, 0)
cnt = sd.obj("v dmxc", 120, 845)
sd.c(doneb, 1, cnt, 0)
sm = sd.msg("Sent! $1 events", 120, 870)
sd.c(cnt, 0, sm, 0)
sd.c(sm, 0, sstat, 0)
sd.c(doneb, 0, ledoff, 0)
# restore the Organelle's MIDI out after sending? no: keep it off while this patch runs.
m.sub(sd, 20, 130)

m.save(os.path.join(OUT, "main.pd"))
print("wrote", OUT)

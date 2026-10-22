
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
mg = au.obj("*~ 0.4", 20, 195)
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
    cl_ = au.obj("clip~ -0.99 0.99", x, 510)
    au.c(s2, 0, cl_, 0)
    au.c(cl_, 0, au.obj(f"throw~ out{side}", x, 540), 0)
m.sub(au, 20, 260)

m.comment("Open the subpatches to see how it works. SHAPE and SETUP values are saved with System > Save Patch.",
          20, 300)
m.save(os.path.join(OUT, "main.pd"))

with open(os.path.join(OUT, "settings.txt"), "w") as f:
    f.write("0.6 0.3 0.25 1 0 48 2 5.5;\n")
print("wrote", OUT)

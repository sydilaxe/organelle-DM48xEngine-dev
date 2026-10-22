import sys, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run, audio, f0, centroid
P="../DM48 Engine"; sr=44100
names=["halo","lyra","steel","under","velvet","volt"]
for name in sys.argv[1:]:
    i=names.index(name)
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,f"knob1 {(i+0.5)/6}"),(300,"notesRaw 60 100"),(350,"notesRaw 60 0")]
    t=600; segs=[]
    for note in (45,57,69,81):
        for br in (30,80,127):
            ev+= [(t,f"eng-in 0 2 {note} 100"),(t+1,f"eng-in 4 2 11 {br}")]
            segs.append((note,br,t+500,t+1400)); ev.append((t+1500,f"eng-in 0 2 {note} 0")); t+=2200
    log=run(P, ev)
    errs=[l for l in log.splitlines() if "error" in l.lower() or "load" in l.lower()]
    print(name, errs[:4])
    x=audio(P).mean(1)
    print(" peak", np.abs(x).max().round(3), "nan", np.isnan(x).any())
    for note,br,a,b in segs:
        s=x[int(a/1000*sr):int(b/1000*sr)]
        exp=440*2**((note-69)/12)
        ff=f0(s,lo=exp*0.7,hi=exp*1.4)
        print(f"  note {note} br {br:3d}: f0 {ff:7.1f} ({1200*np.log2(ff/exp):+5.1f}c) rms {np.sqrt((s**2).mean()):.3f} centroid {centroid(s):6.0f}")

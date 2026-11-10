import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0, centroid, eng_knob
P="../DM48 Engine"; sr=44100
names=["halo","lyra","steel","under","velvet","volt"]
for bowk in (0.0, 0.4, 1.0):
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,f"knob1 {eng_knob('steel')}"),(300,"notesRaw 60 100"),(350,"notesRaw 60 0"),
        (500,"knob4 0.0"),(510,f"knob4 {bowk}"),(520,f"knob4 {bowk+0.0001}")]
    t=800; segs=[]
    for note in (45,57,69,81):
        ev+=[(t,f"eng-in 0 2 {note} 100"),(t+1,f"eng-in 4 2 11 120")]
        segs.append((note,t+2500,t+3800)); ev.append((t+4000,f"eng-in 0 2 {note} 0")); t+=4500
    log=run(P,ev); x=audio(P).mean(1)
    out=[]
    for note,a,b in segs:
        s=x[int(a/1000*sr):int(b/1000*sr)]; exp=440*2**((note-69)/12); ff=f0(s,lo=exp*0.7,hi=exp*1.4)
        out.append(f"{note}:{np.sqrt((s**2).mean()):.3f}/{1200*np.log2(ff/exp):+.0f}c")
    print(f"Bow {bowk}: late-sustain rms/pitch", " ".join(out), "peak", np.abs(x).max().round(2), [l for l in log.splitlines() if 'error' in l][:2])

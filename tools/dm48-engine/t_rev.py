import sys, warnings, numpy as np, time
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"; sr=44100
# FX page (E=64), reverb mix knob4 high; short note then listen to tail
for size in [float(a) for a in sys.argv[1:]] or (0.2, 0.5, 0.9):
    ev=[(100,"notesRaw 64 100"),(150,"notesRaw 64 0"),(300,"knob4 0.9"),(310,"eng-rsize %s"%size),
        (500,"eng-in 0 2 60 100"),(501,"eng-in 4 2 11 110"),(800,"eng-in 4 2 11 0"),(801,"eng-in 0 2 60 0")]
    ev.append((9000,"knob1 0.2"))
    t=time.time(); log=run(P, ev); dt=time.time()-t
    print([l for l in log.splitlines() if "error" in l.lower()][:3])
    x=audio(P); m=x.mean(1)
    env=[np.sqrt((m[int(t*sr):int((t+0.1)*sr)]**2).mean()) for t in np.arange(1.0,9.0,0.5)]
    db=20*np.log10(np.array(env)+1e-9)
    slope=np.polyfit(np.arange(len(db))*0.5, db, 1)[0]
    print(np.round(db[::2],1))
    print(f"size {size}: peak {np.abs(x).max():.2f}  T60~{-60/slope if slope<0 else 99:.1f}s  L/R corr {np.corrcoef(x[sr:3*sr,0],x[sr:3*sr,1])[0,1]:.2f}  run {dt:.1f}s")

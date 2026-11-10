import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"; sr=44100
from harness import ENGINE_NAMES as names
res={}
for name in names:
    i=names.index(name)
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,"knob1 0.99"),(300,f"knob1 {(i+0.5)/len(names)}"),(900,"notesRaw 60 100"),(950,"notesRaw 60 0"),
        (1000,"notesRaw 64 100"),(1050,"notesRaw 64 0"),(1100,"knob3 0.5"),(1110,"knob3 0.0"),(1120,"knob4 0.5"),(1130,"knob4 0.0")]  # FX: dry only
    t=1500; segs=[]
    for br in (60,100,127):
        for ch,n in ((2,57),(3,61),(4,64)):
            ev+=[(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}")]
        segs.append((br,t+700,t+1700))
        for ch,n in ((2,57),(3,61),(4,64)): ev.append((t+1800,f"eng-in 0 {ch} {n} 0"))
        t+=3500
    run(P,ev); x=audio(P).mean(1)
    res[name]=[20*np.log10(np.sqrt((x[int(a/1000*sr):int(b/1000*sr)]**2).mean())+1e-9) for br,a,b in segs]
    print(f"{name:7s}", " ".join(f"{v:6.1f}" for v in res[name]))

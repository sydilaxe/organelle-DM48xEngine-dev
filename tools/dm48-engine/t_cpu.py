import sys, time, os, subprocess, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
P="../DM48 Engine"
res={}
NM=["feral","halo","lyra","steel","under","velvet","volt"]
for i,name in enumerate(NM):
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,f"knob1 {(i+0.5)/7}")]
    for v in range(8):
        ev.append((400, f"eng-live 0 {v+2} {48+v*4} 100")); ev.append((401, f"eng-live 4 {v+2} 11 110"))
    ev.append((20400,"eng-live 4 2 11 111"))
    t=time.time(); run(P, ev); dt=time.time()-t
    res[name]=dt
base_ev=[(100,"knob1 0.1"),(20400,"knob1 0.2")]
t=time.time(); run(P, base_ev); idle=time.time()-t
print(f"idle (FX only, no notes): {idle/20.7*100:.1f}% of one core here")
for k,v in res.items(): print(f"{k:7s} 8 voices: {v/20.7*100:.1f}% of one core here")

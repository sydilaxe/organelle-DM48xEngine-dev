import sys, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"
ev=[(300,"notesRaw 78 100"),(350,"notesRaw 78 0")]          # arp on
# hold C4 (ch2) E4 (ch3) G4 (ch4) with breath rising 30 -> 127 over 4 s
for ch,n in ((2,60),(3,64),(4,67)): ev.append((500, f"eng-in 0 {ch} {n} 90"))
for k in range(200): ev.append((500+k*20, f"eng-in 4 2 11 {int(30+97*k/199)}"))
for ch,n in ((2,60),(3,64),(4,67)): ev.append((4600, f"eng-in 0 {ch} {n} 0"))
log = run(P, ev, extra_prints=["eng-live"])
ons=[(l) for l in log.splitlines() if l.startswith("eng-live: 0") and not l.endswith(" 0")]
print(len(ons),"arp note-ons; first 8:", [o.split()[3] for o in ons[:8]])
# timing: count note-ons in first and last second
import re
x=audio(P).mean(1); sr=44100
print("rms 1-2s", np.sqrt((x[sr:2*sr]**2).mean()).round(3), " rms 3.5-4.5s", np.sqrt((x[int(3.5*sr):int(4.5*sr)]**2).mean()).round(3))
for l in log.splitlines():
    if "error" in l.lower() or "Arp" in l: print(l)

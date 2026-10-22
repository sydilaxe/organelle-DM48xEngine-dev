import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
P="../DM48 Engine"
ev=[(300,"notesRaw 78 100"),(350,"notesRaw 78 0")]
for ch,n in ((2,60),(3,64),(4,67)): ev.append((500, f"eng-in 0 {ch} {n} 90"))
for z,(t0,v) in enumerate(((500,20),(2500,55),(4500,85),(6500,120))):
    ev.append((t0+1, f"eng-in 4 2 11 {v}"))
for ch,n in ((2,60),(3,64),(4,67)): ev.append((8500, f"eng-in 0 {ch} {n} 0"))
log = run(P, ev, extra_prints=["eng-live"])
ons=[l.split() for l in log.splitlines() if l.startswith("eng-live: 0") and not l.endswith(" 0")]
import collections
def tm(i): return i
print(len(ons), "notes (expect ~ 8 s x 8 per s = 64 at 120 BPM 16ths)")
seq=[int(o[3]) for o in ons]
for z,(a,b) in enumerate(((0,15),(16,31),(32,47),(48,63))):
    print(f"zone {z}:", seq[a:b])
print([l for l in log.splitlines() if "error" in l.lower()])

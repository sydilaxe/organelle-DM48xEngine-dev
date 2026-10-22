import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
P="../DM48 Engine"
ev=[(300,"notesRaw 78 100"),(350,"notesRaw 78 0")]
for ch,n in ((2,60),(3,64),(4,67)): ev.append((500, f"eng-in 0 {ch} {n} 90"))
for t0,v in ((500,15),(4500,60),(8500,100),(12500,127)): ev.append((t0+1, f"eng-in 4 2 11 {v}"))
for ch,n in ((2,60),(3,64),(4,67)): ev.append((16500, f"eng-in 0 {ch} {n} 0"))
log = run(P, ev, extra_prints=["eng-live"])
ons=[l.split() for l in log.splitlines() if l.startswith("eng-live: 0") and not l.endswith(" 0")]
print("errors:", [l for l in log.splitlines() if "error" in l.lower()])
# count per 4 s window using order: we don't have timestamps -> rerun simpler: just show sequence chunks by breath change markers
seq=[(int(o[2]),int(o[3])) for o in ons]
print(len(seq),"notes total. channels used:", sorted(set(c for c,n in seq)))
print("notes:", [n for c,n in seq])

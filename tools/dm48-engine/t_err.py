import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
P="../DM48 Engine"
for name, ev in (("arp on/off only", [(300,"notesRaw 78 100"),(350,"notesRaw 78 0")]),
                 ("notes, no arp", [(500,"eng-in 0 2 60 90"),(900,"eng-in 0 2 60 0")]),
                 ("arp + notes", [(300,"notesRaw 78 100"),(350,"notesRaw 78 0"),(500,"eng-in 0 2 60 90"),(900,"eng-in 0 2 60 0")]),
                 ("arp + notes + off", [(300,"notesRaw 78 100"),(350,"notesRaw 78 0"),(500,"eng-in 0 2 60 90"),(900,"eng-in 0 2 60 0"),(1200,"notesRaw 78 100"),(1250,"notesRaw 78 0")])):
    log = run(P, ev, extra_prints=["eng-live"])
    errs=[l for l in log.splitlines() if "error" in l.lower()]
    print(f"{name:20s}", len(errs), errs[:2], [l for l in log.splitlines() if l.startswith("eng-live")][:6])

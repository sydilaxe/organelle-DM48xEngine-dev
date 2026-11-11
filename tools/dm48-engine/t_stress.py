"""Usage: python3 t_stress.py ["../../patches/DM48 Engine" [engine ...]]  (from tools/dm48-engine; ~1 min per engine)
   Worst case per engine: a MIDI loop playing a 4-note chord, 4 more live notes (8 voices), breath moving on all,
an audio loop recorded, then overdubbed with the loop pitch-shifted. CPU over 12..32 s, clicks, clipping."""
import sys, os, resource, numpy as np, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.argv_=sys.argv; sys.argv=["x","none"]
from harness import run, audio, eng_knob, ENGINE_NAMES
from t_clicks import clicks
P=sys.argv_[1] if len(sys.argv_) > 1 else "../DM48 Engine"; names=sys.argv_[2:] or ENGINE_NAMES; SR=44100
def key(ev,t,n,h=60): ev += [(t,f"notesRaw {n} 100"),(t+h,f"notesRaw {n} 0")]
def events(name, end):
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,f"knob1 {eng_knob(name)}"),(300,"notesRaw 60 100"),(350,"notesRaw 60 0")]
    ev += [(2000,"aux 1"),(2050,"aux 0")]                                     # MIDI loop: record
    for v,n in enumerate((45,52,57,64)): ev += [(2100+v,f"eng-in 0 {2+v} {n} 100"),(5800+v,f"eng-in 0 {2+v} {n} 0")]
    for t in range(2150,5800,90):
        for v in range(4): ev.append((t+v, f"eng-in 4 {2+v} 11 {60+int(40*np.sin(t/400+v))}"))
    ev += [(6000,"aux 1"),(6050,"aux 0")]                                     # MIDI loop: play
    for v,n in enumerate((69,72,76,81)): ev.append((6500+v,f"eng-in 0 {6+v} {n} 100"))   # 4 live notes on top
    for t in range(6550,end-200,90):
        for v in range(4): ev.append((t+v, f"eng-in 4 {6+v} 11 {55+int(45*np.sin(t/300+v*1.3))}"))
    key(ev,7000,81); key(ev,11000,81)                                         # audio loop: record 4 s, play
    key(ev,12000,81)                                                          # overdub
    ev += [(13000,"notesRaw 81 100"),(13030,"knob2 0.5"),(13050,"knob2 0.4"),(13100,"notesRaw 81 0")]   # pitched down
    if end > 21000: key(ev,20000,81)                                          # back to play
    ev.append((end,"knob3 0.3"))
    return ev
def cpu(ev):
    r0=resource.getrusage(resource.RUSAGE_CHILDREN); lg=run(P,ev); r1=resource.getrusage(resource.RUSAGE_CHILDREN)
    return r1.ru_utime+r1.ru_stime-r0.ru_utime-r0.ru_stime, lg
print(f"{'engine':8s} {'CPU 12-32 s':>11s}  peak  clipped  clicks (dub 12.5-19.5 s / play 20.5-31 s)  errors")
base=None
for name in ["idle"]+list(names):
    nm = "halo" if name=="idle" else name
    if name=="idle":
        evs=lambda end: [(100,"knob1 0.1"),(end,"knob3 0.3")]
    else:
        evs=lambda end, nm=nm: events(nm,end)
    a,_=cpu(evs(12000)); b,lg=cpu(evs(32000))
    pct=(b-a)/20*100
    if name=="idle": print(f"{'idle FX':8s} {pct:10.2f}%"); continue
    x=audio(P); m=x.mean(1)
    pk=np.abs(x).max(); clip=int((np.abs(x)>0.99).sum())
    bad=[l for l in lg.splitlines() if "error" in l.lower()][:2]
    print(f"{name:8s} {pct:10.2f}%  {pk:.2f}  {clip:7d}  {clicks(m,12.5,19.5)} / {clicks(m,20.5,31)}  {bad}", flush=True)

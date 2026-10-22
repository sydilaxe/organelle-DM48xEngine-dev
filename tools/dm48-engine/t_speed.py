import sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"
ev=[]
def note(t, ch, n, dur, br=100):
    ev.append((t, f"eng-in 0 {ch} {n} 90")); ev.append((t+1, f"eng-in 4 {ch} 11 {br}")); ev.append((t+dur, f"eng-live 0 {ch} {n} 0"))
def tap(t): ev.append((t,"aux 1")); ev.append((t+50,"aux 0"))
tap(500); note(600,2,60,500); note(1600,3,67,500); tap(2500)
ev.append((6500,"notesRaw 71 100")); ev.append((6550,"knob1 0.40")); ev.append((6600,"notesRaw 71 0"))
ev.append((11000,"notesRaw 71 100")); ev.append((11050,"knob1 0.78")); ev.append((11100,"notesRaw 71 0"))
ev.append((15000,"knob1 0.3"))
log = run(P, ev, extra_prints=["eng-loop-speed"])
for l in log.splitlines():
    if any(k in l for k in ("speed","error","screenLine5")): print(l)
x = audio(P).mean(1); sr=44100
seq=[]
for t in range(2500, 16000, 100):
    s=x[int(t/1000*sr):int((t+100)/1000*sr)]
    r=np.sqrt((s**2).mean()); seq.append(round(f0(s)) if r>0.01 else 0)
lab=lambda fr: "-" if fr==0 else ("C" if 120<fr<140 or 250<fr<275 else ("G" if 185<fr<205 or 380<fr<405 else "?"))
s="".join(lab(f) for f in seq)
print("2.5-6.5s normal :", s[:40]); print("6.5-11s reverse:", s[40:85]); print("11-16s fwd fast:", s[85:])

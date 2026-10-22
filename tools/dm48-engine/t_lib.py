import sys, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"
ev=[]
def note(t, ch, n, dur, br=100):
    ev.append((t, f"eng-in 0 {ch} {n} 90")); ev.append((t+1, f"eng-in 4 {ch} 11 {br}")); ev.append((t+dur, f"eng-in 0 {ch} {n} 0"))
def tap(t): ev.append((t,"aux 1")); ev.append((t+50,"aux 0"))
tap(500); note(600,2,60,1700); tap(2500)                     # loop with a long C4
ev.append((3000,"notesRaw 61 100")); ev.append((3050,"notesRaw 61 0"))   # LIBRARY page
ev.append((3200,"knob1 0.05")); ev.append((3400,"aux 1")); ev.append((3450,"aux 0"))   # send first tuning
ev.append((3500,"fs 1")); ev.append((3550,"fs 0"))          # footswitch still drives the looper (-> overdub)
log = run(P, ev, extra_prints=["eng-loopstat"])
sent=[l for l in log.splitlines() if l.startswith("dmx-sent")]
print(len(sent), "tuning MIDI events sent;", [l for l in log.splitlines() if "Sent" in l or "loopstat" in l or "error" in l.lower()])
x=audio(P).mean(1); sr=44100
for a,b in ((2600,3300),(3500,4200),(4600,5300)):
    s=x[int(a/1000*sr):int(b/1000*sr)]; print(f"{a}-{b} ms rms {np.sqrt((s**2).mean()):.3f} f0 {f0(s):.0f}")

"""Stopping the audio looper in different situations must leave silence (no held note)."""
import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"; SR=44100
def key(ev,t,n,hold=60): ev += [(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")]
def note(ev,t,ch,n,dur,br=100): ev += [(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")]
def fx_off(ev):
    key(ev,200,64); ev += [(300,"knob3 0.5"),(310,"knob3 0"),(320,"knob4 0.5"),(330,"knob4 0")]; key(ev,400,60)
def rms(x,a,b): s=x[int(a*SR):int(b*SR)]; return float(np.sqrt((s**2).mean()))
cases = {
  "stop while playing":            lambda ev: key(ev, 5000, 83),
  "stop while overdubbing":        lambda ev: (key(ev, 4500, 81), note(ev, 4550, 3, 64, 300), key(ev, 5000, 83)),
  "stop while the dub finishes":   lambda ev: (key(ev, 4500, 81), note(ev, 4550, 3, 64, 300), key(ev, 4900, 81), key(ev, 5000, 83)),
  "stop after speed 2x":           lambda ev: (ev.extend([(4500,"notesRaw 81 100"),(4530,"knob1 0.5"),(4540,"knob1 0.78"),(4580,"notesRaw 81 0")]), key(ev, 5000, 83)),
  "stop after pitch +7":           lambda ev: (ev.extend([(4500,"notesRaw 81 100"),(4530,"knob2 0.5"),(4540,"knob2 0.8"),(4580,"notesRaw 81 0")]), key(ev, 5000, 83)),
  "stop with a live note held":    lambda ev: (note(ev, 4800, 4, 67, 400), key(ev, 5000, 83)),
  "stop, start, stop":             lambda ev: (key(ev, 5000, 83), key(ev, 5600, 83), key(ev, 6200, 83)),
  "stop while recording":          None,
}
for name, fn in cases.items():
    ev=[]; fx_off(ev)
    if fn is None:
        key(ev,1500,81); note(ev,1520,2,57,1500); key(ev, 2500, 83); key(ev, 3600, 81); key(ev, 5000, 83)
    else:
        key(ev,1500,81); note(ev,1520,2,57,1500); key(ev,3600,81)
        fn(ev)
    stop_t = max(t for t,e in ev if e.startswith("notesRaw 83")) / 1000
    ev.append((int(stop_t*1000)+4000, "knob3 0.5"))
    log = run(P, ev); x = audio(P).mean(1)
    after = rms(x, stop_t + 1.5, stop_t + 3.5)
    print(f"{'OK  ' if after < 0.002 else 'HELD'} {name:30s} level 1.5-3.5 s after the stop: {after:.4f}")

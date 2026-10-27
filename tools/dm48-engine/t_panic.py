"""Panic (low D#) silences everything - freeze, loops, arp, delay - and things work again afterwards."""
import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"; SR=44100
def key(ev,t,n,hold=60): ev += [(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")]
def note(ev,t,ch,n,dur,br=100): ev += [(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")]
def rms(x,a,b): s=x[int(a*SR):int(b*SR)]; return float(np.sqrt((s**2).mean()))
ev=[]
ev += [(500,"aux 1"),(550,"aux 0")]; note(ev,600,2,60,500); ev += [(2000,"aux 1"),(2050,"aux 0")]   # MIDI loop
key(ev,2200,81); note(ev,2300,3,64,800); key(ev,3400,81)                                         # audio loop
key(ev,3600,78); ev += [(3700,"eng-in 0 4 67 100"),(3701,"eng-in 4 4 11 110")]                   # arp on, a held note
key(ev,4000,72)                                                                                  # freeze on
key(ev,5000,63)                                                                                  # PANIC
ev += [(7000,"aux 1"),(7050,"aux 0")]                                                            # MIDI loop starts again (stop -> play)
ev += [(9000,"knob3 0.5")]
log=run(P,ev,extra_prints=["eng-panic"])
x=audio(P).mean(1)
print("errors:", [l for l in log.splitlines() if "error" in l.lower()][:3])
print(f"before panic {rms(x,4.5,4.9):.3f} | 0.5-1.9 s after panic {rms(x,5.6,6.9):.4f} | MIDI loop restarted {rms(x,7.2,8.8):.3f}")

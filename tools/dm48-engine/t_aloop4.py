import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"; sr=44100
ev=[]
def key(t,n,hold=60): ev.extend([(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")])
def note(t,ch,n,dur,br=100): ev.extend([(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")])
def speed(t,v): ev.extend([(t,"notesRaw 81 100"),(t+30,"knob1 0.5"),(t+40,f"knob1 {v}"),(t+80,"notesRaw 81 0")])
key(200,64); ev.extend([(300,"knob3 0.5"),(310,"knob3 0"),(320,"knob4 0.5"),(330,"knob4 0")]); key(400,60)
key(500,81); note(600,2,60,600); key(2500,81)          # C at 1x
speed(3000,0.43)                                        # reverse 1x
key(3300,81); note(3400,3,64,400); key(4000,81)        # overdub E in reverse
speed(4300,0.5)                                         # forward again while that layer's pass is unfinished -> cut, dirty
key(5000,82)                                            # undo it
key(5500,81); note(5600,4,67,400); key(6100,81)        # new overdub reuses (and first clears) that layer
ev.append((10000,"knob2 0.5"))
log=run(P,ev,extra_prints=["eng-aloop-speed"])
L=log.splitlines()
print("errors:", [l for l in L if "error" in l.lower()][:4])
print([l.split(": ",1)[1] for l in L if l.startswith("screenLine5") and "Audio" in l])
x=audio(P).mean(1)
def lab(fr):
    if fr==0: return "-"
    for nm,f in (("C",261.6),("E",329.6),("G",392)):
        if abs(1200*np.log2(fr/f))<70: return nm
    return "?"
for a_,b_,title in ((3.1,4.3,"reverse, dubbing E"),(4.4,4.95,"forward (E layer cut)"),(5.1,5.5,"after undo"),(6.2,9.9,"C + new G layer")):
    seq=[]
    for t in np.arange(a_,b_,0.1):
        s=x[int(t*sr):int((t+0.1)*sr)]; r=np.sqrt((s**2).mean())
        seq.append(lab(f0(s,lo=200,hi=600)) if r>0.005 else "-")
    print(f"{title:24s}", "".join(seq))

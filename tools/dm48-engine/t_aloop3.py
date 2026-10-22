import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"; sr=44100
ev=[]
def key(t,n,hold=60): ev.extend([(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")])
def note(t,ch,n,dur,br=100): ev.extend([(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")])
def speed(t,v): ev.extend([(t,"notesRaw 81 100"),(t+30,"knob1 0.5"),(t+40,f"knob1 {v}"),(t+80,"notesRaw 81 0")])
# turn reverb + delay off for clean pitch reading (FX page knobs 3 and 4)
key(200,64); ev.extend([(300,"knob3 0.5"),(310,"knob3 0"),(320,"knob4 0.5"),(330,"knob4 0")]); key(400,60)
key(500,81); note(600,2,60,600); key(2500,81)          # base: C at 1x, 2 s loop (C during 0.1-0.7 s)
speed(3000,0.78)                                        # 2x
key(3500,81); note(3700,3,67,300); key(4600,81)        # overdub G at 2x (the dub keeps writing for a full pass)
speed(6000,0.5)                                         # back to 1x
ev.append((12000,"knob2 0.5"))
log=run(P,ev,extra_prints=["eng-aloop-speed"])
L=log.splitlines()
print("errors:", [l for l in L if "error" in l.lower()][:4])
print([l.split(": ",1)[1] for l in L if l.startswith("eng-aloop-speed")])
x=audio(P).mean(1)
def lab(fr):
    if fr==0: return "-"
    for nm,f in (("C",261.6),("G",392),("g",196),("c",130.8)):
        if abs(1200*np.log2(fr/f))<70: return nm
    return "?"
for a_,b_,title in ((3.1,5.9,"at 2x (C up an octave = c5?)"),(6.2,11.9,"at 1x: C normal, G an octave down")):
    seq=[]
    for t in np.arange(a_,b_,0.1):
        s=x[int(t*sr):int((t+0.1)*sr)]; r=np.sqrt((s**2).mean())
        fr=f0(s,lo=150,hi=900) if r>0.005 else 0
        seq.append(lab(fr) if fr==0 or fr<600 else ("C2" if abs(1200*np.log2(fr/523.3))<70 else "?"))
    print(f"{title:36s}", "".join(q if len(q)==1 else "^" for q in seq))

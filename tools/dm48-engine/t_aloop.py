import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"; sr=44100
names=["feral","halo","lyra","steel","under","velvet","volt"]
ev=[]
def key(t,n,hold=60): ev.extend([(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")])
def note(t,ch,n,dur,br=100): ev.extend([(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")])
key(500,81)                      # REC
note(700,2,60,800)               # C4 (velvet)
key(2500,81)                     # -> PLAY, loop = 2 s
# morph to halo, then overdub G4 on top
key(3000,69); ev.append((3100,"knob1 0.99")); ev.append((3200,f"knob1 {1.5/7}"))
key(5000,60)                     # back to the PLAY page
key(6500,81)                     # DUB
note(6700,3,67,700)
key(8500,81)                     # -> PLAY (the layer finishes its pass)
key(12500,82)                    # UNDO: the G layer goes
# hold high A + knob 2 = pitch +12
ev.extend([(15000,"notesRaw 81 100"),(15050,"knob2 0.99"),(15100,"knob2 1.0"),(15150,"notesRaw 81 0")])
# hold high A + knob 1 = reverse x1  (pitch back to 0 first)
ev.extend([(19000,"notesRaw 81 100"),(19050,"knob2 0.5"),(19060,"knob2 0.49"),(19100,"knob1 0.0"),(19110,"knob1 0.36"),(19150,"notesRaw 81 0")])
key(23000,83)                    # stop
ev.append((25000,"knob3 0.3"))
log=run(P,ev,extra_prints=["eng-aloop-speed","eng-aloop-pitch"])
print("errors:", [l for l in log.splitlines() if "error" in l.lower()][:5])
print([l.split(": ",1)[1] for l in log.splitlines() if l.startswith("screenLine5") and "Audio" in l or "aloop" in l][:20])
x=audio(P).mean(1)
def lab(fr):
    if fr==0: return "-"
    for nm,f in (("C",261.6),("G",392),("c",523.3),("g",784)):
        if abs(1200*np.log2(fr/f))<60: return nm
    return "?"
for a_,b_,title in ((2.6,6.4,"loop C (velvet), engine now halo"),(8.6,12.4,"C + overdubbed G"),(12.6,14.9,"after undo"),
                    (15.3,18.9,"pitch +12"),(19.3,22.9,"reverse"),(23.3,24.9,"stopped")):
    seq=[]
    for t in np.arange(a_,b_,0.1):
        s=x[int(t*sr):int((t+0.1)*sr)]; r=np.sqrt((s**2).mean())
        seq.append(lab(f0(s,lo=200,hi=900)) if r>0.01 else "-")
    print(f"{title:34s}", "".join(seq))

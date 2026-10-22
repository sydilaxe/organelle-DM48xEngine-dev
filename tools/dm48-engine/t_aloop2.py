import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0
P="../DM48 Engine"; sr=44100
ev=[]
def key(t,n,hold=60): ev.extend([(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")])
def note(t,ch,n,dur,br=100): ev.extend([(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")])
def tap(t): ev.extend([(t,"aux 1"),(t+50,"aux 0")])
# Post mode
ev.extend([(300,"notesRaw 83 100"),(350,"knob1 0.9"),(400,"notesRaw 83 0")])
# MIDI loop 1.6 s with a C
tap(1000); note(1100,2,60,400); tap(2600)
# audio: armed now, records the next MIDI cycle (G played live on top)
key(3000,81)
note(4300,3,67,500)
# after the audio take: clear the MIDI loop (hold aux), the audio loop keeps going
ev.extend([(8000,"aux 1"),(8800,"aux 0")])
# views: scope, loop, back to pages via a page key
key(9000,80); key(9600,80); key(10200,64)
# hold high A 1.2 s = clear
key(11000,81,1200)
ev.append((13000,"knob3 0.3"))
log=run(P,ev,extra_prints=["oscOut"])
L=log.splitlines()
print("errors:", [l for l in L if "error" in l.lower()][:5])
print([l.split(": ",1)[1] for l in L if l.startswith("screenLine5") and ("Audio" in l or "Scope" in l or "Loop wave" in l)])
wf=[i for i,l in enumerate(L) if "gWaveform" in l]
print("gWaveform messages:", len(wf), "| sample:", L[wf[0]][:80] if wf else None)
inv=[l for l in L if "gInvertArea 3" in l and " 9 1 44" in l]
print("playhead marks:", len(inv))
x=audio(P)
def lab(fr):
    if fr==0: return "-"
    for nm,f in (("C",261.6),("G",392)):
        if abs(1200*np.log2(fr/f))<60: return nm
    return "?"
for a_,b_,title in ((3.0,4.6,"armed (MIDI loop only)"),(4.6,8.0,"audio take running"),(8.9,10.9,"MIDI loop cleared, audio loops"),(12.3,13.0,"after clear")):
    seq=[]
    for t in np.arange(a_,b_,0.1):
        s=x[int(t*sr):int((t+0.1)*sr)].mean(1); r=np.sqrt((s**2).mean())
        seq.append(lab(f0(s,lo=200,hi=900)) if r>0.01 else "-")
    print(f"{title:32s}", "".join(seq))
s=x[int(9*sr):int(10.8*sr)]
print("stereo corr in post-mode loop:", round(np.corrcoef(s[:,0],s[:,1])[0,1],2))

import sys, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run, audio
from oledemu import render
import sec_ui
P="../DM48 Engine"
fam=2; within=4   # Gamelan, 5th scale
name=sec_ui.FAMILIES[fam][1][within]; idx=sec_ui.FAM_START[fam]+within
cents=sec_ui.SCALE_TABLE[idx*12+4]*100
ev=[(100,"notesRaw 69 100"),(130,"notesRaw 69 0"),(150,"knob1 0.1"),(200,"notesRaw 67 100"),(240,"notesRaw 67 0"),(400,f"knob1 {(fam+0.5)/10}"),(500,f"knob2 {(within+0.5)/sec_ui.FAM_COUNT[fam]}"),
    (600,"snap symbol tune_family"),(700,"eng-in 0 2 64 100"),(701,"eng-in 4 2 11 100"),(2200,"eng-in 0 2 64 0")]
log=run(P, ev, extra_prints=["oscOut","SNAP"])
print([l for l in log.splitlines() if "error" in l.lower()][:3])
render(log.replace("snap: ", "SNAP: "), "../shots")
x=audio(P).mean(1); sr=44100; seg=x[int(1.0*sr):int(2.1*sr)]
N=1<<20; S=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),N)); f=np.fft.rfftfreq(N,1/sr)
et=329.63; m=(f>et*0.95)&(f<et*1.05); k=np.argmax(S*m)
a,b,c=np.log(S[k-1:k+2]); p=0.5*(a-c)/(a-2*b+c); fr=(k+p)*sr/N
print(f"{name}: E4 measured {1200*np.log2(fr/et):+.1f} cents, table {cents:+.1f}")

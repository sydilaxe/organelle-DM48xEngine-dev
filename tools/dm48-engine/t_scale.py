import sys, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"
ev=[(200,"notesRaw 67 100"),(240,"notesRaw 67 0"),(400,f"knob1 {(6+0.5)/78}"),(500,"knob3 0"),
    (700,"eng-in 0 2 64 100"),(701,"eng-in 4 2 11 100"),(2200,"eng-in 0 2 64 0")]
log=run(P, ev, extra_prints=["oscOut"])
print([l for l in log.splitlines() if "error" in l.lower()][:3])
print([l for l in log.splitlines() if "gPrintln 3 2 " in l][:4])
x=audio(P).mean(1); sr=44100
seg=x[int(1.0*sr):int(2.1*sr)]
N=1<<20; S=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),N)); f=np.fft.rfftfreq(N,1/sr)
et=329.63; m=(f>et*0.95)&(f<et*1.05); k=np.argmax(S*m)
a,b,c=np.log(S[k-1:k+2]); p=0.5*(a-c)/(a-2*b+c); fr=(k+p)*sr/N
print(f"E4 in 'Pelog Degung Sejati': {fr:.2f} Hz = {1200*np.log2(fr/et):+.1f} cents (table says +24)")

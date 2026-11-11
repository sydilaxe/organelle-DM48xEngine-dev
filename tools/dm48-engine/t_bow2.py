import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, f0, eng_knob
P="../DM48 Engine"; sr=44100
note=int(sys.argv[1]) if len(sys.argv)>1 else 57
for bowk in (0.0, 1.0):
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,f"knob1 {eng_knob('steel')}"),(300,"notesRaw 60 100"),(350,"notesRaw 60 0"),
        (500,"knob4 0.0"),(510,f"knob4 {bowk}"),(600,"notesRaw 62 100"),(650,"notesRaw 62 0"),(800,"knob2 1.0"),(810,"knob2 0.0"),
        (900,"notesRaw 60 100"),(950,"notesRaw 60 0"),
        (1000,f"eng-in 0 2 {note} 100"),(1001,"eng-in 4 2 11 120"),(13000,f"eng-in 0 2 {note} 0")]
    log=run(P,ev); x=audio(P).mean(1)
    rm=[np.sqrt((x[int(t*sr):int((t+0.5)*sr)]**2).mean()) for t in (1.5,3,5,8,12)]
    s=x[8*sr:12*sr]; exp=440*2**((note-69)/12)
    print(f"Bow {bowk}: rms over time", np.round(rm,3), f"pitch {1200*np.log2(f0(s,lo=exp*.7,hi=exp*1.4)/exp):+.0f}c", [l for l in log.splitlines() if 'error' in l][:2])

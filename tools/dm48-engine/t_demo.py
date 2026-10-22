import sys, math, warnings, struct, shutil
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
P="../demoE"
ev=[(50,"notesRaw 69 100"),(80,"notesRaw 69 0"),(100,"eng-rmix 0.5")]
t=200
chords={"halo":[(2,62),(3,69),(4,74)],"under":[(2,45),(3,52)],"velvet":[(2,57),(3,64),(4,69),(5,72)],"volt":[(2,50),(3,57)]}
for i,name in enumerate(["velvet","halo","under","volt"]):
    idx=["halo","under","velvet","volt"].index(name)
    ev.append((t, f"knob1 {(idx+0.5)/4}"))
    for ch,n in chords[name]:
        ev.append((t+150, f"eng-in 0 {ch} {n} 70"))
    for k in range(170):
        x=k/169; br=int(8+119*(math.sin(math.pi*x)**1.3))
        for ch,n in chords[name]: ev.append((t+150+k*20, f"eng-in 4 {ch} 11 {br}"))
    if name=="halo":
        for k in range(40): ev.append((t+1500+k*20, f"eng-in 1 3 {int(8192+math.sin(math.pi*k/39)*2/48*8192)} 0"))
    for ch,n in chords[name]: ev.append((t+3600, f"eng-in 0 {ch} {n} 0"))
    t+=4300
# arp section on velvet
ev.append((t, "knob1 0.6")); ev.append((t+50,"notesRaw 78 100")); ev.append((t+80,"notesRaw 78 0"))
for ch,n in ((2,60),(3,64),(4,67),(5,71)): ev.append((t+200, f"eng-in 0 {ch} {n} 90"))
for k in range(300):
    x=k/299; br=int(15+112*x)
    ev.append((t+200+k*20, f"eng-in 4 2 11 {br}"))
for ch,n in ((2,60),(3,64),(4,67),(5,71)): ev.append((t+6400, f"eng-in 0 {ch} {n} 0"))
ev.append((t+8500,"knob2 0.5"))
log=run(P, ev, wav="demo.wav")
print([l for l in log.splitlines() if "error" in l.lower()][:5])
b=bytearray(open(P+"/demo.wav","rb").read()); i=b.index(b"data"); n=len(b)-(i+8)
b[i+4:i+8]=struct.pack("<I",n); b[4:8]=struct.pack("<I",len(b)-8)
open("/home/user/DM48_Engine_demo.wav","wb").write(b)
import wave; w=wave.open("/home/user/DM48_Engine_demo.wav"); print(round(w.getnframes()/w.getframerate(),1),"s")

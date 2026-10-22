import sys, numpy as np
b=open(sys.argv[1],'rb').read()
i=b.index(b'data')+8
sr=44100
x=np.frombuffer(b[i:i+((len(b)-i)//4)*4],dtype=np.int16).reshape(-1,2).astype(float)/32768
print("dur",round(len(x)/sr,2),"peak",np.abs(x).max().round(3))
m=x.mean(1)
def f0(seg):
    seg=seg*np.hanning(len(seg)); N=1<<17
    S=np.abs(np.fft.rfft(seg,N)); hps=S.copy()
    for h in (2,3):
        d=S[::h]; hps[:len(d)]*=d
    hps[:int(60*N/sr)]=0
    k=np.argmax(hps[:len(hps)//3]); return k*sr/N
step=float(sys.argv[2]) if len(sys.argv)>2 else 0.2
t0=0
while t0*sr < len(m):
    seg=m[int(t0*sr):int((t0+step)*sr)]
    rms=np.sqrt((seg**2).mean())
    print(f"{t0:4.1f}s rms {rms:.3f}", f"f0 {f0(seg):7.1f}" if rms>0.005 else "")
    t0+=step

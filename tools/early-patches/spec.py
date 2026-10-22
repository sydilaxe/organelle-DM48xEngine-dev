import sys, numpy as np
b=open(sys.argv[1],'rb').read(); i=b.index(b'data')+8; sr=44100
x=np.frombuffer(b[i:i+((len(b)-i)//4)*4],dtype=np.int16).reshape(-1,2).astype(float).mean(1)/32768
t0,t1=float(sys.argv[2]),float(sys.argv[3])
seg=x[int(t0*sr):int(t1*sr)]; S=np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f=np.fft.rfftfreq(len(seg),1/sr)
top=np.argsort(S)[-8:][::-1]
print("top peaks:", [(round(f[k]),round(20*np.log10(S[k]/S.max()),1)) for k in top])
for lo,hi in ((0,1000),(1000,4000),(4000,10000),(10000,22050)):
    m=(f>=lo)&(f<hi); print(f"{lo}-{hi} Hz energy {10*np.log10((S[m]**2).sum()/(S**2).sum()):.1f} dB")

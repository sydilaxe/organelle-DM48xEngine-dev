import sys
mem={}; base=0; entry=None
for line in open(sys.argv[1]):
    line=line.strip()
    if not line.startswith(':'): continue
    n=int(line[1:3],16); addr=int(line[3:7],16); t=int(line[7:9],16); d=bytes.fromhex(line[9:9+2*n])
    if t==0:
        for i,b in enumerate(d): mem[base+addr+i]=b
    elif t==2: base=int.from_bytes(d,'big')<<4
    elif t==4: base=int.from_bytes(d,'big')<<16
lo,hi=min(mem),max(mem)
img=bytearray(b'\xff'*(hi-lo+1))
for a,b in mem.items(): img[a-lo]=b
open(sys.argv[2],'wb').write(img)
print(f"range 0x{lo:x}-0x{hi:x} size {len(img)}")

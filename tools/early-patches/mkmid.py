import struct, sys
def vlq(n):
    out=[n & 127]; n >>= 7
    while n: out.insert(0,(n & 127)|128); n >>= 7
    return bytes(out)
def track(events):  # events: list of (delta, bytes)
    d=b"".join(vlq(dt)+ev for dt,ev in events)
    return b"MTrk"+struct.pack(">I",len(d))+d
def smf(fmt, tracks, div=480):
    return b"MThd"+struct.pack(">IHHH",6,fmt,len(tracks),div)+b"".join(tracks)

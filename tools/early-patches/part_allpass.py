def allpass(c, x, y, src, name, ms, g=0.6):
    rd_ = c.obj(f"delread~ {name} {ms}", x + 120, y)
    gm = c.obj(f"*~ {g}", x + 120, y + 26)
    c.c(rd_, 0, gm, 0)
    w = c.obj("+~", x, y + 52)
    c.c(src, 0, w, 0)
    c.c(gm, 0, w, 1)
    c.c(w, 0, c.obj(f"delwrite~ {name} 50", x + 120, y + 78), 0)
    ng = c.obj(f"*~ {-g}", x, y + 104)
    c.c(w, 0, ng, 0)
    o = c.obj("+~", x, y + 130)
    c.c(ng, 0, o, 0)
    c.c(rd_, 0, o, 1)
    return o

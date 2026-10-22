def handler(c, x, y, entry, store_default, apply_objs, disp_msg, page, refresh=True):
    """entry receive -> [f] store -> apply chain + display. Returns the store [f]."""
    ent = c.obj(f"r {entry}", x, y)
    st = c.obj(f"f {store_default}", x, y + 30)
    c.c(ent, 0, st, 0)
    if refresh:
        c.c(c.obj(f"r $0-refresh{page}", x + 60, y), 0, st, 0)
    tt = c.obj("t f f", x, y + 60)
    c.c(st, 0, tt, 0)
    prev = None
    yy = y + 90
    for i, txt in enumerate(apply_objs):
        o = c.obj(txt, x + 90, yy)
        c.c(tt if prev is None else prev, 1 if prev is None else 0, o, 0)
        prev = o
        yy += 26
    dm_ = c.msg(disp_msg[1], x, y + 90 + 26 * max(len(apply_objs), 1) + 10)
    if disp_msg[0]:
        pre = None
        yy2 = y + 90
        for txt in disp_msg[0]:
            o = c.obj(txt, x, yy2)
            c.c(tt if pre is None else pre, 0, o, 0)
            pre = o
            yy2 += 26
        c.items[dm_] = ("msg", (x, yy2, disp_msg[1]))
        c.c(pre, 0, dm_, 0)
    else:
        c.c(tt, 0, dm_, 0)
    sd = c.obj(f"s $0-disp{page}", x, c.items[dm_][1][1] + 30)
    c.c(dm_, 0, sd, 0)
    return st



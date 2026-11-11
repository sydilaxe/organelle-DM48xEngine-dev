"""Tiny helper to write Pure Data patches from Python with named objects."""


def esc(text):
    # Pd file escaping: $ -> \$ ; commas/semicolons inside boxes -> \, \;
    out = text.replace("$", "\\$")
    out = out.replace(",", " \\,").replace(";", " \\;")
    return out


class Canvas:
    def __init__(self, name=None, w=900, h=700, font=10):
        self.name = name
        self.w, self.h, self.font = w, h, font
        self.items = []  # (kind, payload)
        self.conns = []
        self.col_x = 20
        self.y = 20
        self.ids = {}

    # layout helpers
    def column(self, x, y=20):
        self.col_x, self.y = x, y

    def _place(self, x, y):
        if x is None:
            x, y = self.col_x, self.y
            self.y += 26
        return x, y

    def obj(self, text, x=None, y=None, name=None):
        x, y = self._place(x, y)
        idx = len(self.items)
        self.items.append(("obj", (x, y, text)))
        if name:
            self.ids[name] = idx
        return idx

    def msg(self, text, x=None, y=None, name=None):
        x, y = self._place(x, y)
        idx = len(self.items)
        self.items.append(("msg", (x, y, text)))
        if name:
            self.ids[name] = idx
        return idx

    def comment(self, text, x=None, y=None):
        x, y = self._place(x, y)
        self.items.append(("text", (x, y, text)))
        return len(self.items) - 1

    def sub(self, canvas, x=None, y=None):
        x, y = self._place(x, y)
        self.items.append(("sub", (x, y, canvas)))
        return len(self.items) - 1

    def c(self, a, ao, b, bi):
        if isinstance(a, tuple):          # (object, outlet): e.g. one outlet of a subpatch with several
            a, ao = a
        self.conns.append((a, ao, b, bi))

    def chain(self, *idxs):
        for a, b in zip(idxs, idxs[1:]):
            self.c(a, 0, b, 0)

    def render(self, top=True, rx=0, ry=0):
        lines = []
        if top:
            lines.append(f"#N canvas 50 50 {self.w} {self.h} {self.font};")
        else:
            lines.append(f"#N canvas 50 50 {self.w} {self.h} {self.name} 0;")
        for kind, p in self.items:
            if kind == "obj":
                x, y, t = p
                lines.append(f"#X obj {x} {y} {esc(t)};")
            elif kind == "msg":
                x, y, t = p
                lines.append(f"#X msg {x} {y} {esc(t)};")
            elif kind == "text":
                x, y, t = p
                lines.append(f"#X text {x} {y} {esc(t)};")
            elif kind == "sub":
                x, y, cv = p
                lines.extend(cv.render(top=False, rx=x, ry=y))
        for a, ao, b, bi in self.conns:
            lines.append(f"#X connect {a} {ao} {b} {bi};")
        if not top:
            lines.append(f"#X restore {rx} {ry} pd {self.name};")
        return lines

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.render()) + "\n")

"""Compile simple expr~ formulas into native Pd signal objects (expr~ is slow on the Organelle's ARM CPU).

    out = compile_expr(canvas, "min(7000, $v1 * 2 + 3)", [src1, ...], x, y)

Handles + - * /, unary -, min, max, abs, fmod(x, 1) (x >= 0), pow, exp, sqrt, mtof and constants (folded at build
time). Anything else returns None, and the caller keeps the [expr~]."""
import ast, math

FUNCS = {"min": "min~", "max": "max~", "abs": "abs~", "exp": "exp~", "sqrt": "sqrt~", "mtof": "mtof~"}


class _Unsupported(Exception):
    pass


def compile_expr(c, text, ins, x, y):
    src = text
    for i in range(len(ins), 0, -1):
        src = src.replace(f"$v{i}", f"v{i}")
    try:
        tree = ast.parse(src, mode="eval").body
    except SyntaxError:
        return None
    pos = [x, y]

    def new(t):
        pos[1] += 22
        return c.obj(t, pos[0], pos[1])

    def num(v):
        return f"{v:.10g}"

    def sig(node):
        """-> ('c', value) or ('s', object index)"""
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return ("c", float(node.value))
        if isinstance(node, ast.Name) and node.id.startswith("v"):
            k = int(node.id[1:]) - 1
            if not 0 <= k < len(ins):
                raise _Unsupported
            return ("s", ins[k])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            a = sig(node.operand)
            return ("c", -a[1]) if a[0] == "c" else ("s", unary(a, "*~ -1"))
        if isinstance(node, ast.BinOp):
            a, b = sig(node.left), sig(node.right)
            op = type(node.op)
            if a[0] == "c" and b[0] == "c":
                f = {ast.Add: lambda p, q: p + q, ast.Sub: lambda p, q: p - q,
                     ast.Mult: lambda p, q: p * q, ast.Div: lambda p, q: p / q}.get(op)
                if f is None:
                    raise _Unsupported
                return ("c", f(a[1], b[1]))
            if op is ast.Add:
                return ("s", binop("+~", a, b, commut=True))
            if op is ast.Mult:
                return ("s", binop("*~", a, b, commut=True))
            if op is ast.Sub:
                if b[0] == "c":
                    return ("s", unary(a, f"-~ {num(b[1])}"))
                if a[0] == "c":                       # c - s
                    return ("s", unary(("s", unary(b, "*~ -1")), f"+~ {num(a[1])}"))
                return ("s", two("-~", a, b))
            if op is ast.Div:
                if b[0] == "c":
                    return ("s", unary(a, f"*~ {num(1 / b[1])}"))
                if a[0] == "c":                       # c / s
                    return ("s", two("/~", ("s", new(f"sig~ {num(a[1])}")), b))
                return ("s", two("/~", a, b))
            raise _Unsupported
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn, args = node.func.id, [sig(a) for a in node.args]
            if all(a[0] == "c" for a in args):
                py = {"min": min, "max": max, "abs": abs, "exp": math.exp, "sqrt": math.sqrt, "pow": math.pow,
                      "fmod": math.fmod, "mtof": lambda m: 440 * 2 ** ((m - 69) / 12)}
                if fn not in py:
                    raise _Unsupported
                return ("c", float(py[fn](*[a[1] for a in args])))
            if fn in ("min", "max") and len(args) == 2:
                a, b = args
                if a[0] == "c":
                    a, b = b, a
                if b[0] == "c":
                    return ("s", unary(a, f"{FUNCS[fn]} {num(b[1])}"))
                return ("s", two(FUNCS[fn], a, b))
            if fn in ("abs", "exp", "sqrt", "mtof") and len(args) == 1:
                return ("s", unary(args[0], FUNCS[fn]))
            if fn == "fmod" and len(args) == 2 and args[1] == ("c", 1.0):
                return ("s", unary(args[0], "wrap~"))        # same as fmod for x >= 0
            if fn == "pow" and len(args) == 2:
                a, b = args
                if a[0] == "c" and a[1] > 0:                 # c^s = exp(s ln c)
                    return ("s", unary(("s", unary(b, f"*~ {num(math.log(a[1]))}")), "exp~"))
                if b[0] == "c":
                    return ("s", unary(a, f"pow~ {num(b[1])}"))
                return ("s", two("pow~", a, b))
        raise _Unsupported

    def unary(a, t):
        o = new(t)
        c.c(a[1], 0, o, 0)
        return o

    def two(t, a, b):
        if a[0] == "c":
            a = ("s", new(f"sig~ {num(a[1])}"))
        if b[0] == "c":
            b = ("s", new(f"sig~ {num(b[1])}"))
        o = new(t)
        c.c(a[1], 0, o, 0)
        c.c(b[1], 0, o, 1)
        return o

    def binop(t, a, b, commut):
        if b[0] == "c":
            return unary(a, f"{t} {num(b[1])}")
        if a[0] == "c" and commut:
            return unary(b, f"{t} {num(a[1])}")
        return two(t, a, b)

    try:
        r = sig(tree)
    except _Unsupported:
        return None
    if r[0] == "c":
        return new(f"sig~ {num(r[1])}")
    return r[1]

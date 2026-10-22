"""Replay the patch's OLED messages (screenLineN + /oled/g* via oscOut) into 128x64 images."""
from PIL import Image, ImageDraw, ImageFont
import re
FONT = ImageFont.load_default()
class Oled:
    def __init__(self):
        self.img = Image.new("1", (128, 64), 0); self.d = ImageDraw.Draw(self.img)
    def calc(self, n): return (n - 1) * 11 + (9 if n > 0 else 0)
    def line(self, n, text):
        y = self.calc(n)
        if n == 1: self.d.rectangle([0, 8, 127, 8], fill=0)
        self.d.rectangle([0, y, 127, y + 10], fill=0)
        self.d.text((2, y), text[:21], fill=1, font=FONT)
    def g(self, cmd, a):
        if cmd == "gPrintln":
            x, y = int(float(a[1])), int(float(a[2])); c = int(float(a[4]))
            txt = " ".join(a[5:]).replace("\\ ", " ")
            self.d.text((x, y - 1), txt, fill=c, font=FONT); return
        a = [int(float(v)) for v in a[1:]] if a else []
        if cmd == "gFillArea": x, y, w, h, c = a[:5]; self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=c)
        elif cmd == "gBox": x, y, w, h, c = a[:5]; self.d.rectangle([x, y, x + w - 1, y + h - 1], outline=c)
        elif cmd == "gInvertArea":
            x, y, w, h = a[:4]
            for i in range(x, min(128, x + w)):
                for j in range(y, min(64, y + h)): self.img.putpixel((i, j), 1 - self.img.getpixel((i, j)))
        elif cmd == "gClear": self.d.rectangle([0, 0, 127, 63], fill=0)
        elif cmd == "gWaveform":          # [screen, y0..y127]: a polyline across the width
            ys = a[1:]
            for i in range(len(ys) - 1):
                self.d.line([i, ys[i], i + 1, ys[i + 1]], fill=1)
    def save(self, path, scale=4):
        rgb = Image.new("RGB", (128, 64))
        px = self.img.load(); out = rgb.load()
        for i in range(128):
            for j in range(64): out[i, j] = (235, 245, 255) if px[i, j] else (8, 10, 14)
        rgb.resize((128 * scale, 64 * scale), Image.NEAREST).save(path)

def render(log, outdir, prefix=""):
    o = Oled(); saved = []
    for l in log.splitlines():
        m = re.match(r"screenLine(\d): (?:list |symbol )?(.*)", l)
        if m: o.line(int(m.group(1)), m.group(2).replace("\\ ", " ")); continue
        m = re.match(r"oscOut: sendtyped /oled/(\w+) \w+ ?(.*)", l)
        if m: o.g(m.group(1), m.group(2).split()); continue
        m = re.match(r"oscOut: /oled/(\w+) ?(.*)", l)
        if m: o.g(m.group(1), m.group(2).split()); continue
        m = re.match(r"SNAP: (?:symbol )?(\S+)", l)
        if m:
            p = f"{outdir}/{prefix}{m.group(1)}.png"; o.save(p); saved.append(p)
    return saved

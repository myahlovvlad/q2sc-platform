"""Generate Q2SC app icons: ICO (Windows), ICNS (macOS), PNG (Linux)."""
from __future__ import annotations
import io, os, struct
from PIL import Image, ImageDraw

BASE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "build", "icons"
)
os.makedirs(BASE_DIR, exist_ok=True)

SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 16)
    ring = max(2, size // 20)
    # dark navy background circle
    d.ellipse([pad, pad, size - pad, size - pad], fill=(2, 6, 23, 255))
    # cyan outer ring
    d.ellipse([pad, pad, size - pad, size - pad], outline=(34, 211, 238, 255), width=ring)
    # inner accent
    inner_pad = size // 4
    d.ellipse(
        [inner_pad, inner_pad, size - inner_pad, size - inner_pad],
        fill=(34, 211, 238, 200),
    )
    # White Q letter (circle + tail)
    q_size = max(10, size // 3)
    q_x = size // 2 - q_size // 2
    q_y = size // 2 - q_size // 2
    q_pad = max(1, q_size // 8)
    stroke_w = max(1, q_size // 8)
    d.ellipse(
        [q_x + q_pad, q_y + q_pad, q_x + q_size - q_pad, q_y + q_size - q_pad],
        outline=(255, 255, 255, 255),
        width=stroke_w,
    )
    cx = q_x + q_size // 2
    cy = q_y + q_size // 2
    tail_w = max(1, q_size // 5)
    d.line(
        [cx + q_size // 5, cy + q_size // 5, cx + q_size // 3, cy + q_size // 3],
        fill=(255, 255, 255, 255),
        width=tail_w,
    )
    return img


def make_icns_entry(ostype: bytes, img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    return ostype + struct.pack(">I", 8 + len(data)) + data


frames: dict[int, Image.Image] = {}
for s in SIZES:
    frames[s] = make_frame(s)
    path = os.path.join(BASE_DIR, f"icon_{s}x{s}.png")
    frames[s].save(path, "PNG")
    print(f"  {path}")

# ICO for Windows (multi-size)
ico_path = os.path.join(BASE_DIR, "icon.ico")
frames[256].save(ico_path, format="ICO", sizes=[(s, s) for s in [16, 32, 48, 64, 128, 256]])
print(f"  {ico_path}")

# ICNS for macOS (PNG-compressed entries)
icns_path = os.path.join(BASE_DIR, "icon.icns")
icns_map = {b"ic07": 128, b"ic08": 256, b"ic09": 512, b"ic10": 1024}
entries = b"".join(make_icns_entry(t, frames[sz]) for t, sz in icns_map.items())
with open(icns_path, "wb") as f:
    f.write(b"icns" + struct.pack(">I", 8 + len(entries)) + entries)
print(f"  {icns_path}")

# 512×512 PNG for Linux
frames[512].save(os.path.join(BASE_DIR, "icon.png"), "PNG")
print("Done.")

from PIL import Image, ImageDraw, ImageFont
import os
W = H = 480
img = Image.new("RGB", (W, H), (30, 27, 75))
d = ImageDraw.Draw(img)
for y in range(H):
    t = y/(H-1)
    r=int(30+t*25); g=int(27+t*21); b=int(75+t*88)
    d.line([(0,y),(W,y)], fill=(r,g,b))
m = Image.new("L", (W, H), 0)
ImageDraw.Draw(m).rounded_rectangle([(0,0),(W-1,H-1)], radius=72, fill=255)
out = Image.new("RGB", (W, H), (255, 255, 255))
out.paste(img, (0, 0), m)
d = ImageDraw.Draw(out)
fb = ImageFont.truetype(r"C:/Windows/Fonts/arialbd.ttf", 240)
fs = ImageFont.truetype(r"C:/Windows/Fonts/arialbd.ttf", 38)
bb = d.textbbox((0, 0), "Ax", font=fb)
tw = bb[2]-bb[0]; tx = (W-tw)//2 - bb[0]
d.text((tx, 80), "Ax", fill=(254, 252, 232), font=fb)
bb2 = d.textbbox((0, 0), "AUDITEX", font=fs)
lw = bb2[2]-bb2[0]
d.text(((W-lw)//2 - bb2[0], 405), "AUDITEX", fill=(199, 210, 254), font=fs)
cx, cy, r = 370, 370, 56
d.ellipse([cx-r-6, cy-r-6, cx+r+6, cy+r+6], fill=(254, 252, 232))
d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(34, 197, 94))
d.line([(cx-28, cy+0), (cx-6, cy+22), (cx+28, cy-20)], fill=(254, 252, 232), width=10, joint="curve")
out.save(r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/docs/assets/auditex-logo.png", "PNG", optimize=True)
print("png_bytes", os.path.getsize(r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/docs/assets/auditex-logo.png"))

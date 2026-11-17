# SPDX-License-Identifier: Unlicense
"""Generate the five canonical font preview images."""


from build_ghosty_font import OUT, TTFont
from PIL import Image, ImageDraw, ImageFont

PREVIEW_FILES = (
    "all-hangul-native-24px.png",
    "hangul-contexts-native-32px.png",
    "jamo-symbols-native-32px.png",
    "native-640x480.png",
    "specimen-2x.png",
)



def grid(cps, destination, columns=96, size=24, cell=(30, 36)):
    font=ImageFont.truetype(str(OUT/"GhostyRoundGhost-Regular.ttf"),size)
    image=Image.new("RGB",(columns*cell[0],((len(cps)+columns-1)//columns)*cell[1]),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    draw.fontmode="L"
    for i,cp in enumerate(cps):
        draw.text(((i%columns)*cell[0]+3,(i//columns)*cell[1]+1),chr(cp),font=font,fill="#66429A")
    image.save(destination)










def specimen(destination, resolution=1):
    """Render directly at the requested size using Pillow, without Godot."""
    font_path=OUT/"GhostyRoundGhost-Regular.ttf"
    image=Image.new("RGB",(640*resolution,480*resolution),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    lines=[(24,48,38,"고스티 동글유령체"),
           (26,77,17,"Ghosty Round Ghost / Regular 1.700"),
           (24,128,32,"갋 값 밟 넓 짧 닭 읽 삶"),
           (24,164,24,". , · : ; ‥ …   ! ? ¡ ¿ ÷ ※"),
           (24,194,20,"곡 국 눈 붑 옹 숭 숯 / 안녕하세요."),
           (24,226,16,"16px  갋 값 밟 넓 짧 읽 삶 앉 많 싫 흙"),
           (24,256,20,"20px  갋 값 밟 넓 짧 읽 삶 앉 많 싫 흙"),
           (24,290,24,"24px  갋 값 밟 넓 짧 읽 삶 앉 많 싫 흙"),
           (24,331,32,"32px  갋 값 밟 넓 짧 읽 삶"),
           (24,402,40,"♤   ♧   †   ‡   £   ¢"),
           (24,473,16,"글자 획 굵기에 맞춘 동그란 점")]
    for x,y,size,text in lines:
        font=ImageFont.truetype(str(font_path),size*resolution)
        draw.text((x*resolution,y*resolution),text,font=font,fill="#66429A",anchor="ls")
    for y in (94,351):
        draw.line((24*resolution,y*resolution,616*resolution,y*resolution),fill="#9866D6",width=resolution)
    image.save(destination)
    return image




def main():
    directory=OUT/"preview"
    directory.mkdir(exist_ok=True)
    specimen(directory/"native-640x480.png",1)
    specimen(directory/"specimen-2x.png",2)
    f=TTFont(OUT/"GhostyRoundGhost-Regular.ttf")
    cps=sorted(f.getBestCmap())
    grid(list(range(0xAC00,0xD7A4)),directory/"all-hangul-native-24px.png")
    # Wider cells preserve the deliberately wide two-em and three-em dashes.
    nonhangul=[cp for cp in cps if not 0xAC00<=cp<=0xD7A3]
    grid(nonhangul,directory/"jamo-symbols-native-32px.png",columns=16,size=32,cell=(78,52))
    # A readable contextual specimen: all 19 initials x 21 medials, without
    # and with final clusters that put the most pressure on the native grid.
    contexts=[0xAC00+li*588+vi*28+ti for ti in (0,1,8,16,18,27)
              for li in range(19) for vi in range(21)]
    grid(contexts,directory/"hangul-contexts-native-32px.png",columns=21,size=32,cell=(38,43))
    print("Saved full Hangul, jamo/symbol, and contextual native-size sheets.")


if __name__=="__main__":
    main()

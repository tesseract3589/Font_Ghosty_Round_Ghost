# SPDX-License-Identifier: Unlicense
"""Rasterize grayscale contact sheets and an optional before/after specimen."""

import argparse

from build_ghosty_font import OUT, TTFont
from PIL import Image, ImageDraw, ImageFont


def grid(cps, destination, columns=96, size=24, cell=(30, 36)):
    font=ImageFont.truetype(str(OUT/"GhostyRoundGhost-Regular.ttf"),size)
    image=Image.new("RGB",(columns*cell[0],((len(cps)+columns-1)//columns)*cell[1]),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    draw.fontmode="L"
    for i,cp in enumerate(cps):
        draw.text(((i%columns)*cell[0]+3,(i//columns)*cell[1]+1),chr(cp),font=font,fill="#66429A")
    image.save(destination)


def comparison(before,destination):
    current=OUT/"GhostyRoundGhost-Regular.ttf"
    image=Image.new("RGB",(1280,620),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    ink="#66429A"
    draw.line((640,28,640,590),fill="#C19AF2",width=2)
    for i,path in enumerate([before,current]):
        x=32+i*640
        draw.fontmode="L"
        draw.text((x,22),"수정 전" if i==0 else "수정 후",font=ImageFont.truetype(str(current),36),fill=ink)
        draw.fontmode="L"
        for y,size,text in [(94,96,"갋 ㄹ ㅂ ㄼ"),
                            (260,24,"갋 값 밟 넓 짧 닭 읽 삶"),
                            (308,32,"갋 값 밟 넓 짧 읽 삶"),
                            (378,24,"말랑말랑 동글동글 통통한 유령"),
                            (432,20,"라 러 로 루 리 / 바 버 보 부 비"),
                            (486,16,"16px  갋 값 밟 넓 짧 읽 삶 앉 많 싫 흙"),
                            (526,20,"20px  갋 값 밟 넓 짧 읽 삶 앉 많 싫 흙")]:
            draw.text((x,y),text,font=ImageFont.truetype(str(path),size),fill=ink)
    image.save(destination)


def proportions(before,destination):
    current=OUT/"GhostyRoundGhost-Regular.ttf"
    image=Image.new("RGB",(1280,680),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    for i,path in enumerate([before,current]):
        y=i*330
        draw.text((32,y+15),"수정 전" if i==0 else "수정 후",font=ImageFont.truetype(str(current),26),fill="#9866D6")
        for dy,size,text in [(65,64,"아야어여오요우유으이의에외"),
                             (165,48,"욺 옮 앎 삶 갋 밟 넓 읽 흙"),
                             (245,30,"자음은 자연스럽게, 모음은 조금 짧게")]:
            draw.text((32,y+dy),text,font=ImageFont.truetype(str(path),size),fill="#352052")
    image.save(destination)


def e_spacing(before,destination):
    current=OUT/"GhostyRoundGhost-Regular.ttf"
    image=Image.new("RGB",(1280,620),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    for i,path in enumerate([before,current]):
        y=i*300
        draw.text((32,y+12),"수정 전" if i==0 else "수정 후",font=ImageFont.truetype(str(current),25),fill="#9866D6")
        for dy,size,text in [(62,72,"ㅔ 에 게 네 데 레 메 베 세"),
                             (175,38,"네게 전해 줄 메세지와 작은 별"),
                             (237,24,"둥근 자음과 짧은 모음 / ABC 012345")]:
            draw.text((32,y+dy),text,font=ImageFont.truetype(str(path),size),fill="#352052")
    image.save(destination)


def dots(before,destination):
    current=OUT/"GhostyRoundGhost-Regular.ttf"
    image=Image.new("RGB",(1200,600),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    for i,path in enumerate([before,current]):
        y=i*290
        draw.text((32,y+8),"수정 전" if i==0 else "수정 후",font=ImageFont.truetype(str(current),24),fill="#9866D6")
        for dy,size,text in [(40,72,". , · : ; ‥ …"),
                             (142,44,"i j ! ? ¡ ¿ ÷ ※  fi ffi"),
                             (223,24,"안녕! 잘 지냈니? 하나… 둘… 셋.")]:
            draw.text((32,y+dy),text,font=ImageFont.truetype(str(path),size),fill="#352052")
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


def stems_and_dots(before,destination):
    current=OUT/"GhostyRoundGhost-Regular.ttf"
    image=Image.new("RGB",(1280,820),"#F3E6FF")
    draw=ImageDraw.Draw(image)
    for i,path in enumerate([before,current]):
        y=i*405
        draw.text((32,y+12),"수정 전" if i==0 else "수정 후",font=ImageFont.truetype(str(current),25),fill="#9866D6")
        for dy,size,text in [(55,52,"I Can't Stand.  안녕하세요."),
                             (140,64,"옹 옹 곡 국 눈 눈 숯 숭 붑"),
                             (240,32,". · : ; ‥ … ! ?  / 곡 국 눈 붑 옹 숯"),
                             (305,20,"20px  곡 국 눈 붑 옹 숯. 안녕하세요."),
                             (350,24,"24px  곡 국 눈 붑 옹 숯. 안녕하세요.")]:
            draw.text((32,y+dy),text,font=ImageFont.truetype(str(path),size),fill="#352052")
    image.save(destination)


def main(before=None):
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
    if before:
        comparison(before,directory/"readability-before-after.png")
        proportions(before,directory/"proportions-before-after.png")
        e_spacing(before,directory/"e-spacing-before-after.png")
        dots(before,directory/"dots-before-after.png")
        stems_and_dots(before,directory/"stems-and-dots-before-after.png")
    print("Saved full Hangul, jamo/symbol, and contextual native-size sheets.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before",type=str,help="Optional previous project font, for visual comparison")
    main(parser.parse_args().before)

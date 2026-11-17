# SPDX-License-Identifier: Unlicense
"""Build Ghosty Round Ghost from original, editable stroke drawings.

Dependencies: fonttools, skia-pathops, Pillow, uharfbuzz (verification).
No outlines or font tables from another typeface are imported. The optional
reference is read only to compare Unicode coverage, never to construct glyphs.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT
SOURCE = Path(__file__).resolve().parent
EM = 1000
FAMILY = "Ghosty Round Ghost"
KOREAN_FAMILY = "고스티 동글유령체"
VERSION = "1.700"
STROKE_WIDTH = 100
DOT_DIAMETER = 150
PAIR_GAP = 32
HANGUL_ADVANCE = 860
HANGUL_OFFSET_X = -17
STROKE_WIDTHS_USED = set()
GHOST_SLOTS = {0x2664: "outline", 0x2667: "floating", 0x2020: "solid",
               0x2021: "sparkle", 0x00A3: "half", 0x00A2: "flame"}


class Drawing:
    """Paths use a top-down, 100 x 100 design space; pens use font units."""

    def __init__(self):
        self.items = []

    def poly(self, *points, close=False, smooth=7):
        self.items.append(("poly", points, close, smooth))
        return self

    def curve(self, commands, fill=False):
        self.items.append(("curve", commands, fill))
        return self

    def oval(self, x, y, rx, ry, fill=False):
        k = 0.55228475
        return self.curve([
            ("M", x+rx, y),
            ("C", x+rx, y+ry*k, x+rx*k, y+ry, x, y+ry),
            ("C", x-rx*k, y+ry, x-rx, y+ry*k, x-rx, y),
            ("C", x-rx, y-ry*k, x-rx*k, y-ry, x, y-ry),
            ("C", x+rx*k, y-ry, x+rx, y-ry*k, x+rx, y), ("Z",)
        ], fill=fill)

    def dot(self, x, y, radius=DOT_DIAMETER/2):
        # Circular in font units, even inside a narrow punctuation design box.
        self.items.append(("dot", x, y, radius))
        return self

    def append(self, other, box=(0, 0, 100, 100)):
        x, y, w, h = box
        for item in other.items:
            if item[0] == "dot":
                _,px,py,r=item
                self.dot(x+px*w/100,y+py*h/100,r)
            elif item[0] == "poly":
                _, pts, closed, sm = item
                self.poly(*[(x+px*w/100, y+py*h/100) for px, py in pts],
                          close=closed,
                          smooth=sm*min(w, h)/100)
            else:
                _, commands, fill = item
                transformed = []
                for command in commands:
                    values = command[1:]
                    values = [x+v*w/100 if i % 2 == 0 else y+v*h/100
                              for i, v in enumerate(values)]
                    transformed.append((command[0], *values))
                self.curve(transformed, fill=fill)
        return self

    def transformed(self, angle=0, cx=50, cy=50):
        angle = math.radians(angle)
        def point(x,y):
            return (cx+(x-cx)*math.cos(angle)-(y-cy)*math.sin(angle),
                    cy+(x-cx)*math.sin(angle)+(y-cy)*math.cos(angle))
        d = Drawing()
        for item in self.items:
            if item[0] == "dot":
                _,x,y,r=item
                d.dot(*point(x,y),r)
            elif item[0] == "poly":
                _,pts,cl,sm=item
                d.poly(*[point(x,y) for x,y in pts],close=cl,smooth=sm)
            else:
                _,cmds,fill=item
                commands=[]
                for op,*vals in cmds:
                    flattened=[]
                    for i in range(0,len(vals),2): flattened.extend(point(*vals[i:i+2]))
                    commands.append((op,*flattened))
                d.curve(commands,fill=fill)
        return d

    def path(self, box):
        # Expand centerlines only after placement: scaling/packing must never
        # change the pen width.
        x, y, w, h = box
        result = pathops.Path()

        def point(p):
            return (x+p[0]*w/100, 820-y-p[1]*h/100)

        for item in self.items:
            path = pathops.Path()
            pen = path.getPen()
            if item[0] == "dot":
                _,px,py,r=item
                px,py=point((px,py)); k=.55228475
                pen.moveTo((px+r,py))
                pen.curveTo((px+r,py+k*r),(px+k*r,py+r),(px,py+r))
                pen.curveTo((px-k*r,py+r),(px-r,py+k*r),(px-r,py))
                pen.curveTo((px-r,py-k*r),(px-k*r,py-r),(px,py-r))
                pen.curveTo((px+k*r,py-r),(px+r,py-k*r),(px+r,py))
                pen.closePath()
            elif item[0] == "poly":
                _, pts, closed, sm = item
                # Round the centerline bends as well as the stroke endpoints.
                def corners(i):
                    p = pts[i]
                    a, b = pts[(i-1) % len(pts)], pts[(i+1) % len(pts)]
                    da, db = math.dist(a, p), math.dist(b, p)
                    radius = min(sm, da*.42, db*.42)
                    return ((p[0]+(a[0]-p[0])*radius/da,
                             p[1]+(a[1]-p[1])*radius/da),
                            (p[0]+(b[0]-p[0])*radius/db,
                             p[1]+(b[1]-p[1])*radius/db))

                if closed:
                    pen.moveTo(point(corners(0)[1]))
                    order = list(range(1, len(pts))) + [0]
                else:
                    pen.moveTo(point(pts[0]))
                    order = range(1, len(pts)-1)
                for i in order:
                    before, after = corners(i)
                    pen.lineTo(point(before))
                    pen.qCurveTo(point(pts[i]), point(after))
                if closed:
                    pen.closePath()
                else:
                    if len(pts) == 2:
                        # A very shallow bow avoids rigid ruler-straight stems.
                        a, b = pts
                        mid = ((a[0]+b[0])/2+(b[1]-a[1])*.014,
                               (a[1]+b[1])/2-(b[0]-a[0])*.014)
                        pen.qCurveTo(point(mid), point(b))
                    else:
                        pen.lineTo(point(pts[-1]))
                    pen.endPath()
                STROKE_WIDTHS_USED.add(STROKE_WIDTH)
                path.stroke(STROKE_WIDTH, pathops.LineCap.ROUND_CAP,
                            pathops.LineJoin.ROUND_JOIN, 4)
            else:
                _, commands, fill = item
                for op, *vals in commands:
                    ps = [point(vals[i:i+2]) for i in range(0, len(vals), 2)]
                    if op == "M":
                        pen.moveTo(ps[0])
                    elif op == "L":
                        pen.lineTo(ps[0])
                    elif op == "Q":
                        pen.qCurveTo(*ps)
                    elif op == "C":
                        pen.curveTo(*ps)
                    elif op == "Z":
                        pen.closePath()
                if commands[-1][0] != "Z":
                    pen.endPath()
                if not fill:
                    STROKE_WIDTHS_USED.add(STROKE_WIDTH)
                    path.stroke(STROKE_WIDTH, pathops.LineCap.ROUND_CAP,
                                pathops.LineJoin.ROUND_JOIN, 4)
            result.addPath(path)
        if len(result):
            result.convertConicsToQuads(0.15)
            result.simplify(clockwise=True)
        return result


DOUBLES = {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}
CLUSTERS = {"ㄳ": "ㄱㅅ", "ㄵ": "ㄴㅈ", "ㄶ": "ㄴㅎ", "ㄺ": "ㄹㄱ",
            "ㄻ": "ㄹㅁ", "ㄼ": "ㄹㅂ", "ㄽ": "ㄹㅅ", "ㄾ": "ㄹㅌ",
            "ㄿ": "ㄹㅍ", "ㅀ": "ㄹㅎ", "ㅄ": "ㅂㅅ"}
def consonant(letter, final=False):
    d = Drawing()
    if letter == "ㄱ":
        d.curve([("M",14,18),("C",34,13,65,11,81,14),
                 ("Q",90,15,87,30),("C",84,48,85,69,81,85)])
    elif letter == "ㄴ":
        d.curve([("M",17,13),("C",14,33,13,62,16,76),
                 ("Q",17,86,30,86),("C",49,88,68,84,86,81)])
    elif letter == "ㄷ":
        d.curve([("M",85,16),("C",64,12,42,12,27,15),
                 ("Q",14,16,14,30),("L",14,69),
                 ("Q",14,84,29,85),("C",48,87,69,83,86,80)])
    elif letter == "ㄹ":
        if final:
            d.curve([("M",19,13),("C",39,10,65,11,79,15),
                     ("Q",87,18,84,30),("Q",83,45,69,47),
                     ("L",29,49),("Q",14,49,15,63),("L",17,74),
                     ("Q",18,87,33,87),("C",51,89,70,85,84,82)])
            return d
        d.curve([("M",16,15),("C",35,11,62,11,79,14),
                 ("Q",87,15,86,25),("L",85,36),
                 ("Q",84,46,72,47),("L",29,49),
                 ("Q",15,49,15,61),("L",15,72),
                 ("Q",15,85,29,86),("C",49,88,69,84,86,81)])
    elif letter == "ㅁ":
        d.curve([("M",29,15),("C",43,12,63,12,76,15),
                 ("Q",86,18,86,31),("L",85,70),
                 ("Q",84,84,70,86),("C",54,88,36,87,25,84),
                 ("Q",14,81,14,68),("L",15,31),
                 ("Q",16,17,29,15),("Z",)])
    elif letter == "ㅂ":
        d.curve([("M",18,10),("C",14,30,13,59,16,75),
                 ("Q",17,86,31,87),("L",71,86),
                 ("Q",85,85,86,71),("C",88,49,85,27,83,10)])
        d.curve([("M",17,47),("Q",49,51,84,45)])
    elif letter == "ㅅ":
        d.curve([("M",49,15),("C",48,40,34,66,15,82)])
        d.curve([("M",49,25),("C",56,47,67,68,85,80)])
    elif letter == "ㅇ":
        d.oval(50, 51, 35, 35)
    elif letter == "ㅈ":
        d.curve([("M",14,18),("Q",49,13,86,16)])
        d.curve([("M",51,20),("C",49,44,35,67,15,83)])
        d.curve([("M",49,34),("C",58,53,69,70,85,80)])
    elif letter == "ㅊ":
        d.poly((39,4),(61,3))
        d.append(consonant("ㅈ"), (0, 23, 100, 77))
    elif letter == "ㅋ":
        d.append(consonant("ㄱ"))
        d.poly((15, 49), (84, 47))
    elif letter == "ㅌ":
        d.append(consonant("ㄷ"))
        d.poly((17, 49), (82, 47))
    elif letter == "ㅍ":
        d.poly((10, 14), (89, 12)).poly((10, 86), (90, 84))
        d.poly((31, 15), (29, 85)).poly((70, 14), (71, 83))
    elif letter == "ㅎ":
        d.poly((50,3),(50,25))
        d.curve([("M",15,26),("Q",50,22,85,24)])
        d.oval(50,75,31,17)
    else:
        raise ValueError(letter)
    return d


def vowel(letter, compact=False):
    d = Drawing()
    # All vowels are drawn separately; the mixed vowels reserve their upper
    # left quadrant for the initial consonant rather than squeezing it.
    vertical = {
        "ㅏ": [((24, 4), (23, 96)), ((24, 47), (83, 45))],
        "ㅐ": [((16, 4), (15, 96)), ((85, 3), (84, 97)), ((16, 47), (56, 46))],
        "ㅑ": [((24, 4), (23, 96)), ((24, 32), (83, 31)), ((24, 66), (83, 65))],
        "ㅒ": [((16, 4), (15, 96)), ((85, 3), (84, 97)), ((16, 32), (56, 31)), ((16, 66), (56, 65))],
        "ㅓ": [((75, 4), (74, 96)), ((16, 48), (74, 46))],
        "ㅔ": [((43, 8), (42, 93)), ((89, 3), (88, 97)), ((7, 48), (42, 46))],
        "ㅕ": [((75, 4), (74, 96)), ((16, 33), (74, 31)), ((16, 67), (74, 65))],
        "ㅖ": [((49, 4), (48, 96)), ((89, 3), (88, 97)), ((6, 33), (48, 31)), ((6, 67), (48, 65))],
        "ㅣ": [((49, 4), (48, 96))],
    }
    horizontal = {
        "ㅗ": [((6, 76), (94, 74)), ((50, 15), (49, 74))],
        "ㅛ": [((6, 76), (94, 74)), ((34, 15), (33, 74)), ((68, 14), (67, 74))],
        "ㅜ": [((6, 26), (94, 24)), ((50, 25), (49, 86))],
        "ㅠ": [((6, 26), (94, 24)), ((34, 26), (33, 86)), ((68, 25), (67, 85))],
        "ㅡ": [((6, 51), (94, 49))],
    }
    if letter in vertical or letter in horizontal:
        for pts in (vertical | horizontal)[letter]:
            d.poly(*pts)
        return d
    if letter in "ㅘㅙㅚ":
        base,tip = (90,74) if compact else (82,66)
        d.poly((4,base),(59,base-2)).poly((31,tip),(30,base-1))
    elif letter in "ㅝㅞㅟ":
        base,tip = (78,96) if compact else (65,90)
        d.poly((4,base),(59,base-2)).poly((31,base-1),(30,tip))
    elif letter == "ㅢ":
        d.poly((4,91 if compact else 80),(59,89 if compact else 78))
    if letter == "ㅘ":
        d.poly((77, 4), (76, 86 if compact else 97)).poly((77, 46), (98, 45))
    elif letter == "ㅙ":
        bottom=86 if compact else 97
        d.poly((70, 4), (69, bottom)).poly((96, 3), (95, bottom)).poly((70, 46), (81, 45))
    elif letter in "ㅚㅟㅢ":
        d.poly((85, 4), (84, 86 if compact else 97))
    elif letter == "ㅝ":
        d.poly((86, 4), (85, 86 if compact else 97)).poly((65, 45), (85, 43))
    elif letter == "ㅞ":
        bottom=86 if compact else 97
        d.poly((75, 4), (74, bottom)).poly((97, 3), (96, bottom)).poly((65, 45), (74, 44))
    else:
        raise ValueError(letter)
    return d


INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
MEDIALS = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
FINALS = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
COMPAT = "ㄱㄲㄳㄴㄵㄶㄷㄸㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅃㅄㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ" + MEDIALS


def consonant_outline(letter, box, final=False):
    """Pack paired outlines by their actual ink bounds without scaling strokes."""
    bx,by,w,h=box
    if letter not in DOUBLES and letter not in CLUSTERS:
        # Preserve a natural consonant aspect inside the allotted space. Change
        # centerline dimensions before stroking; the pen remains uniform.
        max_ratio=1.15 if letter in "ㅇㅁ" else 1.20 if final and letter in "ㄹㅂ" else 1.30
        fitted_w=min(w,h*max_ratio)
        fitted_h=min(h,fitted_w*1.15) if letter in "ㅇㅁ" else h
        bx+=(w-fitted_w)/2
        by+=(h-fitted_h)/2
        w,h=fitted_w,fitted_h
        box=(bx,by,w,h)
        path=consonant(letter,final=final).path(box)
        probes=[(bx+x*w/100,820-by-y*h/100) for x,y in consonant_probes(letter)]
        return path,probes,[]
    pair=DOUBLES[letter]*2 if letter in DOUBLES else CLUSTERS[letter]

    def children(child_width):
        left,lp,_=consonant_outline(pair[0],(0,by,child_width,h),final=final)
        right,rp,_=consonant_outline(pair[1],(0,by,child_width,h),final=final)
        right_offset=left.bounds[2]+PAIR_GAP-right.bounds[0]
        combined_width=right.bounds[2]+right_offset-left.bounds[0]
        return left,right,lp,rp,right_offset,combined_width

    low,high=w*.15,w*.55
    for _ in range(14):
        middle=(low+high)/2
        if children(middle)[-1] <= w: low=middle
        else: high=middle
    left,right,lp,rp,offset,width=children(low)
    origin=bx+(w-width)/2-left.bounds[0]
    left=left.transform(1,0,0,1,origin,0)
    right=right.transform(1,0,0,1,origin+offset,0)
    path=pathops.op(left,right,pathops.PathOp.UNION)
    path.simplify(clockwise=True)
    probes=[(x+origin,y) for x,y in lp]+[(x+origin+offset,y) for x,y in rp]
    gap=right.bounds[0]-left.bounds[2]
    return path,probes,[gap]


def hangul_parts(cp):
    index = cp - 0xAC00
    li, vi, ti = index//588, index//28 % 21, index % 28
    has_final = bool(ti)
    v = MEDIALS[vi]
    if v in "ㅏㅐㅑㅒㅓㅔㅕㅖㅣ":
        initial_box = (30,35 if has_final else 65,520,450 if has_final else 650)
        vowel_box = (590,35 if has_final else 60,270,420 if has_final else 700)
    elif v in "ㅗㅛㅜㅠㅡ":
        initial_box = (180,-20 if has_final else 0,560,360 if has_final else 520)
        vowel_y = (375 if v in "ㅜㅠ" else 390) if has_final else (520 if v=="ㅡ" else 560)
        vowel_box = (125,vowel_y,660,100 if has_final else 260)
        if has_final and v in "ㅗㅛㅜㅠ":
            # Reserve real stem length above/below the bar rather than
            # shrinking it into a pen-width-sized bump.
            initial_box=(180,-90 if v in "ㅗㅛ" else -55,560,360)
            vowel_box=(125,315 if v in "ㅗㅛ" else 330,660,200)
    else:
        initial_box = (20,-40 if has_final else -20,475,350 if has_final else 450)
        vowel_box = (80,20 if has_final else 30,740,490 if has_final else 760)
    if INITIALS[li] == "ㅎ" and v not in "ㅏㅐㅑㅒㅓㅔㅕㅖㅣ":
        x,y,w,h=initial_box
        initial_box=(x,y-20,w,h)
    parts = [("L",li,initial_box,STROKE_WIDTH),
             ("VC" if has_final else "V",vi,vowel_box,STROKE_WIDTH)]
    if has_final:
        # Final clusters get genuine height and width, rather than a flattened
        # copy of an initial. In particular ㄼ needs both ㄹ channels and the ㅂ
        # counter to survive independently.
        final_width = 660 if FINALS[ti] in CLUSTERS or FINALS[ti] in DOUBLES else 400 if FINALS[ti] == "ㅇ" else 470
        final_box = ((920-final_width)/2,610 if v in "ㅜㅠ" else 575,final_width,380)
        parts.append(("T",ti,final_box,STROKE_WIDTH))
    return parts


def latin(letter):
    d = Drawing()
    # Original monoline letter skeletons. Their slight asymmetry is deliberate.
    strokes = {
        "A": [[(9,94),(47,9),(53,8),(92,93)],[(27,61),(74,60)]],
        "E": [[(87,10),(17,12),(15,93),(88,91)],[(17,51),(75,49)]],
        "F": [[(18,94),(19,12),(88,10)],[(20,51),(74,49)]],
        "H": [[(16,10),(14,94)],[(86,9),(85,94)],[(16,52),(85,50)]],
        "I": [[(27,11),(74,9)],[(51,11),(49,92)],[(25,94),(74,92)]],
        "K": [[(17,10),(15,94)],[(87,10),(18,57),(88,93)]],
        "L": [[(19,10),(17,93),(88,91)]],
        "M": [[(10,94),(13,12),(21,10),(51,61),(80,10),(87,12),(91,93)]],
        "N": [[(15,94),(17,11),(25,11),(84,92),(88,91),(86,9)]],
        "T": [[(7,12),(94,10)],[(51,12),(49,94)]],
        "V": [[(8,10),(45,92),(53,94),(92,9)]],
        "W": [[(5,10),(26,94),(33,93),(51,40),(69,93),(76,94),(96,9)]],
        "X": [[(12,11),(89,93)],[(88,10),(11,94)]],
        "Y": [[(9,10),(50,57),(90,9)],[(50,57),(49,94)]],
        "Z": [[(12,12),(88,10),(13,93),(90,91)]],
        "h": [[(16,4),(14,94)]], "k": [[(17,4),(15,94)],[(83,36),(17,70),(88,93)]],
        "l": [[(46,4),(43,85),(51,94),(67,92)]],
        "t": [[(47,15),(45,81),(52,94),(75,91)],[(16,42),(79,40)]],
        "v": [[(12,37),(47,93),(54,94),(89,35)]],
        "w": [[(6,37),(25,94),(32,93),(51,56),(68,93),(75,94),(95,36)]],
        "x": [[(17,38),(85,93)],[(84,36),(15,94)]],
        "z": [[(15,39),(84,37),(17,94),(87,92)]],
        "1": [[(26,30),(51,12),(52,92)],[(29,94),(78,92)]],
        "4": [[(70,11),(17,63),(88,61)],[(70,11),(68,94)]],
        "7": [[(12,13),(89,11),(43,94)]],
    }
    for pts in strokes.get(letter, []):
        d.poly(*pts, smooth=9)
    curves = {
        "B": [("M",18,53),("L",19,12),("C",91,-1,107,48,20,53),("C",110,37,105,104,17,93),("L",18,53),("Z",)],
        "C": [("M",87,21),("C",13,-18,-10,72,33,92),("Q",61,106,89,80)],
        "D": [("M",18,93),("L",20,12),("C",110,-3,115,109,18,93),("Z",)],
        "G": [("M",87,23),("C",17,-20,-9,77,37,94),("Q",70,106,88,80),("L",89,56),("L",61,57)],
        "J": [("M",84,10),("L",82,72),("C",84,107,17,108,15,75)],
        "P": [("M",18,94),("L",20,12),("C",105,-2,112,66,20,58)],
        "Q": [("M",66,73),("Q",81,86,97,99)],
        "R": [("M",18,94),("L",20,12),("C",105,-2,112,66,20,58),("M",53,58),("L",91,93)],
        "S": [("M",86,22),("C",59,-8,5,9,18,38),("C",27,59,94,44,88,76),("C",83,103,33,103,12,82)],
        "U": [("M",15,10),("L",14,65),("C",12,107,88,105,86,64),("L",87,9)],
        "a": [("M",82,39),("L",80,92)],
        "b": [("M",17,4),("L",15,94)],
        "c": [("M",84,45),("C",31,11,-3,65,30,89),("Q",57,105,85,82)],
        "d": [("M",84,4),("L",82,94)],
        "e": [("M",17,66),("L",84,64),("C",92,29,42,25,24,44),("C",0,66,27,111,85,85)],
        "f": [("M",37,94),("L",39,29),("Q",40,-1,78,7),("M",15,42),("L",75,40)],
        "g": [("M",83,38),("L",81,108),("Q",76,133,30,118)],
        "h": [("M",16,58),("C",34,23,85,26,84,60),("L",83,94)],
        "i": [("M",48,40),("L",47,93)],
        "j": [("M",61,40),("L",59,106),("Q",58,131,25,116)],
        "m": [("M",12,94),("L",13,39),("M",13,56),("C",28,23,54,33,52,58),("L",51,94),("M",52,57),("C",66,24,91,31,89,59),("L",88,93)],
        "n": [("M",17,94),("L",18,38),("M",18,57),("C",40,21,85,27,84,60),("L",83,94)],
        "p": [("M",18,39),("L",16,122)],
        "q": [("M",83,39),("L",81,122)],
        "r": [("M",20,94),("L",21,39),("M",21,58),("Q",43,25,80,39)],
        "s": [("M",81,45),("C",54,23,11,37,22,57),("C",30,72,88,60,81,83),("C",75,102,38,102,16,84)],
        "u": [("M",17,39),("L",16,71),("C",12,108,64,99,81,77),("M",84,38),("L",82,94)],
        "y": [("M",14,38),("L",45,93),("M",86,36),("L",51,107),("Q",41,129,21,120)],
        "2": [("M",15,29),("C",28,-6,99,5,83,40),("Q",75,57,16,91),("L",89,91)],
        "3": [("M",16,23),("C",65,-8,110,31,50,50),("C",114,48,103,115,14,88)],
        "5": [("M",87,12),("L",24,14),("L",20,51),("C",101,22,118,111,17,90)],
        "6": [("M",81,13),("C",29,-3,-9,97,52,95),("C",112,94,93,36,53,45),("Q",29,47,19,66)],
        "9": [("M",20,92),("C",74,110,110,7,48,10),("C",-9,14,10,70,51,62),("Q",74,59,84,40)],
    }
    if letter in curves:
        d.curve(curves[letter])
    if letter in "OQ0":
        d.oval(50,52,38,42)
    if letter in "abdgpq":
        d.oval(49,66,33,28)
    if letter == "o":
        d.oval(50,66,35,29)
    if letter == "8":
        d.oval(50,30,30,22).oval(49,74,35,23)
    if letter in "ij":
        d.dot(49 if letter == "i" else 62,16)
    if not d.items:
        raise ValueError(f"Undrawn Latin character {letter!r}")
    return d


def ghost(kind):
    """Six original wisp silhouettes: eyes only, no mouth or limbs."""
    body = [("M",19,66),("C",6,49,11,17,39,12),
            ("C",67,5,84,25,78,48),("Q",76,63,89,65),
            ("Q",102,67,90,77),("C",64,96,34,89,19,66),("Z",)]
    d = Drawing()
    d.curve(body)
    if kind == "floating":
        d = Drawing().append(d.transformed(-13),(3,2,91,87))
        d.poly((25,98),(46,97))
    if kind == "sparkle":
        d = Drawing().append(d,(0,18,80,80))
        d.poly((83,8),(83,25)).poly((75,17),(91,16))
        d.poly((94,40),(94,49)).poly((90,45),(98,44))
    # Eyes are added as filled ovals, or subtracted from a solid silhouette.
    if kind in ("solid", "half"):
        d.items[0] = ("curve", body, True)
    eyes = Drawing().oval(32,41,3.7,5.6,fill=True).oval(53,39,3.7,5.6,fill=True)
    if kind == "floating":
        eyes = Drawing().append(eyes.transformed(-13),(3,2,91,87))
    if kind == "sparkle":
        eyes = Drawing().append(eyes,(0,18,80,80))
    if kind == "flame":
        d.curve([("M",77,69),("Q",99,56,91,40),("Q",112,59,96,79)])
    return d, eyes


def symbol(cp):
    c = chr(cp)
    d = Drawing()
    if c in "!¡":
        d.poly((50,12),(49,66)).dot(49,88)
    elif c in "?¿":
        d.curve([("M",21,26),("C",35,-5,94,6,82,34),("Q",78,45,53,54),("L",50,66)])
        d.dot(49,88)
    elif c in "\"'‘’“”′″`":
        n = 2 if c in "\"“”″" else 1
        for i in range(n):
            d.poly((38+i*25,11),(33+i*25,28))
    elif c in "()[]{}〈〉《》「」『』【】〔〕":
        right = c in ")]}>〉》」』】〕"
        x = 100 if right else 0
        def pts(points):
            return [(x-px if right else px,py) for px,py in points]
        if c in "()〔〕":
            d.curve([("M",*(pts([(68,5)])[0])),("Q",*(sum((list(p) for p in pts([(20,50),(66,98)])),[])))])
        elif c in "{}":
            d.poly(*pts([(73,5),(49,7),(46,40),(29,50),(46,60),(47,93),(72,97)]))
        elif c in "〈〉《》":
            d.poly(*pts([(69,9),(31,50),(68,92)]))
            if c in "《》":
                d.poly(*pts([(96,9),(58,50),(95,92)]))
        elif c in "「」『』":
            d.poly(*pts([(73,10),(34,11),(34,91)]))
            if c in "『』":
                d.poly(*pts([(78,25),(51,26),(51,91)]))
        else:
            d.poly(*pts([(74,8),(34,10),(33,93),(73,92)]))
    elif c in "/\\|_—–‒―⸺⸻-−":
        if c == "/": d.poly((79,6),(22,98))
        elif c == "\\": d.poly((23,6),(78,98))
        elif c == "|": d.poly((50,5),(49,98))
        else: d.poly((9,96 if c=="_" else 52),(91,94 if c=="_" else 50))
    elif c in ".,·:;…‥•◦‣":
        xs = [20,50,80] if c=="…" else [30,70] if c=="‥" else [50]
        ys = [36,84] if c in ":;" else [52] if c in "·•◦‣" else [88]
        for x in xs:
            for y in ys:
                if c=="◦": d.oval(x,y,5.5,5.5)
                else: d.dot(x,y,DOT_DIAMETER/2)
        if c in ",;": d.poly((51,88),(44,103))
        if c=="‣":
            d = Drawing().poly((31,25),(72,52),(30,79),close=True)
    elif c in "+±=≠≤≥<>×÷❌":
        if c in "×❌":
            d.poly((21,24),(80,81)).poly((79,22),(20,83))
        elif c in "<≤>≥":
            sign = 1 if c in "<≤" else -1
            d.poly((50+sign*28,20),(50-sign*28,51),(50+sign*28,79))
            if c in "≤≥": d.poly((19,97),(81,96))
        else:
            d.poly((13,50),(87,48))
            if c in "+±": d.poly((51,14),(50,85 if c=="+" else 76))
            if c in "=≠":
                d = Drawing().poly((14,36),(86,34)).poly((14,69),(86,67))
            if c=="±": d.poly((14,96),(86,94))
            if c=="≠": d.poly((74,8),(28,97))
            if c=="÷": d.dot(50,17).dot(49,82)
    elif c in "#":
        d.poly((38,8),(28,96)).poly((73,7),(63,95))
        d.poly((10,37),(91,35)).poly((7,71),(88,69))
    elif c == "%":
        d.poly((82,9),(18,96)).oval(27,27,15,18).oval(73,78,15,18)
    elif c == "*":
        for a in range(5):
            t=math.radians(a*72-90)
            d.poly((50,48),(50+36*math.cos(t),48+36*math.sin(t)))
    elif c == "^": d.poly((18,41),(50,12),(82,40))
    elif c == "~":
        d.curve([("M",10,55),("C",37,14,64,86,90,44)])
    elif c == "@":
        d.oval(48,51,22,25)
        d.curve([("M",71,28),("L",69,67),("Q",93,81,94,48),("C",97,-7,0,-6,5,58),("Q",8,112,83,93)])
    elif c == "&":
        d.curve([("M",86,91),("C",20,40,13,30,34,15),("C",67,-9,92,30,55,46),
                 ("C",-11,64,20,123,68,87),("Q",84,74,87,55)])
    elif c in "$＄":
        d.append(latin("S"),(10,6,80,84)).poly((53,1),(48,100))
    elif c in "¥￥₩￦":
        d.append(latin("Y" if c in "¥￥" else "W"),(7,8,86,84))
        d.poly((10,54),(90,52)).poly((10,70),(90,68))
    elif c in "€":
        d.append(latin("C"),(7,3,86,94))
        d.poly((7,43),(69,41)).poly((7,60),(65,58))
    elif c == "￡":
        d.curve([("M",84,22),("C",62,-5,27,10,34,39),("L",39,72),("Q",38,89,18,93),("L",87,91)])
        d.poly((14,54),(70,52))
    elif c in "©®ⒸⓇ":
        d.oval(50,51,43,43)
        d.append(latin("C" if c in "©Ⓒ" else "R"),(25,25,50,53))
    elif c in "™℃℉":
        if c == "™":
            d.append(latin("T"),(1,4,43,46)).append(latin("M"),(49,4,47,46))
        else:
            d.oval(13,15,8,8).append(latin("C" if c=="℃" else "F"),(30,7,67,88))
    elif c == "°": d.oval(49,22,16,16)
    elif c == "¶":
        d.poly((67,11),(65,95)).poly((89,11),(87,95))
        d.curve([("M",88,11),("L",36,12),("C",4,12,4,58,38,58),("L",66,57)])
    elif 0x2190 <= cp <= 0x2199:
        # Define a right-pointing arrow, then rotate, preserving its round caps.
        angle = {0x2190:180,0x2191:-90,0x2192:0,0x2193:90,
                 0x2194:0,0x2195:90,0x2196:-135,0x2197:-45,
                 0x2198:45,0x2199:135}[cp]
        t=math.radians(angle)
        def rot(p):
            x,y=p[0]-50,p[1]-50
            return (50+x*math.cos(t)-y*math.sin(t),50+x*math.sin(t)+y*math.cos(t))
        d.poly(*map(rot,[(9,50),(91,50)]))
        d.poly(*map(rot,[(66,25),(92,50),(66,75)]))
        if cp in (0x2194,0x2195): d.poly(*map(rot,[(34,25),(8,50),(34,75)]))
    elif c in "■□▪◇○":
        if c == "○": d.oval(50,51,39,39)
        elif c=="◇": d.poly((50,9),(92,51),(50,94),(8,52),close=True,smooth=4)
        else:
            b = 30 if c=="▪" else 12
            if c in "■▪":
                d.curve([("M",b,b),("L",100-b,b),("L",100-b,100-b),("L",b,100-b),("Z",)],fill=True)
            else: d.poly((b,b),(100-b,b),(100-b,100-b),(b,100-b),close=True,smooth=5)
    elif c in "★☆":
        pts=[]
        for i in range(10):
            t=math.radians(i*36-90); r=44 if i%2==0 else 20
            pts.append((50+r*math.cos(t),52+r*math.sin(t)))
        if c=="★": d.curve([("M",*pts[0])]+[("L",*p) for p in pts[1:]]+[("Z",)],fill=True)
        else: d.poly(*pts,close=True,smooth=4)
    elif c in "♡♥":
        d.curve([("M",50,91),("C",-11,54,5,2,40,21),("Q",48,25,50,31),
                 ("C",72,-8,117,26,86,61),("Q",72,78,50,91),("Z",)],fill=c=="♥")
    elif c == "※":
        d.poly((22,24),(79,82)).poly((79,23),(21,83))
        for x,y in [(50,12),(9,53),(91,52),(49,96)]: d.dot(x,y)
    else:
        raise ValueError(f"Missing symbol drawing U+{cp:04X} {c}")
    if c in "¡¿":
        reflected = Drawing()
        for item in d.items:
            if item[0]=="dot":
                _,x,y,r=item
                reflected.dot(100-x,105-y,r)
            elif item[0]=="poly":
                _,pts,cl,sm=item
                reflected.poly(*[(100-x,105-y) for x,y in pts],close=cl,smooth=sm)
            else:
                _,cmds,fill=item
                reflected.curve([(op,*[100-v if i%2==0 else 105-v for i,v in enumerate(vals)])
                                 for op,*vals in cmds],fill=fill)
        d=reflected
    return d


def tt_glyph(path):
    pen=TTGlyphPen(None)
    if len(path): path.draw(Cu2QuPen(pen, max_err=.6, all_quadratic=True))
    g=pen.glyph()
    if g.numberOfContours > 0:
        g.recalcBounds(None)
    return g


def reference_manifest(reference):
    f=TTFont(reference)
    unicode_cps = sorted({cp for sub in f["cmap"].tables if sub.isUnicode()
                          and sub.format!=14 for cp in sub.cmap})
    data={"reference_family":f["name"].getDebugName(16),
          "reference_character_count":len(unicode_cps),
          "reference_hangul_count":sum(0xAC00<=cp<=0xD7A3 for cp in unicode_cps),
          "reference_styles":[f["name"].getDebugName(2)],
          "reference_has_variation_axes":"fvar" in f,
          "reference_has_unicode_variation_sequences":any(t.format==14 for t in f["cmap"].tables),
          "codepoints":unicode_cps}
    f.close()
    return data


def build(reference=None):
    OUT.mkdir(parents=True,exist_ok=True)
    manifest_path=SOURCE / "reference_coverage.json"
    if reference:
        manifest=reference_manifest(reference)
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    else:
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    codepoints=set(manifest["codepoints"]) | set(range(0xAC00,0xD7A4))
    codepoints |= set(range(0x1100,0x1113)) | set(range(0x1161,0x1176)) | set(range(0x11A8,0x11C3))
    codepoints |= {0x2000,0x2001,0x2008,0x200B,0x202F,0x205F,0x3000,0x3164,0xFFFD}
    glyphs={".notdef":tt_glyph(Drawing().poly((15,10),(85,10),(85,90),(15,90),close=True).path((100,60,600,700)))}
    metrics={".notdef":(800,0)}
    cmap={}
    component_cache={}
    component_paths={}
    component_probes={}
    pair_gaps=[]

    def add(name,path,advance):
        # Tighten Latin/digit side bearings after drawing, without scaling ink.
        if name.startswith("uni") and chr(int(name[3:],16)).isascii() and chr(int(name[3:],16)).isalnum():
            left,_,right,_=path.bounds
            ink_width=right-left
            advance=round(advance-(advance-ink_width)*.30)
            offset=round((advance-ink_width)/2-left)
            path=path.transform(1,0,0,1,offset,0)
        g=tt_glyph(path)
        glyphs[name]=g
        metrics[name]=(advance,g.xMin if g.numberOfContours else 0)

    def component(role,index,box,weight):
        x,y,w,h=box
        # Reserve room for the wider pen while retaining the tighter advance.
        box=(460+(x-460)*.98,y,w*.98,h)
        key=(role,index,box,weight)
        if key not in component_cache:
            name=f"_{role}{index}_{len(component_cache)}"
            if role in ("V","VC"):
                path=vowel(MEDIALS[index],compact=role=="VC").path(box)
                probes,gaps=[],[]
            else:
                path,probes,gaps=consonant_outline((INITIALS if role=="L" else FINALS)[index],box,final=role=="T")
            add(name,path,920)
            component_paths[name]=path
            component_probes[name]=probes
            pair_gaps.extend(gaps)
            component_cache[key]=name
        return component_cache[key]

    spaces={0x20:300,0xA0:300,0x2000:500,0x2001:1000,0x2002:500,0x2003:1000,
            0x2004:333,0x2005:250,0x2006:167,0x2007:620,0x2008:300,0x2009:200,
            0x200A:100,0x200B:0,0x202F:200,0x205F:222,0x3000:920,0x3164:920}
    for cp in sorted(codepoints):
        name=f"uni{cp:04X}"
        cmap[cp]=name
        if 0xAC00<=cp<=0xD7A3:
            pen=TTGlyphPen(glyphs)
            for part in hangul_parts(cp):
                pen.addComponent(component(*part),(1,0,0,1,HANGUL_OFFSET_X,0))
            glyphs[name]=pen.glyph()
            metrics[name]=(HANGUL_ADVANCE,0)
        elif cp in spaces:
            add(name,pathops.Path(),spaces[cp])
        elif 0x3131<=cp<=0x3163:
            c=chr(cp)
            path=vowel(c).path((150,100,620,645)) if c in MEDIALS else consonant_outline(c,(150,100,620,645))[0]
            add(name,path.transform(1,0,0,1,HANGUL_OFFSET_X,0),HANGUL_ADVANCE)
        elif 0x1100<=cp<=0x1112 or 0x1161<=cp<=0x1175 or 0x11A8<=cp<=0x11C2:
            c=INITIALS[cp-0x1100] if cp<0x1161 else MEDIALS[cp-0x1161] if cp<0x11A8 else FINALS[cp-0x11A7]
            path=vowel(c).path((150,100,620,645)) if c in MEDIALS else consonant_outline(c,(150,100,620,645))[0]
            add(name,path.transform(1,0,0,1,HANGUL_OFFSET_X,0),HANGUL_ADVANCE)
        elif chr(cp).isascii() and chr(cp).isalnum():
            c=chr(cp)
            advance=450 if c in "Ilijtfr1" else 790 if c in "MWmw" else 650
            add(name,latin(c).path((55,90,advance-110,680)),advance)
        elif cp in GHOST_SLOTS:
            body,eyes=ghost(GHOST_SLOTS[cp])
            path=body.path((55,75,780,700))
            eye_path=eyes.path((55,75,780,700))
            if GHOST_SLOTS[cp]=="solid":
                path=pathops.op(path,eye_path,pathops.PathOp.DIFFERENCE)
            elif GHOST_SLOTS[cp]=="half":
                # Use a clipped solid right half and hollow left half.
                outline=Drawing().curve(body.items[0][1]).path((55,75,780,700))
                clip=Drawing().curve([("M",50,0),("L",110,0),("L",110,110),("L",50,110),("Z",)],fill=True).path((55,75,780,700))
                half=pathops.op(path,clip,pathops.PathOp.INTERSECTION)
                path=pathops.op(outline,half,pathops.PathOp.UNION)
                # Left eye is ink; the right eye is a counter in the solid half.
                left=Drawing().oval(32,41,3.7,5.6,fill=True).path((55,75,780,700))
                right=Drawing().oval(53,39,3.7,5.6,fill=True).path((55,75,780,700))
                path=pathops.op(path,left,pathops.PathOp.UNION)
                path=pathops.op(path,right,pathops.PathOp.DIFFERENCE)
            else:
                path=pathops.op(path,eye_path,pathops.PathOp.UNION)
            path.simplify(clockwise=True)
            path.convertConicsToQuads(.15)
            add(name,path,920)
        elif 0xFB00<=cp<=0xFB04:
            word={0xFB00:"ff",0xFB01:"fi",0xFB02:"fl",0xFB03:"ffi",0xFB04:"ffl"}[cp]
            d=Drawing()
            for i,c in enumerate(word): d.append(latin(c),(i*34,0,35,100))
            add(name,d.path((45,90,390*len(word),680)),400*len(word))
        elif cp==0xFFFD:
            d=Drawing().poly((50,4),(96,50),(50,97),(4,50),close=True,smooth=4)
            d.append(symbol(ord("?")),(30,20,40,60))
            add(name,d.path((45,60,750,750)),850)
        else:
            wide=cp in (0x2E3A,0x2E3B)
            adv=1500 if cp==0x2E3A else 2100 if cp==0x2E3B else 950 if chr(cp) in "＄￡￥￦" else 720
            if chr(cp) in "!.,:;'’‘′`|·": adv=360
            add(name,symbol(cp).path((50,90,adv-100,680)),adv)

    assert STROKE_WIDTHS_USED == {STROKE_WIDTH},STROKE_WIDTHS_USED
    layout_report=verify_hangul_design(glyphs,component_paths,component_cache,component_probes,pair_gaps)
    fb=FontBuilder(EM,isTTF=True)
    fb.setupGlyphOrder(list(glyphs))
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    # Composite bearings must match their computed contours (not an arbitrary 0).
    for name,g in glyphs.items():
        if g.isComposite():
            g.recalcBounds(fb.font["glyf"])
            metrics[name]=(metrics[name][0],g.xMin)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=1000,descent=-260,lineGap=60)
    fb.setupNameTable({"familyName":FAMILY,"styleName":"Regular",
                       "uniqueFontIdentifier":"GhostyRoundGhost-Regular-"+VERSION,
                       "fullName":FAMILY+" Regular","psName":"GhostyRoundGhost-Regular",
                       "version":"Version "+VERSION,"typographicFamily":FAMILY,
                       "typographicSubfamily":"Regular",
                       "copyright":"Released into the public domain under The Unlicense.",
                       "description":"Original rounded handwriting. Full modern Hangul and six ghost ornaments. No reference font outlines included.",
                       "licenseDescription":"The Unlicense. No attribution required. Use, modification, redistribution and sale are permitted. See LICENSE.",
                       "licenseInfoURL":"https://unlicense.org/"})
    for name_id,value in [(1,KOREAN_FAMILY),(2,"보통"),(4,KOREAN_FAMILY),(16,KOREAN_FAMILY),(17,"보통")]:
        fb.font["name"].setName(value,name_id,3,1,0x412)
    fb.setupOS2(version=4,sTypoAscender=1000,sTypoDescender=-260,sTypoLineGap=60,
                usWinAscent=1000,usWinDescent=260,usWeightClass=400,
                usWidthClass=5,fsType=0,fsSelection=0xC0,sxHeight=420,sCapHeight=650,
                achVendID="GHST")
    fb.setupPost(keepGlyphNames=True)
    fb.setupMaxp()
    fb.font["head"].fontRevision=float(VERSION)
    fb.font["head"].created=fb.font["head"].modified=3877718400
    fb.font.recalcTimestamp=False
    gasp=newTable("gasp")
    gasp.gaspRange={65535:2}
    fb.font["gasp"]=gasp
    target=OUT / "GhostyRoundGhost-Regular.ttf"
    fb.save(target)
    (SOURCE/"readability.json").write_text(json.dumps(layout_report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {target}: {len(cmap):,} encoded characters, {len(glyphs):,} glyphs")
    return target,manifest


def consonant_probes(letter):
    """White-space samples inside the channels/counters most likely to clog."""
    return {"ㄹ":[(50,31),(50,67)],"ㅌ":[(50,31),(50,67)],
            "ㅂ":[(50,68)],"ㅁ":[(50,50)],"ㅇ":[(50,51)],
            "ㅎ":[(50,75)],"ㅍ":[(50,50)]}.get(letter,[])


def verify_hangul_design(glyphs,paths,cache,probes,pair_gaps):
    blocked=[]
    probe_count=0
    for (role,index,box,weight),name in cache.items():
        if role not in ("L","T"): continue
        letter=(INITIALS if role=="L" else FINALS)[index]
        assert weight == STROKE_WIDTH,(role,letter,weight)
        for x,y in probes[name]:
            probe_count+=1
            if paths[name].contains((x,y)):
                blocked.append((role,letter,box,x,y))
    assert not blocked,("Blocked Hangul counters",blocked[:10])
    checked=set()
    overlaps=[]
    for cp in range(0xAC00,0xD7A4):
        components=[c.glyphName for c in glyphs[f"uni{cp:04X}"].components]
        for i,a in enumerate(components):
            for b in components[i+1:]:
                pair=tuple(sorted((a,b)))
                if pair in checked: continue
                checked.add(pair)
                pa,pb=paths[a],paths[b]
                ax,ay,ar,ab=pa.bounds;bx,by,br,bb=pb.bounds
                if ax>=br or bx>=ar or ay>=bb or by>=ab: continue
                area=pathops.op(pa,pb,pathops.PathOp.INTERSECTION).area
                if area>1:
                    overlaps.append((chr(cp),a,b,round(area,2)))
    assert not overlaps,("Touching Hangul components",overlaps[:20],len(overlaps))
    assert all(abs(gap-PAIR_GAP)<.05 for gap in pair_gaps),pair_gaps
    return {"version":VERSION,"syllables_checked":11172,
            "stroke_width_units":STROKE_WIDTH,"emitted_stroke_widths":sorted(STROKE_WIDTHS_USED),
            "paired_consonant_gap_units":PAIR_GAP,
            "paired_gap_min":min(pair_gaps),"paired_gap_max":max(pair_gaps),
            "unique_component_pairs_checked":len(checked),"component_overlaps":overlaps,
            "counter_probes_checked":probe_count,"blocked_counter_probes":blocked,
            "focus_characters":"갋 값 밟 넓 짧 닭 읽 삶 앉 많 싫 흙"}


def verify(target,manifest):
    import uharfbuzz as hb
    from PIL import ImageFont
    f=TTFont(target,checkChecksums=2)
    assert f["OS/2"].fsType == 0,"Font embedding must be unrestricted"
    assert f["name"].getDebugName(14) == "https://unlicense.org/"
    assert "Unlicense" in f["name"].getDebugName(13)
    cmap=f.getBestCmap()
    # Optically larger dots stay distinct, including in Latin ligatures.
    dot_counts={".":1,"·":1,":":2,"‥":2,"…":3,"!":1,"?":1,
                "¡":1,"¿":1,"i":1,"j":1,"÷":2,"※":4,"ﬁ":1,"ﬃ":1}
    for character,expected in dot_counts.items():
        g=f["glyf"][cmap[ord(character)]]
        coordinates,endpoints,_=g.getCoordinates(f["glyf"])
        start,count=0,0
        for end in endpoints:
            contour=coordinates[start:end+1]
            xs,ys=zip(*contour)
            if abs(max(xs)-min(xs)-DOT_DIAMETER)<=1 and abs(max(ys)-min(ys)-DOT_DIAMETER)<=1:
                count+=1
            start=end+1
        assert count==expected,(character,"optically sized dots",count,expected)
    missing=sorted(set(manifest["codepoints"])-set(cmap))
    assert not missing,missing
    assert all(cp in cmap for cp in range(0xAC00,0xD7A4))
    spaces={cp for cp in cmap if chr(cp).isspace()} | {0x200B,0x3164}
    empty=[cp for cp,n in cmap.items() if cp not in spaces and not f["glyf"][n].numberOfContours]
    assert not empty,empty
    bounds=[]
    for cp,n in cmap.items():
        g=f["glyf"][n]
        if not g.numberOfContours: continue
        adv,lsb=f["hmtx"][n]
        assert lsb==g.xMin,(hex(cp),"lsb")
        assert g.xMin>=0 and g.xMax<=adv,(hex(cp),"sidebearing",g.xMin,g.xMax,adv)
        assert -260<=g.yMin and g.yMax<=1000,(hex(cp),"vertical",g.yMin,g.yMax)
        bounds.append((g.yMin,g.yMax))
    hb_font=hb.Font(hb.Face(target.read_bytes()))
    shaping=[]
    for text in ["안녕! 고스티 동글유령체", "꽃 빛 꿈 별 꼬리 불꽃", "똠 쀍 뷁 힣", "고스티", "ABC xyz 0123456789", "♤ ♧ † ‡ £ ¢"]:
        buf=hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
        hb.shape(hb_font,buf)
        ids=[g.codepoint for g in buf.glyph_infos]
        assert all(ids),(text,ids)
        shaping.append({"text":text,"glyph_count":len(ids),"missing":0})
    # Check every precomposed syllable and its NFD spelling shape identically.
    import unicodedata
    nfd_mismatches=[]
    for cp in range(0xAC00,0xD7A4):
        text=chr(cp)
        def shape_ids(s):
            buf=hb.Buffer();buf.add_str(s);buf.guess_segment_properties();hb.shape(hb_font,buf)
            return [g.codepoint for g in buf.glyph_infos]
        if shape_ids(text)!=shape_ids(unicodedata.normalize("NFD",text)):
            nfd_mismatches.append(cp)
    assert not nfd_mismatches,nfd_mismatches[:10]
    # FreeType must rasterize every nonblank character with grayscale coverage.
    raster_font=ImageFont.truetype(str(target),24)
    empty_rasters=[cp for cp in cmap if cp not in spaces
                   and raster_font.getmask(chr(cp),mode="L").getbbox() is None]
    assert not empty_rasters,empty_rasters
    report={"font":target.name,"family":KOREAN_FAMILY,"version":VERSION,
            "license":"Unlicense","embedding_restrictions":0,
            "standard_dot_diameter":DOT_DIAMETER,"dot_glyphs_checked":len(dot_counts),
            "reference_characters":manifest["reference_character_count"],
            "reference_coverage_missing":missing,
            "encoded_characters":len(cmap),"modern_hangul_syllables":11172,
            "hangul_nfd_equivalence_checked":11172,"hangul_nfd_mismatches":len(nfd_mismatches),
            "blank_nonspace_characters":empty,"glyphs":f["maxp"].numGlyphs,
            "native_raster_size":24,"native_raster_blank_characters":empty_rasters,
            "rendering":"grayscale antialiasing; scalable rounded outlines",
            "minimum_y":min(a for a,b in bounds),"maximum_y":max(b for a,b in bounds),
            "ghost_ornaments":{f"U+{cp:04X}":kind for cp,kind in GHOST_SLOTS.items()},
            "styles":["Regular"],"variable_axes":[],"shaping_samples":shaping}
    (SOURCE/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,help="Read reference Unicode coverage only")
    args=parser.parse_args()
    target,manifest=build(args.reference)
    verify(target,manifest)

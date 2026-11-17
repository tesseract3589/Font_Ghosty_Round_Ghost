# SPDX-License-Identifier: Unlicense
"""Run with python -m unittest discover -s tests -v; no Godot required."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import build_ghosty_font as builder
from preview_ghosty_font import specimen
import preview_ghosty_font as previews
from PIL import ImageFont


class FontTests(unittest.TestCase):
    def test_coverage_shaping_dots_metrics_and_license(self):
        manifest=json.loads((builder.SOURCE/"reference_coverage.json").read_text(encoding="utf-8"))
        with contextlib.redirect_stdout(io.StringIO()):
            builder.verify(ROOT/"GhostyRoundGhost-Regular.ttf",manifest)

    def test_preview_outputs_are_exactly_the_five_distribution_images(self):
        old_out=previews.OUT
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)
            (destination/"GhostyRoundGhost-Regular.ttf").write_bytes((ROOT/"GhostyRoundGhost-Regular.ttf").read_bytes())
            try:
                previews.OUT=destination
                with contextlib.redirect_stdout(io.StringIO()):
                    previews.main()
                self.assertEqual({p.name for p in (destination/"preview").iterdir()},set(previews.PREVIEW_FILES))
            finally:
                previews.OUT=old_out

    def test_vowel_stems_in_final_syllables(self):
        font=builder.TTFont(ROOT/"GhostyRoundGhost-Regular.ttf")
        cmap=font.getBestCmap()
        for character in "곡국눈붑옹숭숯굑균":
            syllable=font["glyf"][cmap[ord(character)]]
            medial=font["glyf"][syllable.components[1].glyphName]
            self.assertGreaterEqual(medial.yMax-medial.yMin,210,character)

    def test_rebuild_geometry_and_metrics(self):
        old_out,old_source=builder.OUT,builder.SOURCE
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)
            (temporary/"reference_coverage.json").write_bytes((old_source/"reference_coverage.json").read_bytes())
            try:
                builder.OUT=temporary
                builder.SOURCE=temporary
                with contextlib.redirect_stdout(io.StringIO()):
                    rebuilt,_=builder.build()
                original=builder.TTFont(ROOT/"GhostyRoundGhost-Regular.ttf")
                generated=builder.TTFont(rebuilt)
                for table in ("glyf","hmtx","cmap"):
                    self.assertEqual(original.getTableData(table),generated.getTableData(table),table)
            finally:
                builder.OUT, builder.SOURCE=old_out,old_source

    def test_small_sizes_and_independent_previews(self):
        for size in (16,20,24,32,48):
            font=ImageFont.truetype(str(ROOT/"GhostyRoundGhost-Regular.ttf"),size)
            for text in ("갋 값 밟 넓 짧 읽 삶 흙", "곡 국 눈 붑 옹 숭 숯", ". · : ; ‥ … ! ? i j", "고스티 동글유령체"):
                self.assertIsNotNone(font.getmask(text,mode="L").getbbox(),(size,text))
        with tempfile.TemporaryDirectory() as directory:
            first=specimen(Path(directory)/"small.png",1)
            second=specimen(Path(directory)/"large.png",2)
            self.assertEqual(first.size,(640,480))
            self.assertEqual(second.size,(1280,960))
            self.assertGreater(len(first.getcolors(640*480)),16)
            self.assertNotEqual(first.resize(second.size,resample=0).tobytes(),second.tobytes())


if __name__=="__main__":
    unittest.main()

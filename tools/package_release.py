# SPDX-License-Identifier: Unlicense
"""Package the font, license, README, and exactly five preview images."""
import argparse
from decimal import Decimal
from pathlib import Path
import zipfile

from build_ghosty_font import ROOT, VERSION
from preview_ghosty_font import PREVIEW_FILES


def package(version):
    if Decimal(version)!=Decimal(VERSION):
        raise ValueError("Release version must match the TTF version")
    if any(c not in "0123456789." for c in version):
        raise ValueError("Use a numeric version, such as 1.7")
    images={p.name for p in (ROOT/"preview").iterdir() if p.is_file()}
    if images!=set(PREVIEW_FILES):
        raise ValueError("preview/ must contain exactly the five canonical images")
    names=["GhostyRoundGhost-Regular.ttf","LICENSE","README.md"]
    names += ["preview/"+name for name in PREVIEW_FILES]
    for name in names:
        if not (ROOT/name).is_file():raise FileNotFoundError(name)
    destination=ROOT/"dist"/f"GhostyRoundGhost-v{version}.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names:archive.write(ROOT/name,name)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())==set(names)
    return destination


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version",default=str(Decimal(VERSION).normalize()))
    print(package(parser.parse_args().version))

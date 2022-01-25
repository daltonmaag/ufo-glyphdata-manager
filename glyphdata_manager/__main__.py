# pyright: strict

"""Extract and apply global glyph data of UFOs to and from a CSV file."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from ufoLib2 import Font


@dataclass
class GlyphData:
    export: bool
    opentype_category: str | None
    postscript_name: str | None
    unicodes: list[int]


def extract_from_ufos(ufos: list[Font]) -> dict[str, GlyphData]:
    glyph_data: dict[str, GlyphData] = {}
    for ufo in ufos:
        psn: dict[str, str] = ufo.lib.get("public.postscriptNames", {})
        otc: dict[str, str] = ufo.lib.get("public.openTypeCategories", {})
        seg: list[str] = ufo.lib.get("public.skipExportGlyphs", [])

        # Visit in glyph order, append unlisted glyphs sorted.
        glyph_order = ufo.glyphOrder
        glyph_order_leftovers = sorted(set(ufo.keys()) - set(glyph_order))

        for glyph_name in glyph_order + glyph_order_leftovers:
            glyph = ufo.get(glyph_name)
            if glyph is None:
                continue  # Listed glyphs may not exist.
            data = GlyphData(
                export=glyph.name not in seg,
                opentype_category=otc.get(glyph_name),
                postscript_name=psn.get(glyph_name),
                unicodes=glyph.unicodes,
            )
            if glyph_name in glyph_data:
                if glyph_data[glyph_name] != data:
                    logging.warning(
                        "data mismatch for glyph '%s', have %s, found %s in %s",
                        glyph_name,
                        glyph_data[glyph_name],
                        data,
                        ufo._path,
                    )
            else:
                glyph_data[glyph_name] = data

    return glyph_data


def write_csv(path: Path, glyph_data: dict[str, GlyphData]) -> None:
    header = ("name", "postscript_name", "unicodes", "opentype_category", "export")
    with open(path, "w+") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(header)
        for glyph, data in glyph_data.items():
            csvwriter.writerow(
                (
                    glyph,
                    data.postscript_name or "",
                    " ".join(f"{v:04X}" for v in data.unicodes),
                    data.opentype_category or "",
                    data.export,
                )
            )


def extract_data(args: argparse.Namespace) -> None:
    glyph_data = extract_from_ufos(args.ufos)
    write_csv(args.output, glyph_data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    parser_extract = subparsers.add_parser("extract")
    parser_extract.add_argument("ufos", nargs="+", type=Font.open)
    parser_extract.add_argument("output", type=Path)
    # parser_extract.add_argument("--remove-from-ufo", action="store_true")
    # parser_extract.add_argument("--glyph-list", type=Path)
    parser_extract.set_defaults(func=extract_data)

    # parser_apply = subparsers.add_parser("apply")
    # parser_apply.add_argument("csv", type=Path)
    # parser_apply.add_argument("ufos", nargs="+", type=Font.open)
    # parser_extract.set_defaults(func=None)

    parsed_args = parser.parse_args()
    parsed_args.func(parsed_args)

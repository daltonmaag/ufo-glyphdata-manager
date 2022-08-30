# pyright: strict

"""Extract and apply global glyph data of UFOs to and from a CSV file."""

from __future__ import annotations

import csv
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from ufoLib2 import Font

HEADER: tuple[str, ...] = (
    "name",
    "postscript_name",
    "unicodes",
    "opentype_category",
    "export",
)


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


# TODO: rewrite glyphOrder
def apply_to_ufos(ufos: list[Font], glyph_data: dict[str, GlyphData]) -> None:
    psn: dict[str, str] = {}
    otc: dict[str, str] = {}
    seg: list[str] = []
    for glyph_name, data in glyph_data.items():
        if data.postscript_name is not None:
            psn[glyph_name] = data.postscript_name
        if data.opentype_category is not None:
            otc[glyph_name] = data.opentype_category
        if not data.export:
            seg.append(glyph_name)

    for ufo in ufos:
        ufo_psn: dict[str, str] = ufo.lib.get("public.postscriptNames", {})
        ufo_otc: dict[str, str] = ufo.lib.get("public.openTypeCategories", {})
        ufo_seg: set[str] = set(ufo.lib.get("public.skipExportGlyphs", []))

        ufo_psn.update(psn)
        ufo_otc.update(otc)
        ufo_seg.update(seg)

        ufo.lib["public.postscriptNames"] = ufo_psn
        ufo.lib["public.openTypeCategories"] = ufo_otc
        ufo.lib["public.skipExportGlyphs"] = sorted(ufo_seg)

        # Delete empty dicts and lists.
        if not ufo.lib["public.postscriptNames"]:
            del ufo.lib["public.postscriptNames"]
        if not ufo.lib["public.openTypeCategories"]:
            del ufo.lib["public.openTypeCategories"]
        if not ufo.lib["public.skipExportGlyphs"]:
            del ufo.lib["public.skipExportGlyphs"]

        ufo.save()


def read_csv(path: Path) -> dict[str, GlyphData]:
    glyph_data: dict[str, GlyphData] = {}
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        if tuple(header) != HEADER:
            raise Exception("Header in CSV file does not match internally known header")
        for row in reader:
            if not row:
                continue
            name, postscript_name, unicodes, opentype_category, export = row
            glyph_data[name] = GlyphData(
                export=True if export.lower() == "true" else False,
                opentype_category=opentype_category or None,
                postscript_name=postscript_name or None,
                unicodes=[int(v, 16) for v in unicodes.split(" ")] if unicodes else [],
            )
    return glyph_data


def write_csv(path: Path | None, glyph_data: dict[str, GlyphData]) -> None:
    if path is not None:
        output_stream = open(path, "w", newline="", encoding="utf-8")
    else:
        output_stream = sys.stdout

    writer = csv.writer(output_stream)
    writer.writerow(HEADER)
    writer.writerows(
        (
            glyph,
            data.postscript_name or "",
            " ".join(f"{v:04X}" for v in data.unicodes),
            data.opentype_category or "",
            data.export,
        )
        for glyph, data in glyph_data.items()
    )

    if output_stream is not sys.stdout:
        output_stream.close()


def extract_data(args: argparse.Namespace) -> None:
    glyph_data = extract_from_ufos(args.ufos)
    write_csv(args.output, glyph_data)


def apply_data(args: argparse.Namespace) -> None:
    glyph_data = read_csv(args.csv)
    apply_to_ufos(args.ufos, glyph_data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    parser_extract = subparsers.add_parser("extract")
    parser_extract.add_argument("ufos", nargs="+", type=Font.open)
    parser_extract.add_argument(
        "-o",
        "--output",
        type=Path,
        help="File to write data into (default: standard out)",
    )
    # parser_extract.add_argument("--remove-from-ufo", action="store_true")
    # parser_extract.add_argument("--glyph-list", type=Path)
    parser_extract.set_defaults(func=extract_data)

    parser_apply = subparsers.add_parser("apply")
    parser_apply.add_argument("csv", type=Path)
    parser_apply.add_argument("ufos", nargs="+", type=Font.open)
    parser_apply.set_defaults(func=apply_data)

    parsed_args = parser.parse_args()
    parsed_args.func(parsed_args)

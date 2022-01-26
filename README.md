# Glyph Data Manager

Store your family-wide glyph data in a central CSV file instead of duplicated in every UFO.

## Todo

- Convert between Glyphs.app GlyphData.xml and CSV
    - Decide on subset of data to convert
- Remove data from UFOs after extraction into CSVs
- Optionally store kerning group information
- Add arguments on which pieces of data (columns) to write?
- Custom fields for custom purposes, like subsets?
- Interaction between encoding and CSV file?
    - Maybe always sort CSV by glyph name and encode encoding into "order"
      column, filling up gaps in public.GlyphOrder with made up glyph12345 names

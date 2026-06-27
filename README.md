# wiki-hs-parser

Small CLI utility for Hearthstone Wiki pages, demonstrated with `C'Thun`.

It extracts from the `C'Thun` page:

- all card art variants shown in the infobox
- direct image URLs for each art variant
- downloaded image files for each art variant
- `Patch changes` from the page

## Requirements

- Python 3.13+
- `lxml`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python wiki_hs_parser.py --page "https://hearthstone.wiki.gg/wiki/C%27Thun" --output-dir out/c-thun
```

That command uses `C'Thun` as the example page and writes:

- `out/c-thun/result.json`
- `out/c-thun/patch-changes.md`
- `out/c-thun/arts/*`

## Notes

- The script uses the public MediaWiki API on `hearthstone.wiki.gg`.
- The `C'Thun` page is a good sanity check because it includes regular, golden, and signature art variants.
- Art variants are resolved from the page's infobox, so regular, golden, signature, and other displayed variants are included when present.

# wiki-hs-parser

Small CLI utility for Hearthstone Wiki pages.

It extracts:

- all card art variants shown on the page infobox
- direct image URLs for each art variant
- downloaded image files
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

Outputs:

- `out/c-thun/result.json`
- `out/c-thun/patch-changes.md`
- `out/c-thun/arts/*`

## Notes

- The script uses the public MediaWiki API on `hearthstone.wiki.gg`.
- Art variants are resolved from the page's infobox, so regular, golden, signature, and other displayed variants are included when present.

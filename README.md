# wiki-hs-parser

Small CLI utility for Hearthstone Wiki pages, demonstrated with `C'Thun` and `Mountain Map`.

It extracts from the `C'Thun` page:

- the full infobox card data
- all card art variants shown in the infobox
- direct image URLs for each art variant
- downloaded image files for each art variant
- related cards grouped by section
- `Patch changes` from the page

It also extracts from pages like `Mountain Map`:

- the full infobox card data
- generated card pool links from `Generated cards`
- the cards returned by each `Special:RunQuery/WikiCardPool` page

## Requirements

- Python 3.13+
- `lxml`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

`C'Thun` example:

```bash
python wiki_hs_parser.py --page "https://hearthstone.wiki.gg/wiki/C%27Thun" --output-dir out/c-thun
```

`Mountain Map` example:

```bash
python wiki_hs_parser.py --page "https://hearthstone.wiki.gg/wiki/Mountain_Map" --output-dir out/mountain-map
```

Each run writes:

- `out/c-thun/result.json`
- `out/c-thun/result.md`
- `out/c-thun/patch-changes.md`
- `out/c-thun/arts/*`
- `out/mountain-map/result.json`
- `out/mountain-map/result.md`
- `out/mountain-map/patch-changes.md`
- `out/mountain-map/arts/*`

## Notes

- The script uses the public MediaWiki API on `hearthstone.wiki.gg`.
- The `C'Thun` page is a good sanity check because it includes regular, golden, and signature art variants.
- `Mountain Map` is a good sanity check for generated card pools because it exposes a `Special:RunQuery/WikiCardPool` link.
- Art variants are resolved from the page's infobox, so regular, golden, signature, and other displayed variants are included when present.

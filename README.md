# wiki-hs-parser

Small CLI utility for Hearthstone Wiki pages, demonstrated with `C'Thun` and `Mountain Map`.

It extracts:

- the full infobox card data
- all art variants shown in the infobox
- direct image URLs for each art variant
- downloaded image files for each art variant
- related cards grouped by section
- generated card pools and the cards returned by each `Special:RunQuery/WikiCardPool` page
- `Patch changes` from the page

`related_cards` and `generated_cards` store `card_code` values such as `OG_281` and `CORE_ULD_723`.

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

- `out/<slug>/result.json`
- `out/<slug>/result.md`
- `out/<slug>/patch-changes.md`
- `out/<slug>/arts/*`

## What You Get

The JSON output contains these top-level keys:

- `page_title`
- `page_url`
- `infobox_fields`
- `arts`
- `related_cards`
- `generated_cards`
- `patch_changes`

Example card data for `C'Thun`:

| Field | Value |
| --- | --- |
| Name | `C'Thun` |
| Card id | `OG_280` |
| dbfId | `38857` |
| Cost | `8` |
| Attack | `6` |
| Health | `6` |
| Card set | `Whispers of the Old Gods` |
| Rarity | `Legendary` |
| Text | `Battlecry: Deal damage equal to this minion's Attack randomly split among all enemies.` |

## C'Thun Arts

| Variant | Preview | File |
| --- | --- | --- |
| Regular | <img src="https://hearthstone.wiki.gg/images/OG_280.png?65d054" alt="C'Thun regular art" width="150" /> | `https://hearthstone.wiki.gg/images/OG_280.png?65d054` |
| Golden | <img src="https://hearthstone.wiki.gg/images/OG_280_Premium1.png?98bc25" alt="C'Thun golden art" width="150" /> | `https://hearthstone.wiki.gg/images/OG_280_Premium1.png?98bc25` |
| Signature | <img src="https://hearthstone.wiki.gg/images/OG_280_Premium3.png?ca6651" alt="C'Thun signature art" width="150" /> | `https://hearthstone.wiki.gg/images/OG_280_Premium3.png?ca6651` |

## C'Thun Related Cards

`Cards that improve C'Thun`

| Card code | Card | Preview |
| --- | --- | --- |
| `OG_281` | Beckoner of Evil | <img src="https://hearthstone.wiki.gg/images/thumb/OG_281.png/235px-OG_281.png?d5f49a" alt="Beckoner of Evil" width="120" /> |
| `OG_303` | Cult Sorcerer | <img src="https://hearthstone.wiki.gg/images/thumb/OG_303.png/235px-OG_303.png?41c8c8" alt="Cult Sorcerer" width="120" /> |
| `OG_284` | Twilight Geomancer | <img src="https://hearthstone.wiki.gg/images/thumb/OG_284.png/235px-OG_284.png?bda504" alt="Twilight Geomancer" width="120" /> |
| `OG_162` | Disciple of C'Thun | <img src="https://hearthstone.wiki.gg/images/thumb/OG_162.png/235px-OG_162.png?f2e382" alt="Disciple of C'Thun" width="120" /> |
| `OG_286` | Twilight Elder | <img src="https://hearthstone.wiki.gg/images/thumb/OG_286.png/235px-OG_286.png?254686" alt="Twilight Elder" width="120" /> |
| `OG_283` | C'Thun's Chosen | <img src="https://hearthstone.wiki.gg/images/thumb/OG_283.png/235px-OG_283.png?a9a82b" alt="C'Thun's Chosen" width="120" /> |
| `OG_321` | Crazed Worshipper | <img src="https://hearthstone.wiki.gg/images/thumb/OG_321.png/235px-OG_321.png?829e46" alt="Crazed Worshipper" width="120" /> |
| `OG_334` | Hooded Acolyte | <img src="https://hearthstone.wiki.gg/images/thumb/OG_334.png/235px-OG_334.png?dbf5e7" alt="Hooded Acolyte" width="120" /> |
| `OG_302` | Usher of Souls | <img src="https://hearthstone.wiki.gg/images/thumb/OG_302.png/235px-OG_302.png?4f1a43" alt="Usher of Souls" width="120" /> |
| `OG_293` | Dark Arakkoa | <img src="https://hearthstone.wiki.gg/images/thumb/OG_293.png/235px-OG_293.png?13be3f" alt="Dark Arakkoa" width="120" /> |
| `OG_339` | Skeram Cultist | <img src="https://hearthstone.wiki.gg/images/thumb/OG_339.png/235px-OG_339.png?cadcd7" alt="Skeram Cultist" width="120" /> |
| `OG_282` | Blade of C'Thun | <img src="https://hearthstone.wiki.gg/images/thumb/OG_282.png/235px-OG_282.png?a08602" alt="Blade of C'Thun" width="120" /> |
| `OG_255` | Doomcaller | <img src="https://hearthstone.wiki.gg/images/thumb/OG_255.png/235px-OG_255.png?a7123c" alt="Doomcaller" width="120" /> |

`Cards with C'Thun-related conditions`

| Card code | Card | Preview |
| --- | --- | --- |
| `WON_144` | Eyestalk of C'Thun | <img src="https://hearthstone.wiki.gg/images/thumb/WON_144.png/235px-WON_144.png?32397b" alt="Eyestalk of C'Thun" width="120" /> |
| `OG_188` | Klaxxi Amber-Weaver | <img src="https://hearthstone.wiki.gg/images/thumb/OG_188.png/235px-OG_188.png?6887d5" alt="Klaxxi Amber-Weaver" width="120" /> |
| `OG_096` | Twilight Darkmender | <img src="https://hearthstone.wiki.gg/images/thumb/OG_096.png/235px-OG_096.png?b16a94" alt="Twilight Darkmender" width="120" /> |
| `OG_301` | Ancient Shieldbearer | <img src="https://hearthstone.wiki.gg/images/thumb/OG_301.png/235px-OG_301.png?22bb2d" alt="Ancient Shieldbearer" width="120" /> |
| `OG_131` | Twin Emperor Vek'lor | <img src="https://hearthstone.wiki.gg/images/thumb/OG_131.png/235px-OG_131.png?2cc297" alt="Twin Emperor Vek'lor" width="120" /> |
| `OG_255` | Doomcaller | <img src="https://hearthstone.wiki.gg/images/thumb/OG_255.png/235px-OG_255.png?a7123c" alt="Doomcaller" width="120" /> |

## Mountain Map Generated Cards

`Mountain Map` exposes a `Special:RunQuery/WikiCardPool` link, and the script follows it automatically.

| Card code | Card | Preview |
| --- | --- | --- |
| `CORE_ULD_723` | Murmy (Core) | <img src="https://hearthstone.wiki.gg/images/thumb/CORE_ULD_723.png/235px-CORE_ULD_723.png?8f06b5" alt="Murmy (Core)" width="120" /> |
| `CORE_EX1_012` | Bloodmage Thalnos (Core) | <img src="https://hearthstone.wiki.gg/images/thumb/CORE_EX1_012.png/235px-CORE_EX1_012.png?54369e" alt="Bloodmage Thalnos (Core)" width="120" /> |
| `CORE_EX1_059` | Crazed Alchemist (Core) | <img src="https://hearthstone.wiki.gg/images/thumb/CORE_EX1_059.png/235px-CORE_EX1_059.png?6ff547" alt="Crazed Alchemist (Core)" width="120" /> |
| `CORE_NEW1_020` | Wild Pyromancer (Core) | <img src="https://hearthstone.wiki.gg/images/thumb/CORE_NEW1_020.png/235px-CORE_NEW1_020.png?6ef3b3" alt="Wild Pyromancer (Core)" width="120" /> |
| `END_031` | Shade of the End Time | <img src="https://hearthstone.wiki.gg/images/thumb/END_031.png/235px-END_031.png?866616" alt="Shade of the End Time" width="120" /> |

## Notes

- The script uses the public MediaWiki API on `hearthstone.wiki.gg`.
- `C'Thun` is a good sanity check because it includes regular, golden, and signature art variants.
- `Mountain Map` is a good sanity check for generated card pools because it exposes a `Special:RunQuery/WikiCardPool` link.
- Art variants are resolved from the page's infobox, so regular, golden, signature, and other displayed variants are included when present.

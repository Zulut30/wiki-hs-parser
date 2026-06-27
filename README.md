# wiki-hs-parser

Small CLI utility for Hearthstone Wiki pages, demonstrated with `C'Thun` and `Mountain Map`.

It extracts:

- the full infobox card data
- all art variants shown in the infobox
- direct image URLs for each art variant
- downloaded image files for each art variant
- related cards grouped by section
- generated card pools and the cards returned by each `Special:RunQuery/WikiCardPool` page
- artist, keywords, availability, voice actor, race, dbfId, and card id stats
- sound recordings from the `Sounds` section
- external links from the `External links` section
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
| Artist | `James Ryman` |
| Keywords | `BATTLECRY` |
| Availability | `Default card generation`, `Wild` |
| Voice actor | `Michael Bell` |
| Race | `Old God` |

## C'Thun Arts

The script extracts all three art variants from the infobox.

### Regular

![C'Thun regular art](./assets/readme/cthun-regular.png)

`OG_280`

### Golden

![C'Thun golden art](./assets/readme/cthun-golden.png)

`OG_280`

### Signature

![C'Thun signature art](./assets/readme/cthun-signature.png)

`OG_280`

### Stat Fields

The parser also keeps the smaller infobox stats that appear under the main card block:

- `keywords`: `BATTLECRY`
- `fullTags`: `RARITY=5 CLASS=12 COLLECTIBLE=1 ELITE=1 COST=8 HEALTH=6 ATK=6 CARDTYPE=4 BATTLECRY=1 2165=1 3076=1 1724=1 HAS_SIGNATURE_QUALITY=1 3633=1`
- `custom_mechanicTags`: `Battlecry , Deal damage`
- `custom_refTags`: `Attack-related , Random`
- `derived_exclusions`: `Default card generation`
- `derived_formats`: `Wild`
- `custom_voiceActor`: `Michael Bell`
- `custom_race`: `Old God`
- `dbfId`: `38857`
- `id`: `OG_280`

## C'Thun Related Cards

`Cards that improve C'Thun`

- `OG_281` Beckoner of Evil

  ![Beckoner of Evil](./assets/readme/beckoner-of-evil.png)

- `OG_303` Cult Sorcerer

  ![Cult Sorcerer](./assets/readme/cult-sorcerer.png)

- `OG_284` Twilight Geomancer

  ![Twilight Geomancer](./assets/readme/twilight-geomancer.png)

`Cards with C'Thun-related conditions`

- `WON_144` Eyestalk of C'Thun

  ![Eyestalk of C'Thun](./assets/readme/eyestalk-of-cthun.png)

- `OG_188` Klaxxi Amber-Weaver

  ![Klaxxi Amber-Weaver](./assets/readme/klaxxi-amber-weaver.png)

- `OG_131` Twin Emperor Vek'lor

  ![Twin Emperor Vek'lor](./assets/readme/twin-emperor-veklor.png)

## Mountain Map Generated Cards

`Mountain Map` exposes a `Special:RunQuery/WikiCardPool` link, and the script follows it automatically.

- `CORE_ULD_723` Murmy (Core)

  ![Murmy (Core)](./assets/readme/murmy-core.png)

- `CORE_EX1_012` Bloodmage Thalnos (Core)

  ![Bloodmage Thalnos (Core)](./assets/readme/bloodmage-thalnos-core.png)

- `CORE_NEW1_020` Wild Pyromancer (Core)

  ![Wild Pyromancer (Core)](./assets/readme/wild-pyromancer-core.png)

- `END_031` Shade of the End Time

  ![Shade of the End Time](./assets/readme/shade-of-the-end-time.png)

## C'Thun Sounds

The `Sounds` section is extracted as grouped audio clips:

- `Play`
  - `VO_OG_280_Male_OldGod_Play_01.wav`
  - `CThun_Play_Stinger.wav`
- `Trigger`
  - `VO_OG_280_Male_OldGod_InPlay_01.wav`
  - `VO_OG_280_Male_OldGod_InPlay_02.wav`
- `Attack`
  - `VO_OG_280_Male_OldGod_Attack_01.wav`
- `Death`
  - `VO_OG_280_Male_OldGod_Death_01.wav`

## C'Thun External Links

- [PlayHearthstone](https://hearthstone.blizzard.com/cards/38857)
- [HSReplay.net](https://hsreplay.net/cards/38857)
- [Hearthpwn](https://www.hearthpwn.com/cards/31110)

## Notes

- The script uses the public MediaWiki API on `hearthstone.wiki.gg`.
- `C'Thun` is a good sanity check because it includes regular, golden, and signature art variants.
- `Mountain Map` is a good sanity check for generated card pools because it exposes a `Special:RunQuery/WikiCardPool` link.
- Art variants are resolved from the page's infobox, so regular, golden, signature, and other displayed variants are included when present.

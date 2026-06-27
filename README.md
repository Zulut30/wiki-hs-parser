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
- fast `card_id` / `dbfId` lookup for cards, Battlegrounds minions, and Battlegrounds heroes

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

Fast lookup index:

```bash
python wiki_hs_lookup.py --refresh-index --scope all --index-path out/wiki-card-index.json
```

Fast lookup by normal card id:

```bash
python wiki_hs_lookup.py --id OG_280 --scope card --index-path out/wiki-card-index.json
```

Fast lookup by Battlegrounds minion id:

```bash
python wiki_hs_lookup.py --id BG26_817 --scope bg-minion --index-path out/wiki-card-index.json
```

Fast lookup by Battlegrounds hero id and then parse the found page:

```bash
python wiki_hs_lookup.py --id TB_BaconShop_HERO_29 --scope bg-hero --fetch --no-download --output-dir out/bg-cthun
```

Each run writes:

- `out/<slug>/result.json`
- `out/<slug>/result.md`
- `out/<slug>/patch-changes.md`
- `out/<slug>/arts/*`

`wiki_hs_lookup.py` writes:

- `out/lookup/lookup.json`
- `out/wiki-card-index.json`
- `result.json`, `result.md`, and `patch-changes.md` when `--fetch` is used

## What You Get

The JSON output contains these top-level keys:

- `page_title`
- `page_url`
- `card_data`
- `infobox_fields`
- `arts`
- `related_cards`
- `generated_cards`
- `sounds`
- `external_links`
- `patch_changes`

## Fast Lookup

The lookup script uses the same Cargo data behind these Hearthstone Wiki query pages:

- [Special:RunQuery/Card](https://hearthstone.wiki.gg/wiki/Special:RunQuery/Card)
- [Special:RunQuery/BG/Minion](https://hearthstone.wiki.gg/wiki/Special:RunQuery/BG/Minion)
- [Special:RunQuery/BG/Hero](https://hearthstone.wiki.gg/wiki/Special:RunQuery/BG/Hero)

It builds a local JSON index so an app can resolve a `card_id` or `dbf_id` to a wiki page without scraping search pages every time.

Supported scopes:

- `card`: normal Hearthstone cards from `Special:RunQuery/Card`
- `bg-minion`: Battlegrounds minion cards from `Special:RunQuery/BG/Minion`
- `bg-hero`: Battlegrounds heroes from `Special:RunQuery/BG/Hero`
- `all`: all three scopes

Example lookup result for `OG_280`:

```json
{
  "scope": "card",
  "source_url": "https://hearthstone.wiki.gg/wiki/Special:RunQuery/Card",
  "page_title": "C'Thun",
  "page_url": "https://hearthstone.wiki.gg/wiki/C%27Thun",
  "name": "C'Thun",
  "card_id": "OG_280",
  "dbf_id": 38857,
  "details": {
    "artist": "James Ryman",
    "type_id": 4,
    "cost": 8,
    "attack": 6,
    "health": 6,
    "is_collectible": true,
    "is_elite": true
  }
}
```

Example Battlegrounds minion lookup for `BG26_817`:

```json
{
  "scope": "bg-minion",
  "page_title": "Battlegrounds/Blade Collector",
  "page_url": "https://hearthstone.wiki.gg/wiki/Battlegrounds/Blade_Collector",
  "name": "Blade Collector",
  "card_id": "BG26_817",
  "dbf_id": 99035,
  "details": {
    "attack": 3,
    "health": 2,
    "tier": 4,
    "is_pool_minion": true,
    "premium_dbf_id": 99036
  }
}
```

Example Battlegrounds hero lookup for `TB_BaconShop_HERO_29`:

```json
{
  "scope": "bg-hero",
  "page_title": "Battlegrounds/C'Thun",
  "page_url": "https://hearthstone.wiki.gg/wiki/Battlegrounds/C%27Thun",
  "name": "C'Thun",
  "card_id": "TB_BaconShop_HERO_29",
  "dbf_id": 58535,
  "details": {
    "health": 30,
    "armor": 20,
    "is_draftable_hero": true,
    "duos_armor": 18,
    "buddy_dbf_id": 77475
  }
}
```

Use `--fetch` when the app needs the full parser result, including art variants, patch changes, sounds, related cards, generated cards, and external links.

For Battlegrounds pages, `--fetch` also normalizes optional infobox fields into `card_data`:

- `armor` and `armor_text`
- `battlegrounds_tier`
- `minion_type`
- `hero_description`
- `hero_id`
- `alternate_card` for linked golden/alternate card stats from `other_*` infobox fields

Example card data for `C'Thun`:

| Field | Value |
| --- | --- |
| Name | `C'Thun` |
| Card id | `OG_280` |
| dbfId | `38857` |
| Class | `Neutral` |
| Card type | `Minion` |
| Cost | `8` |
| Attack | `6` |
| Health | `6` |
| Card set | `Whispers of the Old Gods` |
| Rarity | `Legendary` |
| Collectible | `true` |
| Non-collectible | `false` |
| Elite | `true` |
| Text | `Battlecry: Deal damage equal to this minion's Attack randomly split among all enemies.` |
| Battlecry | `true` |
| Artist | `James Ryman` |
| Keywords | `BATTLECRY` |
| Availability formats | `Wild` |
| Availability exclusions | `Default card generation` |
| Wiki mechanics | `Battlecry`, `Deal damage` |
| Wiki tags | `Attack-related`, `Random` |
| Flavor | `C'Thun's least favorite Hearthstone card: Eye for an Eye.` |
| Voice actor | `Michael Bell` |
| Race | `Old God` |

Normalized `card_data` excerpt:

```json
{
  "name": "C'Thun",
  "card_code": "OG_280",
  "dbf_id": 38857,
  "artist": "James Ryman",
  "full_text": "Battlecry: Deal damage equal to this minion's Attack randomly split among all enemies.",
  "battlecry": true,
  "keywords": ["BATTLECRY"],
  "rarity": "Legendary",
  "card_class": "Neutral",
  "card_type": "Minion",
  "cost": 8,
  "attack": 6,
  "health": 6,
  "card_set": "Whispers of the Old Gods",
  "collectible": true,
  "non_collectible": false,
  "elite": true,
  "availability": {
    "exclusions": ["Default card generation"],
    "formats": ["Wild"]
  },
  "wiki_mechanics": ["Battlecry", "Deal damage"],
  "wiki_tags": ["Attack-related", "Random"],
  "flavor": "C'Thun's least favorite Hearthstone card: Eye for an Eye.",
  "voice_actor": "Michael Bell",
  "race": "Old God"
}
```

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

The `Sounds` section is extracted as grouped audio clips. Each clip has a direct `file_url`, so it can be played from JSON or from the generated Markdown.

- `Play`
  - [`VO_OG_280_Male_OldGod_Play_01.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_Play_01.wav?32ea16): `My dreaming ends... Your nightmare... begins.`
  - [`CThun_Play_Stinger.wav`](https://hearthstone.wiki.gg/images/CThun_Play_Stinger.wav?e61ea9): `<music stinger>`
- `Trigger`
  - [`VO_OG_280_Male_OldGod_InPlay_01.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_01.wav?78a6b0): `Your minions will abandon you.`
  - [`VO_OG_280_Male_OldGod_InPlay_02.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_02.wav?7429aa): `Death is close.`
  - [`VO_OG_280_Male_OldGod_InPlay_03.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_03.wav?e13a43): `Your deck betrays you.`
  - [`VO_OG_280_Male_OldGod_InPlay_04.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_04.wav?19167e): `You have already lost.`
  - [`VO_OG_280_Male_OldGod_InPlay_05.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_05.wav?3bed9f): `Caress your fear.`
  - [`VO_OG_280_Male_OldGod_InPlay_06.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_06.wav?5e3708): `Your minions think you are weak`
  - [`VO_OG_280_Male_OldGod_InPlay_07.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_07.wav?f5ab64): `Hope is an illusion.`
  - [`VO_OG_280_Male_OldGod_InPlay_08.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_08.wav?9a8378): `It was your fault.`
  - [`VO_OG_280_Male_OldGod_InPlay_09.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_09.wav?732793): `That was a mistake.`
  - [`VO_OG_280_Male_OldGod_InPlay_10.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_10.wav?9a1101): `Flee, screaming.`
  - [`VO_OG_280_Male_OldGod_InPlay_11.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_11.wav?a5d752): `Give in to your fear.`
  - [`VO_OG_280_Male_OldGod_InPlay_12.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_InPlay_12.wav?95670b): `Well met.`
- `Attack`
  - [`VO_OG_280_Male_OldGod_Attack_01.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_Attack_01.wav?f0f54e): `Sleep.`
- `Death`
  - [`VO_OG_280_Male_OldGod_Death_01.wav`](https://hearthstone.wiki.gg/images/VO_OG_280_Male_OldGod_Death_01.wav?d44bfc): `<death sound>`

## C'Thun External Links

- [PlayHearthstone](https://hearthstone.blizzard.com/cards/38857)
- [HSReplay.net](https://hsreplay.net/cards/38857)
- [Hearthpwn](https://www.hearthpwn.com/cards/31110)

## Notes

- The script uses the public MediaWiki API on `hearthstone.wiki.gg`.
- `C'Thun` is a good sanity check because it includes regular, golden, and signature art variants.
- `Mountain Map` is a good sanity check for generated card pools because it exposes a `Special:RunQuery/WikiCardPool` link.
- Art variants are resolved from the page's infobox, so regular, golden, signature, and other displayed variants are included when present.

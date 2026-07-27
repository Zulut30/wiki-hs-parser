import unittest
from unittest.mock import patch

import wiki_hs_parser as parser


class RelatedCardSectionTests(unittest.TestCase):
    def test_collects_companion_card_sections_and_skips_cosmetic_sections(self) -> None:
        rendered_html = """
        <div>
          <h2><span class="mw-headline" id="Modules">Modules</span></h2>
          <div class="list-cards">
            <div class="card-div">
              <a href="/wiki/Recursive_Module" title="Recursive Module">
                <img alt="TOY 330t92.png" src="/images/TOY_330t92.png">
              </a>
            </div>
          </div>
          <h2><span class="mw-headline" id="How_to_get">How to get</span></h2>
          <div class="list-cards">
            <div class="card-div">
              <a href="/wiki/Whizbang%27s_Workshop" title="Expansion icon">
                <img alt="Expansion.png" src="/images/Expansion.png">
              </a>
            </div>
          </div>
          <h2><span class="mw-headline" id="Art_pieces">Art pieces</span></h2>
          <div class="list-cards">
            <div class="card-div">
              <a href="/wiki/Zilliax_Deluxe_3000_(Power_art)" title="Power art">
                <img alt="TOY 330t12.png" src="/images/TOY_330t12.png">
              </a>
            </div>
          </div>
          <h2><span class="mw-headline" id="Related_cards">Related cards</span></h2>
          <h3>Additional hero powers</h3>
          <div class="list-cards">
            <div class="card-div">
              <a href="/wiki/Extra_Hero_Power" title="Extra Hero Power">
                <img alt="HERO_POWER.png" src="/images/HERO_POWER.png">
              </a>
            </div>
          </div>
          <h2><span class="mw-headline" id="Hero_skins">Hero skins</span></h2>
          <div class="list-cards">
            <div class="card-div">
              <a href="/wiki/Cosmetic_Skin" title="Cosmetic Skin">
                <img alt="SKIN.png" src="/images/SKIN.png">
              </a>
            </div>
          </div>
          <h2><span class="mw-headline" id="Gallery">Gallery</span></h2>
          <div class="list-cards">
            <div class="card-div">
              <a href="/wiki/Unrelated_Gallery_Card" title="Gallery card">
                <img alt="GALLERY.png" src="/images/GALLERY.png">
              </a>
            </div>
          </div>
        </div>
        """
        card_codes = {
            "Recursive_Module": "TOY_330t92",
            "Zilliax_Deluxe_3000_(Power_art)": "TOY_330t12",
            "Extra_Hero_Power": "HERO_POWER",
            "Cosmetic_Skin": "SKIN",
            "Unrelated_Gallery_Card": "GALLERY",
        }

        def resolve(page_url: str) -> str | None:
            return card_codes.get(page_url.rsplit("/", 1)[-1])

        with patch.object(parser, "resolve_card_code", side_effect=resolve):
            groups = parser.extract_related_card_groups(rendered_html)

        self.assertEqual(
            [(group.heading, [card.card_code for card in group.cards]) for group in groups],
            [
                ("Modules", ["TOY_330t92"]),
                ("Art pieces", ["TOY_330t12"]),
                ("Additional hero powers", ["HERO_POWER"]),
            ],
        )

    def test_deduplicates_cards_repeated_in_multiple_sections(self) -> None:
        rendered_html = """
        <div>
          <h2><span class="mw-headline" id="Tokens">Tokens</span></h2>
          <div class="list-cards"><div class="card-div"><a href="/wiki/Token">Token</a></div></div>
          <h2><span class="mw-headline" id="Related_cards">Related cards</span></h2>
          <div class="list-cards"><div class="card-div"><a href="/wiki/Token">Token</a></div></div>
        </div>
        """
        with patch.object(parser, "resolve_card_code", return_value="TOKEN_1"):
            groups = parser.extract_related_card_groups(rendered_html)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].heading, "Tokens")
        self.assertEqual([card.card_code for card in groups[0].cards], ["TOKEN_1"])


if __name__ == "__main__":
    unittest.main()

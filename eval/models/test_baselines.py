from __future__ import annotations

from eval.models.baselines import KeywordRouter, Majority, stem, words
from eval.models.data import NONE


def test_majority_picks_the_most_common_label() -> None:
    assert Majority(["a", "b", "b"]).predict("anything") == "b"


def test_keyword_router_finds_an_obvious_topic_and_its_subject() -> None:
    kw = KeywordRouter(majority_domain="biology")
    assert kw.topic("explain how electromagnetic induction works with a magnet and coil").startswith("physics_")
    assert kw.domain("how does a transformer step up voltage with electromagnetic induction") == "physics"


def test_keyword_router_says_none_when_nothing_matches() -> None:
    kw = KeywordRouter(majority_domain="biology")
    assert kw.topic("zzzz qqqq xxxx") == NONE
    assert kw.domain("zzzz qqqq xxxx") == "biology"


def test_helpers_drop_stop_words_and_stem() -> None:
    assert "the" not in words("show me the cell") and "cell" in words("show me the cell")
    assert stem("enzymes") == "enzym" or stem("enzymes").startswith("enzym")

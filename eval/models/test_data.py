from __future__ import annotations

import json

from eval.models.data import (
    DERIVED,
    HEADS,
    NONE,
    SOURCE_COMMIT,
    jaccard,
    leakage_between,
    load_split,
    taxonomy_slugs,
    tokens,
)


def test_no_query_is_in_both_train_and_test_or_val_and_test() -> None:
    train, val, test = load_split("train"), load_split("val"), load_split("test")
    assert leakage_between(train, test) == 0
    assert leakage_between(val, test) == 0
    assert leakage_between(train, val) == 0


def test_no_near_duplicate_of_a_test_question_is_in_train() -> None:
    train, test = load_split("train"), load_split("test")
    test_tokens = [tokens(r["query"]) for r in test]
    worst = max(jaccard(tokens(r["query"]), t) for r in train for t in test_tokens)
    assert worst < 0.8


def test_counts_add_up_to_the_audit() -> None:
    audit = json.loads((DERIVED / "audit.json").read_text(encoding="utf-8"))
    out = audit["rows_out"]
    assert (len(load_split("train")), len(load_split("val")), len(load_split("test"))) == (
        out["train"],
        out["val"],
        out["test"],
    )
    removed = audit["exact_duplicates_removed_from_train"] + sum(
        audit["train_rows_removed_for_test_leakage"][k] for k in ("exact", "near")
    )
    assert audit["rows_in"]["train"] - removed == out["train"] + out["val"]
    assert audit["source_commit"] == SOURCE_COMMIT


def test_every_topic_label_is_in_the_taxonomy_or_none_or_unknown() -> None:
    allowed = set(taxonomy_slugs()) | {NONE, None}
    for split in ("train", "val", "test"):
        assert {r["topic"] for r in load_split(split)} <= allowed


def test_every_taxonomy_topic_has_training_rows_and_heads_are_complete() -> None:
    train = load_split("train")
    assert {r["topic"] for r in train} >= set(taxonomy_slugs())
    for r in train + load_split("test"):
        assert all(h in r for h in HEADS) and r["query"].strip()
        assert r["complexity"] in (1, 2, 3)


def test_the_split_is_stratified_by_topic() -> None:
    val = load_split("val")
    assert len({r["topic"] for r in val if r["topic"] not in (None, NONE)}) >= 45


def test_derived_files_do_not_contain_textbook_text_fields() -> None:
    for split in ("train", "val", "test"):
        for r in load_split(split):
            assert set(r) == {"query", "topic", "domain", "pattern", "complexity"}

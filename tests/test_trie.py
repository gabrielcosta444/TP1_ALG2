import pytest

from tp1.trie import RadixTrie


def test_single_key_can_be_found_by_full_or_partial_prefix() -> None:
    trie = RadixTrie()
    trie.insert("u9a1bcde", "c1")

    assert trie.search_prefix("u9a1bcde") == ("c1",)
    assert trie.search_prefix("u9a") == ("c1",)
    assert len(trie) == 1


def test_shared_prefix_splits_edge_and_separates_branches() -> None:
    trie = RadixTrie()
    trie.insert("u9a1bcde", "c1")
    trie.insert("u9a1zzzz", "c2")
    trie.insert("u9a1bfff", "c3")

    assert trie.search_prefix("u9a1") == ("c1", "c2", "c3")
    assert trie.search_prefix("u9a1b") == ("c1", "c3")
    assert trie.search_prefix("u9a1z") == ("c2",)


def test_shorter_key_inserted_after_longer_key_keeps_both_ids() -> None:
    trie = RadixTrie()
    trie.insert("u9a1bcde", "long")
    trie.insert("u9a1", "short")

    assert trie.search_prefix("u9a1") == ("long", "short")
    assert trie.search_prefix("u9a1b") == ("long",)


def test_longer_key_inserted_after_shorter_key_keeps_prefix_id_separate() -> None:
    trie = RadixTrie()
    trie.insert("u9a1", "short")
    trie.insert("u9a1bcde", "long")

    assert trie.search_prefix("u9a1") == ("short", "long")
    assert trie.search_prefix("u9a1b") == ("long",)


def test_same_key_preserves_insertion_order_and_deduplicates_id() -> None:
    trie = RadixTrie()
    trie.insert("u9a1bcde", "c2")
    trie.insert("u9a1bcde", "c1")
    trie.insert("u9a1bcde", "c1")

    assert trie.search_prefix("u9a1bcde") == ("c2", "c1")
    assert len(trie) == 2


def test_missing_prefix_returns_empty_tuple() -> None:
    trie = RadixTrie()
    trie.insert("u9a1bcde", "c1")

    assert trie.search_prefix("u9b") == ()


def test_empty_prefix_returns_every_id_in_insertion_order() -> None:
    trie = RadixTrie()
    trie.insert("u9a1bcde", "c2")
    trie.insert("7h2x4abc", "c1")

    assert trie.search_prefix("") == ("c2", "c1")


@pytest.mark.parametrize("key, courier_id", [("", "c1"), ("u9a1", "")])
def test_insert_rejects_empty_key_or_id(key: str, courier_id: str) -> None:
    with pytest.raises(ValueError):
        RadixTrie().insert(key, courier_id)

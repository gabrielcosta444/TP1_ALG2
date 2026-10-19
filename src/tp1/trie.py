
from dataclasses import dataclass, field


@dataclass(slots=True)
class _Node:
    label: str
    children: dict[str, "_Node"] = field(default_factory=dict)
    ids: dict[str, None] = field(default_factory=dict)


class RadixTrie:

    def __init__(self) -> None:
        self._root = _Node("")

    def __len__(self) -> int:
        return len(self._root.ids)

    def insert(self, key: str, courier_id: str) -> None:
        if not key:
            raise ValueError("key must not be empty")
        if not courier_id:
            raise ValueError("courier_id must not be empty")

        self._root.ids[courier_id] = None
        node = self._root
        remaining = key

        while remaining:
            child = node.children.get(remaining[0])
            if child is None:
                node.children[remaining[0]] = _Node(
                    label=remaining,
                    ids={courier_id: None},
                )
                return

            common_length = _common_prefix_length(remaining, child.label)
            if common_length == len(child.label):
                child.ids[courier_id] = None
                remaining = remaining[common_length:]
                node = child
                continue

            common_label = child.label[:common_length]
            existing_suffix = child.label[common_length:]
            new_suffix = remaining[common_length:]
            split_ids = dict(child.ids)
            split_ids[courier_id] = None
            split = _Node(label=common_label, ids=split_ids)

            child.label = existing_suffix
            split.children[existing_suffix[0]] = child
            if new_suffix:
                split.children[new_suffix[0]] = _Node(
                    label=new_suffix,
                    ids={courier_id: None},
                )

            node.children[common_label[0]] = split
            return

    def search_prefix(self, prefix: str) -> tuple[str, ...]:
        if not prefix:
            return tuple(self._root.ids)

        node = self._root
        remaining = prefix
        while remaining:
            child = node.children.get(remaining[0])
            if child is None:
                return ()

            common_length = _common_prefix_length(remaining, child.label)
            if common_length == len(remaining):
                return tuple(child.ids)
            if common_length < len(child.label):
                return ()

            remaining = remaining[common_length:]
            node = child

        return tuple(node.ids)


def _common_prefix_length(left: str, right: str) -> int:
    length = 0
    for left_character, right_character in zip(left, right, strict=False):
        if left_character != right_character:
            break
        length += 1
    return length

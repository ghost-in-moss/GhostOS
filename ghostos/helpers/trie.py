from typing import List, Dict, Set, Optional, Iterable


class SimpleTrie:

    def __init__(self, *searches: str):
        self.str_set: Set[str] = set(searches)
        self.char_set: Dict[int, Set[str]] = {}
        self.max_length = 0
        for line in searches:
            i = 0
            for c in line:
                if i not in self.char_set:
                    self.char_set[i] = set()
                exists = self.char_set[i]
                exists.add(c)
                self.char_set[i] = exists
                i += 1
            self.max_length = max(self.max_length, i)

    def match(self, target: str) -> bool:
        return target in self.str_set

    def startswith(self, target: str) -> Iterable[str]:
        """
        ? 运行效率会比 for 循环 startwith 高吗?
        """
        buffer = ""
        i = 0
        for c in target:
            if i >= self.max_length:
                break
            chars = self.char_set[i]
            if c in chars:
                buffer += c
                if buffer in self.str_set:
                    yield buffer
            i += 1

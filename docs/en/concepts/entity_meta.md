# Entity Meta

A code-driven AI Agent needs to store various data during its operation, a
nd also be able to restore variables in subsequent operations.
Considering a distributed system or an interruptible Agent, these data need a long-term storage solution.

`GhostOS`, based on `pickle` and `pydantic`, has
implemented [EntityMeta](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/entity.py).

It aims to:

1. Serialize and deserialize the vast majority of accessible Python data structures
2. Provide a universal container and API for data manipulation
3. Ensure data readability as much as possible.

More technical details can be seen in the code.
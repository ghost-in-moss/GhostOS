# Contracts

This directory provides basic abstract classes that GhostOS and Ghost depending on.
The implementations shall be wrapped by GhostOS.container.Provider and register to Container.
So every class depend on them can fetch them from Container.

`GhostOS` has three layers of library interfaces:
- Contracts: independent libraries.
- Ghosts: the interfaces of `GhostOS`, depending on `Contracts`
- Libraries: the libraries for `GhostOS`'s applications, depending on `GhostOS` and `Contracts` interfaces.

The implementations provided by this project are defined at `ghostos.framework`.
There are providers (`ghostos_container.Provider`) managing implementations of the library interfaces,
develop should choose wanted providers and register them to the `IoCContainer`.
By `IoCContainer` we can switch the implementations without too much pain.

There are at least four level IoCContainer in the `GhostOS`:
- application container: manage static implementations of `Contracts`.
- GhostOS container: manage the process level implementations for `GhostOS`.
- Ghost container: `GhostOS` can manage multiple ghost process concurrently so each Ghost instance has it own container.
- Moss container: when LLM generate python code within Moss, some in-context temporary bindings are needed, so `MossRuntime` has a container.

Each container is nested from above level container, so they inherit or override parent container's bindings.

> todo: let LLM optimize the content above
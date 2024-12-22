# Abstract Class Design

The abstract design of GhostOS adheres to the principle of interface-oriented programming.
All modules are designed using abstract classes, and implementations are assembled through
the [IoC Container](/en/concepts/ioc_container.md)

![architecture](../../assets/architecture.png)

The basic interrelationships of these abstractions and their usage logic are as follows:

```python
from ghostos.abcd import GhostOS, Shell, Conversation, Ghost
from ghostos.container import Container
from ghostos.bootstrap import make_app_container, get_ghostos

# create your own root ioc container.
# register or replace the dependencies by IoC service providers.
container: Container = make_app_container(...)

# fetch the GhostOS instance.
ghostos: GhostOS = get_ghostos(container)

# Create a shell instance, which managing sessions that keep AI Ghost inside it.
# and initialize the shell level dependency providers.
shell: Shell = ghostos.create_shell("your robot shell")
# Shell can handle parallel ghosts running, and communicate them through an EventBus.
# So the Multi-Agent swarm in GhostOS is asynchronous.
shell.background_run()  # Optional

# need an instance implements `ghostos.abcd.Ghost` interface.
my_chatbot: Ghost = ...

# use Shell to create a synchronous conversation channel with the Ghost.
conversation: Conversation = shell.sync(my_chatbot)

# use the conversation channel to talk
event, receiver = conversation.talk("hello?")
with receiver:
    for chunk in receiver.recv():
        print(chunk.content)

```

For detailed content, please check the source code. [ghostos.abcd.concepts](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/abcd/concepts.py)

> Abstract design-related introductions can be quite complex; 
> only complete the documentation when I have the energy (T_T).
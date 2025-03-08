# Messages

One of the design goals of `GhostOS` is to implement a fully asynchronous intelligent agent cluster on the server side.
Therefore, the transmission and storage of historical messages cannot be limited to the client side; they also need to
be handled on the server side.

To address issues such as streaming message protocol, model compatibility, storage, and reading; `GhostOS` has designed
its own message container.
For more details, see [ghostos.core.messages](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/messages/message.py)

At present, there is no energy to introduce all the details, so I will focus on introducing a few key concepts:

## Variable Message

`GhostOS` agents are driven by code, so they can transmit various runtime variables in the form of `VariableMessage`,
including:

1. Passed to the client side, such as streamlit
2. Transmitted to other Agents

In the historical records, the LLM can see the `vid` parameter of the variable,
and the corresponding variable can be obtained using
the [ghostos/contracts/variables](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/variables.py) library.
This enables interaction based on variables.

Examples:

1. An Agent transmits its own variables to another Agent.
2. An Agent sends a variable of a certain data structure to the client, which then renders it on its own.
3. The client side can send variables in the form of messages, and the Agent can retrieve the variable data structure in
   the code and manipulate it.
4. An Agent can manipulate variables seen in the historical context.

## Audio & Image Message

In `GhostOS`, images and audio messages in the historical records are stored in centralized storage, with the message ID
serving as the storage ID for both images and audio. For more details,
see [ghostos/contracts/assets](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/contracts/assets.py).

It is expected that in the future, Audio and Image will also support `variable type messages`, allowing large language
models to manipulate them through code.

For example, a large language model without image recognition capabilities can call another model capable of image
recognition to assist it in reading images through code.
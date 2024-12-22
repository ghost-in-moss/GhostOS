# EventBus

`GhostOS` manages event communication between Agents, between Agents and the external world, and within Agents
themselves through the [EventBus](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/events.py) class.

Based on the event bus, we can implement a fully asynchronous Agent. Taking the example of a time-consuming network
car-hailing:

1. The user converses with the main Agent, requesting that the Agent hail a car.
2. The Agent calls upon a sub-Agent with car-hailing capabilities to execute the task.
3. The Agent continues to converse with the user.
4. The Agent can inquire about the task execution status from the sub-Agent at any time.
5. After the sub-Agent hails a car, it notifies the main Agent through an Event.

The event bus maintains the Event Loop for all Agents, thereby achieving fully asynchronous communication.

In addition to communication between Agents, communication between external systems and Agents also needs to go through
the EventBus. However, the `ghostos.abcd.Conversation` abstraction includes the relevant interfaces for this purpose.
Communication from external systems can include:

* Events that occur in the environment
* Scheduled tasks
* Asynchronous callbacks from interfaces

# Event Object

GhostOS
中的事件对象定义在 [ghostos.core.runtime.events.Event](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/core/runtime/events.py).
相关 API 详见代码.

# EventBus Registrar

As the base class, EventBus is registered in `ghostos.bootstrap.app_container`. By simply changing the Provider
registered with EventBus, you can modify its implementation. For more details, see the relevant section on the
Container.

# Current Implementation

The `EventBus` can be implemented using various technologies, including file-based, relational database-based, and Redis
or other KV storage-based implementations to achieve an event bus for distributed systems.

Since `GhostOS` lacks development resources, the current implementation is a memory-based dictionary. For more details,
see [MemEventBusImpl](https://github.com/ghost-in-moss/GhostOS/tree/main/ghostos/framework/eventbuses/memimpl.py). This means that
shutting down a running program will result in the loss of events.

In the future, it is hoped that the default implementation of EventBus can be made configurable, allowing users to
choose between several out-of-the-box solutions such as `file`, `redis`, `mysql` through configuration options.
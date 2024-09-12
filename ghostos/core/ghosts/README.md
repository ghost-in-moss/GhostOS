# Ghosts 

The Ghosts directory provides the interfaces of Ghost, and Ghost is the blueprint of llm-based agent.
Ghost provide fundamental APIs from libraries that MUST EXISTS for a functional agent.
Such as Session, Container, Workspace and schedulers.

The Thought class is an atomic stateful thinking machine unit (like an agent), using Task to describe thinking state, 
using MsgThread to record thinking / conversation history messages. 
And Thought receive a Ghost instance to control everything.

The Action is the atomic abstract for LLM callback function. 
Thought provides multiple actions to interact with LLM outputs.

The `schedulers.py` file defines the basic schedulers for a Thought to controller task, multi-task, multi-agent ETC.

# Title of paper

From Code to Context: Achieving Self-Evolving Turing Completeness in AI Agents


# Abstract
Developing AI agents powered by large language models (LLMs) faces significant challenges in achieving true Turing completeness and self-evolving capabilities. Current approaches often generate code independently of its runtime context, relying heavily on the LLM's memory, which results in inefficiencies and limits adaptability. Manual protocol development in sandbox environments further constrains the agent's autonomous evolution. Crucially, achieving consistency in code and context across multi-turn interactions and ensuring isolation of local variables within each interaction remains an unsolved problem.   

We introduce MOSS (llM-oriented Operating System Simulation), a novel framework that systematically addresses these challenges by integrating code generation with a dynamic context management system. MOSS ensures consistency and adaptability by using a sophisticated mechanism that maintains the Python context across interactions, including isolation of local variables and preservation of runtime integrity. At its core, the framework employs an Inversion of Control (IoC) container in conjunction with decorators to enforce the least knowledge principle, allowing agents to focus on abstract interfaces rather than concrete implementations. This facilitates seamless integration of new tools and libraries, enables runtime instance replacement, and reduces prompt complexity, providing a "what you see is what you get" environment for the agent.   

Through a series of case studies, we show how this framework can enhance the efficiency and capabilities of agent development and highlight its advantages in achieving Turing-complete and self-evolving agents.

# Introduction
Developing AI agents capable of self-evolution and achieving Turing completeness is a major frontier in artificial intelligence research. Early efforts, such as Program-aided Language Models (PAL)【PAL】 and CodeAct【CodeAct】, laid the groundwork for using large language models (LLMs) to automate code generation and execution, demonstrating that AI agents could interact with their environments by writing and executing code. However, these methods primarily focus on single-turn interactions, which limits the agents' ability to maintain and adapt complex runtime contexts over multi-turn engagements. While subsequent approaches like OpenDevin【OpenDevin】 and MindSearch【MindSearch】 have expanded upon this foundation by offering platforms for multi-agent interactions and complex task planning, they still face challenges in managing execution contexts and preserving consistency across multiple interactions—a critical requirement for true Turing completeness.   
MindSearch, for instance, employs a multi-agent system for complex web information retrieval, using a WebPlanner to decompose tasks and a WebSearcher for hierarchical retrieval. However, despite its advanced planning and information processing capabilities, it struggles with dynamic adaptability and context management in multi-turn interactions. Similarly, OpenDevin offers a platform where agents can interact with tools and environments through sandboxed code execution, but it primarily relies on event streams to manage interactions, which often leads to a lack of runtime consistency and isolated execution contexts. Automated Design of Agentic Systems (ADAS)【ADAS】 takes a different approach by introducing a meta-agent that programs new agents iteratively. However, it also lacks a robust mechanism for maintaining code context across multi-turn interactions, thus limiting its adaptability and autonomy.   
Recent efforts such as Diversity Empowered Intelligence (DEI)【DEI】 have aimed to harness the strengths of diverse agents by forming multi-agent ensembles. While DEI demonstrates the potential of collaborative AI systems, it does not achieve Turing completeness in the sense of a single autonomous agent evolving and adapting its capabilities. Similarly, while the "Literate Programming in the LLM Era" approach【Literate Programming】 offers an innovative way to synchronize code and natural language outline for better code understanding and maintenance, it focuses more on aiding developers in coding rather than enabling autonomous agent evolution.   
The core challenge in achieving Turing-complete AI agents lies in maintaining consistency between code and its runtime context across multi-turn interactions. Current LLM-powered systems often generate code in a single-shot manner, heavily relying on the LLM's memory and understanding to adapt in subsequent turns. This approach leads to inefficiencies and limits adaptability, as it fails to preserve the execution context or isolate variables between interactions. Consequently, AI agents struggle with complex tasks that require multi-step execution and dynamic adaptation. Moreover, existing methods frequently rely on manual protocol development in sandbox environments, which hinders the agent's ability to evolve autonomously.   
In this paper, we introduce MOSS (llM-oriented Operating System Simulation), a novel framework designed to overcome these challenges by integrating code generation with a dynamic context management system. Unlike previous methods that rely on event streams, sandboxed environments, or natural language summaries, MOSS ensures consistency and adaptability by maintaining the Python runtime context across interactions. It isolates local variables and preserves runtime integrity, providing an environment where agents can evolve autonomously.   
MOSS aims to advance the field of AI agents in the following ways:   
1. Achieving True Turing Completeness: By ensuring consistency in code execution and context management across multi-turn interactions, MOSS enables AI agents to handle complex, multi-step tasks autonomously. This capability surpasses systems like ADAS and OpenDevin, which focus on single-shot code generation or sandboxed execution but lack dynamic adaptability in evolving environments.   
2. Self-Evolving Capabilities: MOSS introduces a framework where agents can self-evolve by creating and integrating new tools at runtime. Unlike approaches like NL Outlines and "Literate Programming in the LLM Era," which primarily aid code understanding and generation, MOSS enables agents to extend their functionality autonomously through IoC containers, thus fostering continuous self-improvement.

# Method
## Overview of the MOSS Framework
MOSS (llM-oriented Operating System Simulation) is designed to achieve Turing completeness and self-evolving capabilities in AI agents through multi-turn interactions. Unlike traditional LLM-based systems that rely heavily on the model's internal memory, MOSS integrates code generation with dynamic context management to ensure consistency between the code and its runtime environment. In single-turn tasks, MOSS achieves Turing completeness by enabling agents to plan and execute actions using Python code. For multi-turn interactions, it addresses challenges such as maintaining consistent code context, isolating variables, and preserving execution context across frames. This allows MOSS to perform complex tasks that require multi-step execution and dynamic adaptation. Additionally, MOSS facilitates self-evolution by allowing agents to autonomously extend their capabilities through seamless integration of new tools and libraries, fostering continuous self-improvement.   

## Dynamic Context Management and Frame Mechanism
Dynamic context management is at the core of MOSS, ensuring that the code generated in each interaction remains consistent with the Python runtime context. MOSS accomplishes this by isolating and preserving the execution context through a frame-based mechanism. Each interaction is treated as an independent execution frame, and MOSS maintains a stack of these frames to support complex tasks that involve multiple steps.

## Execution Isolation
Each AIFunc and Thought operates in a separate execution frame managed by dedicated managers. This isolation ensures that local variables and temporary states are contained within each frame, preventing unintended side effects that could arise from variable leakage or context pollution. By using temporary modules and a runtime compilation-execution mechanism, MOSS ensures that each interaction has a clean state, which is crucial for reliable multi-turn interactions.

### Global State Inheritance
While isolating local variables, MOSS ensures that global variables and instances are inherited across frames. This design allows agents to access and modify the global context as needed, preserving coherence throughout multi-step tasks. By maintaining a stack of execution frames, MOSS supports complex task flows where the agent can build upon previous states, ensuring that the entire task chain remains intact and consistent. This inheritance enables the agent to retain important global information, like configurations and persistent objects, across interactions, which is essential for tasks that require continuity.

### Context Consistency
MOSS uses execution managers, runtime modules, and the Python context (PyContext) to maintain consistency across multi-turn interactions. PyContext acts as a container for each interaction’s runtime state, holding global variables, module references, and dependencies. By preserving the state of PyContext across interactions, MOSS ensures that the agent's code can evolve and adapt without losing track of the execution context, enabling seamless execution of multi-step tasks.

## IoC and Local Process Integration
MOSS adopts an Inversion of Control (IoC) container to enforce the Least Knowledge Principle (LKP) and streamline the integration of tools and libraries. By focusing on interface-oriented programming, the agent interacts with abstract interfaces rather than specific implementations. The IoC container injects dependencies at runtime, adapting to the current environment and requirements.

### Seamless Interface Integration
Since the framework and agent runtime operate within the same process, MOSS can directly integrate new functionalities without the need for complex RPC protocols. This direct interaction with the IoC container enables the agent to extend its capabilities in a Turing-complete manner. By injecting abstract interfaces into the MOSS environment, the agent can focus on high-level goals while the IoC container handles the details of implementation, ensuring a clean separation of concerns.

### Dynamic Replacement and Adaptation
The IoC container allows runtime instance replacement, enabling agents to adapt to new environments or requirements without modifying their core logic. This dynamic flexibility is crucial for self-evolving agents, as it permits the seamless introduction of new tools, libraries, or functionalities at runtime, enhancing the agent's ability to evolve autonomously.

## Intelligent Units: AIFunc and Thought
MOSS introduces two fundamental intelligent units—AIFunc and Thought—that empower agents to perform complex task decomposition and high-level planning:

**AIFunc** (Synchronous Single-Turn Intelligent Functions)
AIFunc represents atomic units of execution that complete within a single interaction. They allow the agent to generate and execute Python code based on natural language instructions, providing a form of literate programming. Each AIFunc operates within its own execution frame but can access the global context, ensuring a consistent execution environment. AIFuncs can be nested within other AIFuncs or Thoughts, allowing the agent to break down complex tasks into smaller steps and achieve higher-order reasoning. This modularity enables the agent to handle tasks in a structured manner and facilitates the reuse of AIFuncs across different contexts.

**Thought** (Asynchronous Multi-Turn Intelligent Thought Processes)
Thought extends AIFunc by enabling multi-turn, asynchronous interactions. It allows the agent to engage in iterative reasoning, dynamically adjusting its strategy based on real-time feedback. Within a Thought process, the agent can invoke multiple AIFuncs, orchestrating them to achieve complex goals. Thoughts maintain a persistent context across interactions, making them suitable for tasks that require ongoing planning, exploration, and adaptation. This asynchronous process enables nearly infinite nesting and complex interaction patterns, allowing the agent to adaptively evolve based on runtime conditions rather than being limited to sequential execution.

## Self-Evolving Capabilities
MOSS supports self-evolution by enabling agents to interact with their environment entirely through code, allowing them to autonomously develop and integrate new tools:

**Code-Environment Interaction**
Agents interact with the environment by generating and executing code, eliminating the need for pre-defined, human-developed tools. MOSS facilitates this interaction through its IoC container, enabling agents to directly extend their capabilities. By generating code that directly interacts with the environment, agents can autonomously create new functionalities to address evolving requirements.

**Seamless Integration of New Tools**
Through the IoC container, MOSS supports the dynamic integration of new tools and libraries. Agents interact with these tools via abstract interfaces, injecting dependencies at runtime. This process breaks the barrier between code and prompt, allowing agents to evolve by creating new functionalities that can be immediately utilized. The IoC container ensures that the agent can seamlessly incorporate new tools into its workflow, promoting continuous self-improvement.

**Runtime Knowledge Accumulation**
Using the PyContext mechanism, MOSS allows agents to preserve and leverage valuable information across interactions. Agents can "remember" learned knowledge, apply it in future interactions, and iteratively optimize their behaviors. This continuous accumulation and refinement of knowledge contribute to the agent’s self-evolution. Additionally, MOSS allows successful AIFuncs or Thoughts to be converted into static code, making them part of the agent's permanent toolkit. This dynamic-to-static code transition enriches the agent's capabilities over time, reducing reliance on dynamic code generation for recurring tasks.

**Human-in-the-Loop Collaboration**
MOSS supports human-agent collaboration, enabling developers to adjust the agent's behavior by embedding solutions into the agent's operating context. Since the agent's actions and thought processes are represented in code, developers can guide and influence the agent's self-evolution in a more controlled manner. This collaborative process ensures that the agent’s learning and adaptation align with human-defined goals and standards.   

Through this structured management of execution context, intelligent unit design, and integration with the IoC container, MOSS achieves both the isolation necessary for multi-turn interactions and the consistency required for Turing-complete and self-evolving AI agents. The framework provides a robust platform for agents to evolve autonomously, leveraging code generation, dynamic context management, and human collaboration to tackle increasingly complex tasks.

# Case Studies


# Discussion
## Security Considerations
One of the key design choices in MOSS is its operation within the local Python process rather than a sandboxed environment. While this decision facilitates direct integration and interaction with the IoC container, enhancing execution efficiency and context management, it raises potential security concerns. Unlike sandboxed environments, where code execution is isolated and risks are mitigated, the local process approach requires careful management to prevent unintended side effects or security vulnerabilities. Future work will focus on improving the safety of the local execution environment, implementing more robust safeguards to prevent harmful code execution, and ensuring the integrity of the system. We invite the community to collaborate on developing best practices and contributing to the security framework of MOSS.  

## Enhancing Thought and AIFunc with Advanced Models
MOSS introduces Thought and AIFunc as intelligent units for executing complex, multi-turn tasks. While these units already offer significant capabilities, their potential can be further unlocked through advanced language models like the GPT-4 series, known for their strong chain-of-thought (CoT) reasoning abilities. Such models can improve the coherence and effectiveness of Thought processes and enhance the accuracy of AIFunc operations by generating more context-aware and purpose-driven code. By leveraging the inherent reasoning strengths of these models, MOSS can execute complex sequences of actions more effectively, making the framework even more suitable for tasks that require adaptive planning, exploration, and execution.

## The Need for Amplifiers and Integration Frameworks
Even the most advanced AI models, like GPT-4, benefit significantly from amplifiers—tools and frameworks that augment their problem-solving capabilities. Just as humans rely on IDEs and methodologies like divide-and-conquer to tackle complex software development tasks, AI agents require a well-integrated framework to interact with their environment and manage complex workflows. MOSS serves as this amplifier, providing an integrated code-generation and context-management system that allows AI agents to decompose intricate tasks into manageable units. By systematically interacting with their environment through code, agents can achieve higher-order functionalities that transcend the limitations of any single model. This framework enables the development and deployment of sophisticated AI systems that can be debugged, monitored, and guided more effectively by humans, ensuring reliable and controllable AI behavior.

## Enhancing Debuggability and Control in Complex AI Systems
A core advantage of MOSS's design philosophy is the emphasis on code-driven interaction with the environment, which offers a higher degree of transparency and control compared to black-box AI systems. By adopting a divide-and-conquer approach and focusing on generating and executing code, MOSS allows developers to debug complex AI systems in a manner similar to traditional software debugging. This structured approach provides a clear trace of the agent's decision-making process, enabling developers to intervene, modify, and guide the AI system at critical junctures. By integrating human expertise into the evolution of AI agents through direct code modification, MOSS offers a path toward creating more controllable and interpretable AI systems that can evolve autonomously while remaining aligned with human objectives.

# Conclusion

MOSS represents a significant advancement in the development of Turing-complete and self-evolving AI agents. By integrating code generation with dynamic context management, it addresses the challenges of maintaining consistency between code and runtime context across multi-turn interactions. The framework's use of an IoC container and runtime instance replacement facilitates the seamless integration of new tools and libraries, enabling agents to autonomously evolve their capabilities. Furthermore, MOSS's structured approach to executing complex, multi-step tasks through isolated execution frames and intelligent units like AIFunc and Thought empowers agents to adapt and tackle increasingly intricate challenges.   

The framework's design also emphasizes the importance of transparency and control in AI systems, offering developers a robust platform to debug and guide agents using familiar programming paradigms. While challenges such as execution security remain, MOSS lays the groundwork for future research and development in creating more adaptable, interpretable, and secure AI agents. The integration of advanced language models and the continued refinement of the framework promise to further enhance the capabilities of AI agents, bridging the gap between current limitations and the vision of truly autonomous, self-evolving intelligent systems.

# References



0. Martin R C. Agile software development: principles, patterns, and practices[M]. Prentice Hall PTR, 2003.

1. Natural Language Outlines for Code: Literate Programming in the LLM Era

The paper introduces a novel approach using natural language outlines, where concise natural language segments are employed to summarize code logic. NL Outlines not only aid developers in quickly understanding and navigating code but also enable bidirectional synchronization between code and natural language, allowing for more efficient code maintenance and generation.   
Bidirectional Synchronization of Code and Natural Language: NL Outlines provide a two-way interactive mode, allowing developers to edit either the code or the natural language outline to trigger corresponding updates. This interaction mode enables developers to directly drive code modifications and extensions through high-level natural language descriptions.
Code Understanding and Maintenance: In IDEs, NL Outlines serve as annotations embedded in the code, aiding developers in faster code comprehension, navigation, and maintenance. They ensure consistency between code and its documentation by providing real-time updates to the NL Outline when the code is modified.   
Code Generation and Review: NL Outlines can guide code generation and offer more understandable summaries of changes during code reviews. This approach helps developers more effectively guide and inspect code during the generation and review process.   

2. OpenDevin: An Open Platform for AI Software Developers as Generalist Agents
OpenDevin's Core Points:
Generalist and Specialist AI Agents: OpenDevin provides a platform for developing both generalist and specialist AI agents that interact with their environment primarily by writing code, using command-line tools, and browsing the web.
Action and Observation Stream: It employs an event stream architecture that captures actions and observations, allowing agents to perceive their environment and take appropriate actions. The agents can create, modify, and execute code based on this interaction stream.   
Sandboxed Environment: Agents operate in a secure sandbox environment (e.g., Docker containers) to safely execute code, reducing the risk of negative side effects on the user's system.
Tool and Web Integration: OpenDevin includes a standardized set of tools, like Python and Bash command execution, and can interact with web browsers, enabling agents to perform a wide range of tasks from software development to web browsing.
Multi-Agent Coordination: It supports multi-agent systems where specialized agents can delegate tasks to one another, enhancing their problem-solving capabilities.
Evaluation Framework: OpenDevin includes a comprehensive evaluation framework with benchmarks to test agent performance across diverse tasks, such as software engineering, web browsing, and complex problem-solving.

3. Automated Design of Agentic Systems
The core idea of ADAS (Automated Design of Agentic Systems) is to automate the creation of powerful AI agents by leveraging a meta-agent to program new agents iteratively. The ADAS framework views agent design as an optimization process within a code-based search space. This allows the system to invent new agents, including various components such as prompts, tool usage, and control flows, thus aiming for a general-purpose and flexible agent system. Key points include:
Meta-Agent Search: ADAS uses a meta-agent to explore an ever-growing archive of previously discovered agents, iteratively generating new agents in code.
Turing Completeness: By defining agents in a Turing-complete language like Python, ADAS can, in theory, learn and discover any agentic system design.
Self-Improvement: The meta-agent can refine agents through iterative programming, testing, and archiving, leading to progressively better agents.
Generality and Robustness: Discovered agents show strong transferability across different domains and models, indicating that the system can create versatile agents that perform well beyond their training context.

4. PAL: Program-aided Language Models
5. CodeAct: Executable Code Actions Elicit Better LLM Agents
6. MindSearch: Mimicking Human Minds Elicits Deep AI Searcher
7. Diversity Empowers Intelligence: Integrating Expertise of Software Engineering Agents
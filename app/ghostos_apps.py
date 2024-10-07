from os.path import dirname, join
from ghostos.container import Container
from ghostos.contracts.logger import config_logging
from ghostos.providers import default_application_providers, application_contracts
from ghostos.prototypes.ghostfunc import init_ghost_func, GhostFunc
import dotenv
import os

# Core Concepts
#
# 1. Ghost and Shell
# We take the word `Ghost` from famous manga movie <Ghost In the Shell> as the abstract of an Agent.
# Ghost shall have concurrent thinking/action capabilities, each thought or task is a fragment of the Ghost mind;
# not like an independent agent in a multi-agent system.
# But you can take `Ghost` as `Agent` for now.
# Also, the word `Shell` in this project refers to the `Body` of the Agent,
# regardless if it is an Embodied Robot/IM chatbot/Website/IDE etc.
#
# 2. MOSS
# stands for "Model-oriented Operating System Simulation".
# - operating system: to operate an Agent's body (Shell), mind, tools.
# - model-oriented: the first class user of the OS is the brain of Ghost(AI models), not Human
# - simulation: we merely use python to simulate the OS, not create a real one.
# Instead of `JSON Schema Tool`, we provide a python code interface for LLMs through MOSS.
# The LLMs can read python context as prompt, then generate python code to do almost everything.
# MOSS can reflect the python module to prompt, and execute the generated python code within a specific python context.
#
# We are aiming to create Fractal Meta-Agent which can generate tools/libraries/Shells/
#
# 3. GhostOS
# Is an agent framework for developers like myself, to define/test/use/modify Model-based Agents.
# Not like MOSS which serve the Models (Large Language Model mostly),
# GhostOS is a framework works for me the Human developer.
#
# 4. Application
# Is the production built with GhostOS.
# There are light-weight applications like `GhostFunc` which is a python function decorator,
# and heavy applications like Streamlit app.
#
# todo: let the gpt4o or moonshot fix my pool english expressions above.



__all__ = [
    'app_dir', 'workspace_dir',

    # >>> container
    # GhostOS use IoC Container to manage dependency injections at everywhere.
    # IoCContainer inherit all the bindings from parent Container, and also able to override them.
    # The singletons in the container shall always be thread-safe.
    #
    # The containers nest in multiple levels like a tree:
    # - Application level (global static container that instanced in this file)
    # - GhostOS level (a GhostOS manage as many ghost as it able to)
    # - Ghost level (a Ghost is a instance frame of the Agent's thought)
    # - Moss level (each MossCompiler has it own container)
    # <<<

    # application level container (global static IoC container)
    'container',

    # >>> GhostFunc
    # is a test library, which is able to define dynamic code for a in-complete function.
    # We develop it for early experiments.
    # Check example_ghost_func.py
    # <<<
    'GhostFunc',
    'ghost_func',
]

# --- prepare application paths --- #

app_dir = dirname(__file__)
"""application root path"""

workspace_dir = join(app_dir, 'workspace')
"""workspace root path"""

logging_conf_path = join(workspace_dir, 'configs/logging.yml')
"""logging configuration file"""

# --- system initialization --- #

# load env from dotenv file
dotenv.load_dotenv(dotenv_path=join(app_dir, '.env'))

# default logger name for GhostOS application
logger_name = os.environ.get("LoggerName", "debug")

# initialize logging configs
config_logging(logging_conf_path)

# --- prepare application container --- #

container = Container()
"""application root static container"""

# get default application providers.
application_providers = default_application_providers(root_dir=app_dir, logger_name=logger_name)
# register application providers
container.register(*application_providers)

# validate the application contracts
application_contracts.validate(container)

# --- init ghost func decorator --- #

ghost_func: GhostFunc = init_ghost_func(container)
"""
ghost func is a function decorator, that produce dynamic codes and exec it for the function during calling
"""

# --- test the module by python -i --- #

if __name__ == '__main__':
    """
    run `python -i __init__.py` to interact with the current file
    """
    pass

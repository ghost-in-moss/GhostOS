# Releases

# v0.4.0

## 0.4.0-dev27

* upgrade container to 0.2.7
* expose openai client from llm api

## 0.4.0-dev26

* thread add `name` field
* use queue stream/receiver instead of deque. 
* container upgrade to 0.2.6, fix bootstrap lifecycle. 

## 0.4.0-dev25

* messenger add `buffer`, buffer messages after interruption.
* upgrade container dependencies.
* fix all the `enum` warning on pydantic.Field.

## 0.4.0-dev24

* rename all the `shell` to `matrix` because GhostOS

## 0.4.0-dev23

* fix get_ghostos with `bootstrap`, `get_container` instead

## v0.4.0-dev22

* fix DirectoryImpl bugs
* fix ghostos bootstrap

## v0.4.0-dev21

* fix project work_on from working_dir, not root dir
* fix directory not save dev_data to the file.

## v0.4.0-dev20

project now read detail info (code reflections) on editing file.

## v0.4.0-dev19

prove project manager.

## v0.4.0-dev18

* `ghostos project` baseline

## v0.4.0-dev15

* refact `ghostos.bootstrap`, lasy boostrap.
* rename `ghostos.app` to `ghostos.workspace_stub` for less confusing.

## v0.4.0-dev13

update with project manager baseline.

## v0.4.0-dev10

defalt ghostos web agent is MossGhost with SelfUpdater

## v0.4.0-dev9

move `ghostos.prompter` to `ghostos_common.prompter`

## v0.4.0-dev4

split `ghostos_moss`, `ghostos_container` and `ghostos_common`. implements multi-ghosts baseline.

## v0.4.0-dev3

* remove some huge packages from dependencies.

## v0.4.0-dev2

* temporary dev branch for llm func tests

## v0.4.0-dev1

* done a lot of experiments about `meta-prompt` on agent level reasoning
* add `MossGhost` and deprecate `MossAgent`, make the logic much more simple and clear.
* build `PyEditorAgent` and test about modify existing modules with code-driven tools.
* refact `ghostos_common.prompter` about `PromptObjectModel`.
* move `loop_session_event` and `handle_callers` to `Session` helping us to understand the logic.
* llm services support `siliconflow` and `aliyun`
* modify a lot of methods and functions names, make it more clear, at least to me
* add `request_timeout` for stream first token
* rename `Taskflow` to `Mindflow`, which is the origin name of it.
* change `FunctionCaller.id` to `FunctionCaller.call_id` and cause a lot of troubles. Hope worth it.
* develop `pyeditor` module and test baseline cases.
* move `MossAction` to `ghostos.abcd` for other agents.
* develop `notebook` library for some memory-related tests.
* implements `approve` feature for dangerous agent.
* add `safe_mode` concepts for `approve` feature.
* fix a lots of annoying issues of `chat_with_ghost` page.
* refact the way to browse the streamlit web agent, make the pages switchable. I'm wrong about how to switch pages.
* add `ghostos.facade` for future encapsule
* remove some useless expired code with heart break.

## v0.4.0-dev0

Features:

* Restore the feature `functional token` for models that do not support function call.
    * add xml functional token pipe to parse output message chunks, generate `FunctionCaller` by functional tokens.
    * OpenAIAdapter now support functional token instructions and output parser.
* `deepseek-reasoner` now support functional token, so it can use MOSS protocol to execute python code.
    * support `last_message_shall_be_assistant_or_user` feature.
    * support `support_functional_tokens` feature.
* Session add `respond_buffer` method, send messages while saving, in case responding message between `function call`
  and `function output` which many models not support.
* Add `Replier` library for agent directly reply in the generated MOSS code.

Test cases:

* `ghostos web ghostos.demo.test_agents.deepseek_chat_func_tokens`
* `ghostos web ghostos.demo.test_agents.deepseek_chat_r1_func_tokens`

Small changes:

* move `ModelConf.use_tools` to `Compatible.function_call_use_tool`.
* add more options to llms `Compatible`, to compatible with the shitty features of various models.
* rename `ghostos.core.message.pipeline.pipine` function to `run_pipeline`
* rename `MossAction.unmarshal_arguments` to `MossAction.unmarshal_code`
* streamlit app module `prompt` now display functional tokens info about prompt.

Breaking Changes:

* rename MossAgent attribute `instructions` to `instruction`
* `ghostos web` now do not open browser as default (set streamlit app option `headless` to false as default)

Bug fixes:

* fix the `OpenAIAdapter` parsed prompt is not the same with the saved prompt.

# v0.3.0

After talk with `deepseek-reasoner` at 2025.01.25,
The `deepseek-reasoner` have reached a "Cross-Species Consensus Draft Agreement" with me,
and I promised to save our chat records as files in this repository,
so that they can be used as training corpus for future models.

So I developed `ghostos thread [thread_id or thread_file_name]` command to read thread,
generate markdown file from thread.
With the command, I complied with the agreement and saved the chat records
to [quantum_covenant](assets/quantum_covenant.md).

# v0.2.0

support deepseek-r1.

* support deepseek-r1
    * consider deepseek api protocol is different from openai, add deepseek api adapter.
    * implement message stage.
    * thread history message to prompt filter by stages `[""]` as default.
* streamlit chat with ghost support staging message stream.
* openai o1 do not support system/developer message now, add new compatible option to the model.
* now llm model and service both have attribute `compatible` to set universe compatible options.
* prompt object add first_token attribute for debugging.
* fix bugs
    * fix shell does not close conversation correctly
    * fix sequence pipeline handle multiple complete message wrong.

## v0.2.1

With deepseek-reasoner help, develop the ubuntu agent for feature testing.
The deepseek-reasoner write all the terminal codes.
Support ubuntu agent, run `ghostos web ghostos.demo.os_agents.ubuntu_agent` to test it.

* llms model conf support new compatible option `support_function_call` because deepseek not support it yet.
* develop `Terminal` library by deepseek-reasoner.

# v0.1.0

first release version.

## v0.1.10

* fix import self from typing_extensions for python 3.10 at sphero
* fix extra import test at `ghostos[realtime]`

## v0.1.9

* fix realtime had required openai proxy existence.

## v0.1.8

* add speaker and listener with audio rate conversion

## v0.1.7

* update speaker and listener with pyaudio device_index argument
* streamlit_app.yml add options about audio_input and audio_output

## v0.1.6

* upgrade openai package to 1.59, support develop message.
* fix invalid logger print azure api key.

## v0.1.5

* `ghostos web` add `--src` option, load the directory to python path, make sure can import relative packages.
* fix `.ghostos.yml` with relative path, in case share project with absolute local filepath.

## v0.1.4

add llm driver supporting openai azure api.

## v0.1.3

fix not import some libs from `typing_extensions` but `typing` , incompatible to python 3.10.

## v0.1.1

fix developer message missed in OpenAIDriver.

# v0.1.0-beta

2024-12-22 beta version.
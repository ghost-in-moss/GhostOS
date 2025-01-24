# Releases

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
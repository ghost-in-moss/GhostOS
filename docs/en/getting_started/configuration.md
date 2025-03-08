# Configuration

Configuration files that `GhostOS` relies on are stored within the workspace.

Running `ghostos init` creates a workspace in the current directory.

The default workspace is located at: [ghostos/app](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app).

The default location for configuration files is
at: [ghostos/app/configs](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app/configs).

## Edit in UI

`GhostOS` default configuration items are defined through `pydantic.BaseModel`, hence it can automatically
generate `JSON Schema`.

The author has developed the
repository [streamlit-react-jsonschema](https://github.com/ghost-in-moss/streamlit-react-jsonschema), which is based
on [react-jsonschema-form](https://react-jsonschema-form.readthedocs.io/) for automated form rendering.

Running `ghostos config` opens a streamlit page where you can visually configure options.

> Since I don't have much time for testing, directly modifying the target configuration file is more reliable and
> secure.

## LLM Config

`GhostOS` encapsulates its
own [LLMs Interface](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/llms/abcd.py).

For related configuration items,
see [LLMsConfig](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/llms/configs.py).

The configuration file is located
at [\[workspace\]/configs/llms_conf.yml](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app/configs/llms_conf.yml).

The currently tested model services include:

- OpenAI
- Moonshot

Most Agents that do not specify model configurations directly will use the  `LLMConfigs.default` model.

## Realtime Beta Config

`GhostOS` support [OpenAI Realtime Beta](https://platform.openai.com/docs/api-reference/realtime).

Configuration Model of
it: [OpenAIRealtimeAppConfig](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/frameworks/openai_realtime/configs.py).

The config file
is [\[workspace\]/configs/openai_realtime_config.yml](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app/configs/openai_realtime_config.yml).

## Streamlit Config

The
file [ghostos/app/.streamlit/config.toml](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/.streamlit/config.toml)
is the Streamlit configuration that is read when running `ghostos web`.

For details on how to modify them,
see [streamlit configuration](https://docs.streamlit.io/en/latest/advanced-features/configuration.html).
# Configuration

`GhostOS` 依赖的配置文件都会存在 workspace 中.
运行 `ghostos init` 可以在当前目录创建 workspace.
系统默认的 workspace 在: [ghostos/app](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app).

而配置文件默认地址在 [ghostos/app/configs](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app/configs).

## Edit in UI

`GhostOS` 默认的配置项都是通过 `pydantic.BaseModel` 定义的, 所以可以自动生成 `JSON Schema`.
作者开发了仓库 [streamlit-react-jsonschema](https://github.com/ghost-in-moss/streamlit-react-jsonschema),
基于 [react-jsonschema-form](https://react-jsonschema-form.readthedocs.io/) 自动化渲染表单.

运行 `ghostos config` 会打开一个 streamlit 的页面, 可以可视化配置选项.

> 由于我没有多少时间做测试, 所以直接修改目标配置文件更加安全可靠.

## LLM Config

`GhostOS` 封装了自己的 [LLMs](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/llms/abcd.py).
相关配置项详见 [LLMsConfig](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/core/llms/configs.py).

配置文件在 [\[workspace\]/configs/llms_conf.yml](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app/configs/llms_conf.yml).

目前经过反复测试的模型服务有: 

- OpenAI
- Moonshot

大多数没有直接指定模型配置的 Agent, 会直接使用这里 `LLMConfigs.default` 的模型配置项. 

## Realtime Beta Config

`GhostOS` 支持了 [OpenAI Realtime Beta](https://platform.openai.com/docs/api-reference/realtime).
相关配置项详见 [LLMsConfig](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/frameworks/openai_realtime/configs.py).

配置文件在 [\[workspace\]/configs/openai_realtime_config.yml](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/app/configs/openai_realtime_config.yml).

## Streamlit Config

文件 [ghostos/app/.streamlit/config.toml](https://github.com/ghost-in-moss/GhostOS/tree/main/libs/ghostos/ghostos/.streamlit/config.toml)
是运行 `ghostos web` 时读取的 streamlit 配置项.

修改它们的方式详见 [streamlit configuration](https://docs.streamlit.io/develop/concepts/configuration).
# Installation

## Cli

还在测试中. 

## From GitHub

下载 GhostOS 仓库. 
```bash
git clone https://github.com/ghost-in-moss/GhostOS.git 
cd GhostOS # 进入目标目录
```

创建 python3 (>=3.10) 虚拟环境.
Mac 电脑举例如下: 
```bash
python3 -m venv venv
source venv/bin/activate
```

虚拟环境里安装 Poetry

```bash
python -m pip install poetry
```

使用 poetry 安装依赖库 
```bash
poetry install
```

配置 OpenAI 的 api-key:
```bash
export OPENAI_API_KEY="your openai api key"
# export OPENAI_PROXY="your proxy if necessary"  
```

或者修改 `.env` 文件, 根据文件提示配置: 
```bash
copy workspace/.example.env workspace/.env
vim workspace/.env # 修改默认的环境变量
```

运行测试:
```bash
poetry run ghost examples/agents/jojo.py
```

正常的话应该启动了 Streamlit Web 页面, 并且可以对话. 

接下来可以使用 `poetry run ghost` 某一个可以独立运行的 python 文件, 将之直接变成 Web Agent, 并可以要求 Agent 调用文件中的函数. 

> 当前版本, 所有的运行时临时数据, 比如对话历史, 都会存储到 `workspace/runtime` 目录下.
> 想要清空这些临时文件, 需要运行 `poetry run clear_runtime -a`
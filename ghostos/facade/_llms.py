from ghostos.core.llms import LLMsConfig


def get_llm_configs() -> LLMsConfig:
    from ghostos.core.llms import LLMs
    from ghostos.bootstrap import get_container
    llms = get_container().force_fetch(LLMs)
    return llms.config


def set_default_model(model_name: str):
    get_llm_configs().default = model_name

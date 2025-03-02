from typing import Optional, List, Dict
from ghostos.core.llms import LLMsConfig, LLMs, ModelConf, LLMApi


def get_llms(config: Optional[LLMsConfig] = None) -> LLMs:
    from ghostos.bootstrap import get_container
    from ghostos.core.llms import LLMs
    llms = get_container().force_fetch(LLMs)
    if config is not None:
        llms.update(config)
    return llms


def get_llm_api(api_name: str = "", model: Optional[ModelConf] = None) -> LLMApi:
    """
    get llm api from ghostos.
    :param api_name: the llm api name in LLMsConfig
    :param model: the ModelConf object
    :return: LLMApi
    """
    llms = get_llms()
    if model is None:
        return llms.get_api(api_name)
    api_name = api_name if api_name else model.model
    return llms.new_model_api(model, api_name)


def get_llm_configs() -> LLMsConfig:
    llms = get_llms()
    return llms.config


def set_default_model(model_name: str):
    get_llm_configs().default = model_name


def get_llm_api_info() -> List[Dict]:
    """
    get all the llm api simple description
    """
    configs = get_llm_configs()
    result = []
    for api_name, model in configs.models.items():
        result.append(dict(
            api_name=api_name,
            model_name=model.model,
            description=model.description,
        ))
    return result

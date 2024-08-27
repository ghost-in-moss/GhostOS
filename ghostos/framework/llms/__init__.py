from ghostos.framework.llms.llms import LLMsImpl
from ghostos.framework.llms.openai_driver import OpenAIDriver, OpenAIAdapter, LitellmAdapter
from ghostos.framework.llms.providers import ConfigBasedLLMsProvider


default_llms_provider = ConfigBasedLLMsProvider("llms/llms_conf.yaml")
"""default llms provider based by configs contract """



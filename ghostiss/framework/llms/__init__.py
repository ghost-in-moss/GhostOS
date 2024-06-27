from ghostiss.framework.llms.llms import LLMsImpl
from ghostiss.framework.llms.openai_driver import OpenAIDriver, OpenAIAdapter
from ghostiss.framework.llms.providers import ConfigBasedLLMsProvider


default_llms_provider = ConfigBasedLLMsProvider("llms/llms_conf.yaml")
"""default llms provider based by configs contract """



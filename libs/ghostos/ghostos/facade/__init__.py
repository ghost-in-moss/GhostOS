from ghostos.facade._llms import (
    get_llm_configs,  # get the ghostos llms config
    set_default_model,  # set the default model to llms, only work during runtime
    get_llm_api_info,
    get_llms,
    get_llm_api,
)

from ghostos.facade._contracts import (
    get_logger,  # get ghostos logger
)

from ghostos.facade._model_funcs_facade import (
    text_completion,  #
    file_reader,
)

# ghostos.facade is a composer of all the application level functions.
# easy to use, but more likely are the tutorials of how to use ghostos
# ghostos 内部所有模块都不能依赖 facade.

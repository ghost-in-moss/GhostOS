from ghostos.prototypes.aifunc import quick_run_aifunc
from ghostos.demo.src.aifuncs.agentic import AgentFn
from ghostos.helpers import yaml_pretty_dump

if __name__ == '__main__':
    fn = AgentFn(
        request="please tell me the weather in beijing today, and I want to know the news about OpenAI model o1",
    )

    result = quick_run_aifunc(fn, current_path=__file__, dirname_times=3, debug=True)
    print(result)
    print(yaml_pretty_dump(result.model_dump(exclude_defaults=True)))

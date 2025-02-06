from ghostos.core.model_funcs.abcd import LLMModelFunc, R
from ghostos.core.llms import Prompt
from ghostos.core.runtime.threads import GoThreadInfo
from pydantic import Field

__all__ = ['TruncateThreadByLLM']


class TruncateThreadByLLM(LLMModelFunc[GoThreadInfo]):
    """
    simple summary thought
    """

    thread: GoThreadInfo = Field(description="the target thread")
    llm_api: str = Field("", description="the llm api to use")
    instruction: str = Field(
        "the chat history is too long. "
        "You MUST summarizing the history message in 500 words, keep the most important information."
        "Your Summary:",
        description="the llm instruction to use",
    )
    truncate_at_turns: int = Field(40),
    reduce_to_turns: int = Field(20),

    def run(self) -> R:
        thread = self.thread
        turns = thread.get_history_turns(truncate=True)
        # do the truncate
        if len(turns) > self.truncate_at_turns:
            # the history turns to remove
            truncated = self.truncate_at_turns - self.reduce_to_turns
            if truncated <= 0:
                return thread
            turns = turns[:truncated]
            # last turn of the truncated turns
            if len(turns) < 1:
                return thread
            target = turns[-1]
            messages = []
            for turn in turns:
                messages.extend(turn.messages(False))
            prompt = Prompt(history=messages)
            summary = self._generate_from_prompt(prompt)
            if summary:
                target.summary = summary
        return thread

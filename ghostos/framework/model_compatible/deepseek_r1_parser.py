from typing import List

from ghostos.core.llms import MessagesCompatibleParser
from ghostos.core.messages import Message, MessageType, FunctionCallMessage, FunctionCallOutputMessage, Role


class DeepseekR1SupportFunctionParser(MessagesCompatibleParser):
    """
    deepseek r1 not support messages other than `user` and `assistant`
    we need to:
    1. filter other messages.
    2. change compatible messages to user message.
    3. combine user / assistant messages.
    4. last message shall be user.
    """

    def parse(self, messages: List[Message]) -> List[Message]:
        if len(messages) == 0:
            return []

        first_message = messages[0]
        outputs = []
        if Role.is_system(first_message.role):
            outputs.append(first_message)
            messages = messages[1:]

        last_message = None

        for message in messages:
            if not message.is_complete():
                continue
            if message.stage:
                continue

            if message.type == MessageType.FUNCTION_CALL.value:
                callerMsg = FunctionCallMessage.from_message(message)
                if callerMsg is None:
                    continue
                caller = callerMsg.caller

                if caller.functional_token:
                    # functional token message do not need to add new one.
                    continue

                content = f"> run function call `{caller.name}`, arguments: `{caller.arguments}`"
                new_message = Role.USER.new(
                    content=content,
                    name="__function_call__",
                    msg_id=message.msg_id,
                )
                message = new_message

            elif message.type == MessageType.FUNCTION_OUTPUT.value:
                output_msg = FunctionCallOutputMessage.from_message(message)
                if output_msg is None:
                    continue
                content = f"> receive function output of `{output_msg.name}`:\n\n{output_msg.content}"
                new_message = Role.USER.new(
                    content=content,
                    name="__function_output__",
                    msg_id=message.msg_id,
                )
                message = new_message

            else:
                # not compatible.
                # ignored now
                # todo: define them later
                continue

            if last_message is None:
                last_message = message
                continue
            elif last_message.role == message.role:
                # 合并同类消息.
                last_message.content = last_message.get_content() + "\n\n" + message.get_content()
            else:
                outputs.append(last_message)
                last_message = message
        if last_message is not None:
            outputs.append(last_message)
        return outputs


deepseek_reasoner_support_functions = DeepseekR1SupportFunctionParser()

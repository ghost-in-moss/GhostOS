from typing import Union, List, Dict

from ghostos.abcd import Operator, Session, Ghost, Matrix
from ghostos.core.runtime import GoTaskStruct, EventTypes, GoThreads
from ghostos.core.messages import Message, Role
from ghostos_common.identifier import get_identifier
from ghostos_common.helpers import md5


class PublicChatOperator(Operator):

    def __init__(self, *, topic: str, hostname: str, message: str, ghosts: List[Ghost]):
        self.topic = topic
        self.hostname = hostname
        self.message = message
        self.ghosts = ghosts

    def get_ghost_task_id(self, session: Session, ghost: Ghost) -> str:
        name = get_identifier(ghost).name
        return md5(f"multi-ghosts:session:{session.task.task_id}:topic:{self.topic}:ghost_name:{name}")

    def run(self, session: Session) -> Union[Operator, None]:

        host_message = Role.USER.new(
            content=self.message,
            name=self.hostname,
        )
        shell = session.container.force_fetch(Matrix)
        conversations = {}
        threads = {}
        added = []
        for ghost in self.ghosts:
            task_id = self.get_ghost_task_id(session, ghost)
            conversation = shell.sync(ghost, task_id=task_id)
            conversations[task_id] = conversation
            # get the task thread
            thread = conversation.get_thread()
            # copy it.
            thread = thread.thread_copy()
            event = EventTypes.INPUT.new(task_id=task_id, messages=[host_message])
            thread.new_turn(event)
            threads[task_id] = thread

        for task_id, conversation in conversations.items():
            messages = [host_message]
            messages.extend(added)
            event = EventTypes.INPUT.new(task_id=task_id, messages=messages)
            receiver = conversation.respond_event(event, streaming=session.allow_streaming())
            # reply by current session
            messages, callers = session.respond(receiver.recv())
            added.extend(messages)

        for thread in threads.values():
            thread.last_turn().added = added
        session.save_threads(*threads.values())
        return session.mindflow().wait()

    def destroy(self):
        del self.ghosts

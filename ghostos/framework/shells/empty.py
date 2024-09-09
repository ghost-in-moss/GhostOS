from ghostos.framework.shells.basic import BasicShell


class EmptyShell(BasicShell):

    def __init__(self):
        super().__init__(
            shell_id="empty_shell",
            prompt="",
            actions=[],
            drivers=[]
        )

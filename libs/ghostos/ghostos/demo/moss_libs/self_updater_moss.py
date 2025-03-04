from ghostos_moss.abcd import SelfUpdater, Moss as Parent


class Moss(Parent):
    updater: SelfUpdater
    """update current module code"""

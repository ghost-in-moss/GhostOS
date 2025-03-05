from ghostos_moss.abcd import SelfUpdater, Moss as Parent


class Moss(Parent):
    updater: SelfUpdater
    """
    update current module code.
    notice, only the code string used by updater will change the current module's code. 
    if you define a function or class in your generation, it will not be existed next round. 
    """

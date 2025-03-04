from ghostos_moss.abcd import Moss as Parent, SelfUpdater


class Moss(Parent):
    updater: SelfUpdater

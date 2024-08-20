from typing import Type
from ghostiss.core.quests.itf import Quest, QuestDriver
from ghostiss.helpers import generate_import_path, import_from_path

__all__ = ['get_quest_driver']


def get_quest_driver(cls: Type[Quest]) -> Type[QuestDriver]:
    """
    基于约定, 通过一个 Quest 的类, 获取它的 Driver类.
    """
    driver = cls.__quest_driver__
    if driver is not None:
        return driver
    import_path = generate_import_path(cls)
    splits = import_path.split('.')
    splits[-1] = splits[-1] + "Driver"
    real_path = '.'.join(splits)
    value = import_from_path(real_path)
    if not issubclass(value, QuestDriver):
        raise ValueError(f"expected driver class '{real_path}' is not a quest driver")
    return value

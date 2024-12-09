import struct
from spherov2.commands.sensor import Sensor, CollisionDetected

__all__ = ["SpheroEduAPI", "SpheroEventType", "Color", "scanner"]


def __collision_detected_notify_helper(listener, packet):
    """
    解决 Spherov2 解码 bolt 的 bug?
    """
    unpacked = struct.unpack('>3hB3hBH', packet.data)
    listener(CollisionDetected(acceleration_x=unpacked[0] / 4096, acceleration_y=unpacked[1] / 4096,
                               acceleration_z=unpacked[2] / 4096, x_axis=bool(unpacked[3] & 1),
                               y_axis=bool(unpacked[3] & 2), power_x=unpacked[4], power_y=unpacked[5],
                               power_z=unpacked[6], speed=unpacked[7], time=unpacked[8] / 1000))


Sensor.collision_detected_notify = (24, 18, 0xff), __collision_detected_notify_helper

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI as Api, EventType as SpheroEventType, Color


class SpheroEduAPI(Api):

    def get_animation_id(self) -> int:
        _id = self.__animation_index - 1
        if _id < 0:
            return 0
        return _id

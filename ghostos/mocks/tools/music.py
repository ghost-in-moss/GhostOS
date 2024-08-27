from __future__ import annotations
from typing import List
from ghostos.core.moss_p1.exports import Exporter


# fake a music player
class MusicPlayer:
    """
    useful to play music for the user
    """

    def search(self, desc: str, *keywords: str) -> List[str]:
        """
        search music by description and keywords
        :param desc: description of the song
        :param keywords: keyword about the song that could be artist or song name etc.
        :return: list of song names
        """
        return ["七里香", "七里巴厘"]

    def play(self, name: str) -> bool:
        """
        play a music
        :param name: name of the music
        :return: weather the music is playing
        """
        return True


EXPORTS = Exporter().attr("player", MusicPlayer(), MusicPlayer)

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Union
from pydantic import BaseModel, Field
from ghostos.contracts.storage import Storage
from ghostos.helpers import uuid, yaml_pretty_dump
import yaml


class ImageInfo(BaseModel):
    image_id: str = Field(default_factory=uuid, description="ID of the image.")
    filename: str = Field(description="The file name of the image.")
    description: str = Field(default="", description="The description of the image.")
    filetype: str = Field(default="", description="The file type of the image.")
    url: Optional[str] = Field(default=None, description="The URL of the image.")


class ImagesAsset(ABC):

    @abstractmethod
    def save(self, image: ImageInfo, binary: Optional[bytes]) -> str:
        """
        save image info and binary data to storage
        :param image: the image info
        :param binary: binary data of the image. if None, the url must be provided
        :return: relative file path of the saved image
        """
        pass

    @abstractmethod
    def get_binary(self, filename: str) -> Optional[bytes]:
        """
        get binary data of the image
        :param filename: the relative filename of the image
        :return: binary data of the image, None if binary data is not available
        """
        pass

    @abstractmethod
    def get_image_info(self, image_id: str) -> Optional[ImageInfo]:
        """
        get image info from storage
        :param image_id: the image id
        :return: None if no image info is available
        """
        pass

    def get_binary_by_id(self, image_id: str) -> Optional[Tuple[ImageInfo, Union[bytes, None]]]:
        """
        get binary data by image id
        :param image_id: the image info id.
        :return: image info and binary data, if binary data is None, means the image has url.
        """
        image_info = self.get_image_info(image_id)
        if image_info is None:
            return None
        return image_info, self.get_binary(image_info.filename)


class StorageImagesAsset(ImagesAsset):

    def __init__(self, storage: Storage):
        self._storage = storage

    @staticmethod
    def _get_image_info_filename(image_id: str) -> str:
        return f"{image_id}.yml"

    def save(self, image: ImageInfo, binary: Optional[bytes]) -> str:
        if binary is None and image.url is None:
            raise AttributeError("failed to save image: binary is None and image info is not from url.")
        image_info_filename = self._get_image_info_filename(image.image_id)
        data = image.model_dump(exclude_none=True)
        content = yaml_pretty_dump(data)
        self._storage.put(image_info_filename, content.encode())
        if binary:
            self._storage.put(image.filename, binary)

    def get_binary(self, filename: str) -> Optional[bytes]:
        if self._storage.exists(filename):
            return self._storage.get(filename)
        return None

    def get_image_info(self, image_id: str) -> Optional[ImageInfo]:
        image_info_filename = self._get_image_info_filename(image_id)
        if not self._storage.exists(image_info_filename):
            return None
        content = self._storage.get(image_info_filename)
        data = yaml.safe_load(content)
        return ImageInfo(**data)

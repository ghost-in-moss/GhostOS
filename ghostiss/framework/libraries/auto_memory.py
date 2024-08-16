import os

from abc import ABC, abstractmethod
from typing import List, Dict

from pydantic import BaseModel, Field

from mem0 import Memory


class DBConfig(BaseModel):
    path: str = Field(description="Path to the database file", default="memory.db")


class VectorDBConfig(BaseModel):
    provider: str = Field(description="Provider of the vector store (e.g., 'qdrant', 'chroma')", default="qdrant")


class ProxyConfig(BaseModel):
    proxy_url: str = Field(description="Proxy URL", default=None)


class TextMemory(ABC):
    """
    TextMemory Storage enhances AI assistants and agents with an intelligent memory layer, enabling personalized AI interactions
    """

    def __init__(self, proxy_config: ProxyConfig):
        if proxy_config and proxy_config.proxy_url:
            os.environ['http_proxy'] = proxy_config.proxy_url
            os.environ['https_proxy'] = proxy_config.proxy_url

    @abstractmethod
    def add(self, data: str, agent_id=None, run_id=None, metadata=None, filters=None, prompt=None):
        """
        Create a new memory.

        Args:
            data (str): Data to store in the memory.
            agent_id (str, optional): ID of the agent creating the memory. Defaults to None.
            run_id (str, optional): ID of the run creating the memory. Defaults to None.
            metadata (dict, optional): Metadata to store with the memory. Defaults to None.
            filters (dict, optional): Filters to apply to the search. Defaults to None.
            prompt (str, optional): Prompt to use for memory deduction. Defaults to None.

        Returns: None
        """
        pass

    @abstractmethod
    def search(self, query, agent_id=None, run_id=None, limit=100, filters=None) -> List[Dict]:
        """
        Search for memories.

        Args:
            query (str): Query to search for.
            agent_id (str, optional): ID of the agent to search for. Defaults to None.
            run_id (str, optional): ID of the run to search for. Defaults to None.
            limit (int, optional): Limit the number of results. Defaults to 100.
            filters (dict, optional): Filters to apply to the search. Defaults to None.

        Returns:
            list: List of search results.
        """
        pass

    @abstractmethod
    def get(self, memory_id):
        """
        Retrieve a memory by ID.

        Args:
            memory_id (str): ID of the memory to retrieve.

        Returns:
            dict: Retrieved memory.
        """
        pass

    @abstractmethod
    def get_all(self, agent_id=None, run_id=None, limit=100):
        """
        List all memories.

        Returns:
            list: List of all memories.
        """
        pass

    @abstractmethod
    def update(self, memory_id, data):
        """
        Update a memory by ID.

        Args:
            memory_id (str): ID of the memory to update.
            data (dict): Data to update the memory with.

        Returns:
            dict: Updated memory.
        """
        pass

    @abstractmethod
    def delete(self, memory_id):
        """
        Delete a memory by ID.

        Args:
            memory_id (str): ID of the memory to delete.
        """
        pass

    @abstractmethod
    def delete_all(self, agent_id=None, run_id=None):
        """
        Delete all memories.

        Args:
            agent_id (str, optional): ID of the agent to delete memories for. Defaults to None.
            run_id (str, optional): ID of the run to delete memories for. Defaults to None.
        """
        pass

    @abstractmethod
    def history(self, memory_id):
        """
        Get the history of changes for a memory by ID.

        Args:
            memory_id (str): ID of the memory to get history for.

        Returns:
            list: List of changes for the memory.
        """
        pass

    @abstractmethod
    def clear(self):
        """
        Clear the memory store.
        """
        pass


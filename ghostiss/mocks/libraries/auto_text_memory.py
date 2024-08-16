from typing import Dict

from mem0 import Memory
from mem0.configs.base import MemoryConfig, LlmConfig, VectorStoreConfig
from ghostiss.framework.libraries.auto_memory import TextMemory, ProxyConfig, VectorDBConfig, DBConfig


class Mem0TextMemory(TextMemory):

    def __init__(self, proxy_config: ProxyConfig = None, llm_config: Dict = None, vector_config: VectorDBConfig = None, db_config: DBConfig = None):
        super().__init__(proxy_config)

        conf = MemoryConfig()
        if llm_config:
            conf.llm = LlmConfig(provider=llm_config["llm_provider"])
        if vector_config:
            conf.vector_store = VectorStoreConfig(provider=vector_config.provider)
        if db_config:
            conf.history_db_path = db_config.path
        self.memory = Memory(conf)

    def add(self, data, agent_id=None, run_id=None, metadata=None, filters=None, prompt=None):
        # Implement the add method
        self.memory.add(data, agent_id=agent_id, run_id=run_id, metadata=metadata, filters=filters, prompt=prompt)

    def search(self, query, agent_id=None, run_id=None, limit=100, filters=None):
        return self.memory.search(query, agent_id=agent_id, run_id=run_id, limit=limit, filters=filters)

    def get(self, memory_id):
        return self.memory.get(memory_id)

    def get_all(self, agent_id=None, run_id=None, limit=100):
        return self.memory.get_all(agent_id=agent_id, run_id=run_id, limit=limit)

    def update(self, memory_id, data):
        return self.memory.update(memory_id, data)

    def delete(self, memory_id):
        return self.memory.delete(memory_id)

    def delete_all(self, agent_id=None, run_id=None):
        return self.memory.delete_all(agent_id=agent_id, run_id=run_id)

    def history(self, memory_id):
        return self.memory.history(memory_id)

    def clear(self):
        return self.memory.reset()

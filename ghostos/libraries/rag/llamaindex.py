
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("YOUR_DATA_DIRECTORY").load_data()
index = VectorStoreIndex.from_documents(documents)
index.update()
index.insert()
engine = index.as_query_engine()
engine.query()
index.storage_context.persist()
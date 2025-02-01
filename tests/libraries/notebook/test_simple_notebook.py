from ghostos.libraries.notebook.cache_notebook import SimpleNotebookImpl, NotebookConfig


def test_simple_notebook_baseline():
    from ghostos.framework.storage.memstorage import MemStorage
    notebook = SimpleNotebookImpl(
        "test",
        storage=MemStorage(),
        config=NotebookConfig(),
    )

    notebook.add_memo("todo", "hello")
    notebook.add_memo("todo", "world")

    assert "hello" in notebook.dump_context()
    assert "world" in notebook.dump_context()

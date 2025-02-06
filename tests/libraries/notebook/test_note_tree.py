from ghostos.libraries.notebook.cache_notebook import NoteTree, Note


def test_add_note_to_empty_tree():
    root = NoteTree(Note(path="", description="", content=""))
    new_note = Note(path="note1", description="First note", content="Content of first note")
    root.add_note(new_note)
    assert "note1" in root.children
    assert root.children["note1"].note.description == "First note"


def test_add_note_with_subpath():
    root = NoteTree(Note(path="", description="", content=""))
    new_note = Note(path="folder/note1", description="Nested note", content="Content of nested note")
    root.add_note(new_note)
    assert "folder" in root.children
    assert "note1" in root.children["folder"].children
    assert root.children["folder"].children["note1"].note.content == "Content of nested note"


def test_get_node_non_existent():
    root = NoteTree(Note(path="", description="", content=""))
    result = root.get_node("nonexistent/path")
    assert result is None


def test_get_node_existent():
    root = NoteTree(Note(path="", description="", content=""))
    new_note = Note(path="folder/note1", description="Nested note", content="Content of nested note")
    root.add_note(new_note)
    result = root.get_node("folder/note1")
    assert result is not None
    assert result.note.content == "Content of nested note"


def test_list_notes_empty():
    root = NoteTree(Note(path="", description="", content=""))
    result = root.list_notes()
    assert result == ""


def test_list_notes_with_hierarchy():
    root = NoteTree(Note(path="", description="", content=""))
    note1 = Note(path="folder1", description="Folder 1", content="Content of folder 1")
    note2 = Note(path="folder1/note1", description="Note 1 in folder 1", content="Content of note 1 in folder 1")
    note3 = Note(path="folder2", description="Folder 2", content="Content of folder 2")
    root.add_note(note1)
    root.add_note(note2)
    root.add_note(note3)
    result = root.list_notes()
    expected_result = "+ folder1\n  - note1\n- folder2"
    assert result == expected_result, (result, expected_result)


def test_add_note_same_path_overwrites():
    root = NoteTree(Note(path="", description="", content=""))
    first_note = Note(path="note", description="Original", content="Original content")
    second_note = Note(path="note", description="Updated", content="Updated content")
    root.add_note(first_note)
    root.add_note(second_note)
    assert root.children["note"].note.content == "Updated content"


def test_list_notes_single_note():
    root = NoteTree(Note(path="", description="", content=""))
    note1 = Note(path="note1", description="Single note", content="Content of single note")
    root.add_note(note1)
    result = root.list_notes()
    expected_result = "- note1"
    assert result == expected_result


def test_list_notes_deep_hierarchy():
    root = NoteTree(Note(path="", description="", content=""))
    note1 = Note(path="folder1/folder2/folder3/note1", description="Deeply nested note", content="Deep content")
    root.add_note(note1)
    result = root.list_notes(depth=4)
    expected_result = "+ folder1\n  + folder2\n    + folder3\n      - note1"
    assert result == expected_result


def test_list_notes_multiple_notes_same_level():
    root = NoteTree(Note(path="", description="", content=""))
    note1 = Note(path="folder1/note1", description="Note 1", content="Content of note 1")
    note2 = Note(path="folder1/note2", description="Note 2", content="Content of note 2")
    root.add_note(note1)
    root.add_note(note2)
    result = root.list_notes()
    expected_result = "+ folder1\n  - note1\n  - note2"
    assert result == expected_result

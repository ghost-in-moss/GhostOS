if __name__ == '__main__':
    from ghostos.prototypes.console import new_console_app
    from ghostos.thoughts import DirectoryEditorThought
    from os.path import dirname

    app = new_console_app(__file__, 4)
    app.run_thought(
        DirectoryEditorThought(
            directory=dirname(dirname(__file__)),
            debug=True,
        ),
        instruction="please help me to read the .py files in code_edits directory, "
                    "and replace the chinese code comments you found to english.",
    )

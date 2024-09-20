if __name__ == '__main__':
    from ghostos.prototypes.console import quick_new_console_app
    from ghostos.thoughts import DirectoryEditorThought
    from os.path import dirname

    app = quick_new_console_app(__file__, 4)
    app.run_thought(
        DirectoryEditorThought(
            directory=dirname(dirname(__file__)),
            debug=True,
        ),
        instruction="please checkout content of the `.py` files in code_edits directory, "
                    "and translate the comments in  chinese into english if you found them in the code.",
    )

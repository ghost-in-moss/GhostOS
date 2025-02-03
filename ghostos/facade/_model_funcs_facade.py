def text_completion(text: str) -> str:
    """
    complete the text by llm
    :param text: the text to complete
    """
    from ghostos.core.model_funcs.llms_model_funcs import TextCompletion
    return TextCompletion(text=text).run()


def file_reader(filename: str, question: str) -> str:
    """
    read a file and answer the question about the file by llm
    :param filename: absolute path of the file, or the path relative to the pwd
    :param question: the question to ask
    :return:
    """
    from ghostos.core.model_funcs.llms_model_funcs import FileReader
    return FileReader(filename=filename, question=question).run()

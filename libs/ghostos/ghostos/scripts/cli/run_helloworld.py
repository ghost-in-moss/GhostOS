from sys import argv
from os.path import dirname, join


def main():
    """
    test start streamlit and pass value
    :return:
    """
    from ghostos.prototypes.streamlitapp import cli
    from streamlit.web.cli import main_run
    args = argv[1:]
    filename = join(dirname(cli.__file__), "helloworld.py")
    args.insert(0, filename)
    main_run(args)

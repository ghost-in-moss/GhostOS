import os
import yaml
from logging.config import dictConfig


def prepare_logger():
    demo_dir = os.path.abspath(os.path.dirname(__file__) + "/../../demo")
    conf_path = os.path.join(demo_dir, "ghostos/configs/logging.yaml")
    conf_path = os.path.abspath(conf_path)
    with open(conf_path) as f:
        content = f.read()
    data = yaml.safe_load(content)
    dictConfig(data)

import streamlit as st
from ghostos.prototypes.streamlitapp.utils.session import ModelSingleton
from pydantic import BaseModel, Field


class AppConf(ModelSingleton):
    name: str = "GhostOS"
    default_lang: str = "en"

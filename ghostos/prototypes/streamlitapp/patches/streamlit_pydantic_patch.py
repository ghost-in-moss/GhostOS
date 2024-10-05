from pydantic_settings import BaseSettings
import pydantic

pydantic.BaseSettings = BaseSettings

# after pydantic patch
import streamlit_pydantic

__all__ = [
    'streamlit_pydantic'
]

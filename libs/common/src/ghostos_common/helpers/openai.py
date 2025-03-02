def get_openai_key() -> str:
    import os
    return os.environ.get("OPENAI_API_KEY", "")

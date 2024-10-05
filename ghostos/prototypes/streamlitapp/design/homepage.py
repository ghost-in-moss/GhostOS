import streamlit as st

pages = {
    # 需要有系统自带的 bots.
    "GhostOS": [
        st.Page(
            "home/ghostos_bot.py",
            icon=":material/robot:",
            title="Host Bot",
            default=True,
        ),
        st.Page(
            "home/docs.py",
            title="Documents",
            icon=":material/book:",
        ),
        st.Page(
            "home/home.py",
            title="Readme",
            icon=":material/home:",
        ),
        st.Page(
            "home/configs.py",
            title="Configs",
            icon=":material/home:",
        ),
        st.Page(
            "home/tools.py",
            title="Tools",
            icon=":material/control_point:",
        ),
    ],
    "Applications": [
        st.Page(
            "apps/chatbots.py",
            title="ChatBots",
            icon=":material/chat:",
        ),
        st.Page(
            "apps/autobots.py",
            title="Autonomous Bots",
            icon=":material/chat:",
        ),
        st.Page(
            "apps/code_project.py",
            title="Project Manager",
            icon=":material/chat:",
        ),
        st.Page(
            "apps/talk_to_files.py",
            title="Talk to Files",
            icon=":material/description:",
        ),
        st.Page(
            "apps/streamlit_app.py",
            title="Streamlit Expert",
            icon=":material/description:",
        ),
        st.Page(
            "apps/talk_to_db.py",
            title="Talk to Database",
            icon=":material/database:",
        ),
    ],
    "Resources": [
        st.Page(
            "resources/llms.py",
            title="Large Language Models",
            icon=":material/database:",
        ),
        st.Page(
            "resources/moss_files.py",
            title="Moss Files",
            icon=":material/functions:",
        ),
        st.Page(
            "resources/ai_funcs.py",
            title="AI Functions",
            icon=":material/functions:",
        ),
        st.Page(
            "resources/thoughts.py",
            title="Thoughts",
            icon=":material/functions:",
        ),
        st.Page(
            "resources/libraries.py",
            title="Libraries",
            icon=":material/functions:",
        ),
        st.Page(
            "resources/knowledge.py",
            title="Knowledge",
            icon=":material/functions:",
        ),
        st.Page(
            "resources/data_objects.py",
            title="Data Objects",
            icon=":material/database:",
        ),
    ],
}


ng = st.navigation(
    pages,
    expanded=False,
)

ng.run()


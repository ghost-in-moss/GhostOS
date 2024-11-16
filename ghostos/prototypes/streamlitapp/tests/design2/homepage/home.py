import streamlit as st
import streamlit_antd_components as sac

st.title("GhostOS")
with st.expander(label="Introduction"):
    st.markdown("hello world")
with st.expander(label="How to"):
    st.markdown("hello world")

with st.container(border=True):
    st.subheader("Page links for test")
    st.page_link(
        "aifuncs/index.py",
        label="AI Functions",
        use_container_width=True,
    )

with st.container(border=True):
    st.subheader("Navigation")
    label = sac.menu([
        sac.MenuItem(
            'Home',
            icon='house-fill',
            children=[
                sac.MenuItem("Host", icon="robot", description="GhostOS official chatbot"),
                sac.MenuItem("Documents", icon="book-fill", description="guide book"),
                sac.MenuItem("Settings", icon="gear-fill", description="configs"),
                sac.MenuItem("Tools", icon="hammer", description="System scripts"),
            ],
        ),
        sac.MenuItem('Applications', icon='box-fill', children=[
            sac.MenuItem('ChatBots', icon='chat-dots'),
            sac.MenuItem('AIFuncs', icon='code-square'),
        ]),
        sac.MenuItem('Resources', icon='database-fill-gear', children=[
            sac.MenuItem('LLMs', icon='heart-fill'),
            sac.MenuItem('Moss Files', icon='heart-fill'),
            sac.MenuItem('Thoughts', icon='heart-fill'),
            sac.MenuItem('Registry', icon='heart-fill'),
            sac.MenuItem('Knowledge', icon='heart-fill'),
            sac.MenuItem('Data Objects', icon='heart-fill'),
        ]),
    ], open_all=True, index=0, variant="left-bar")
    st.write(label)

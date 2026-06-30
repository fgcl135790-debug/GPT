import streamlit as st
import streamlit.components.v1 as components


def render_html(html: str, height: int = 480, scrolling: bool = False):
    """Render trusted app-generated HTML without showing raw tags.

    Some Streamlit versions render complex HTML as escaped markdown/code
    when using st.markdown. Use st.html first; fallback to components.html.
    """
    try:
        if hasattr(st, "html"):
            st.html(html)
            return
    except Exception:
        pass

    components.html(html, height=height, scrolling=scrolling)

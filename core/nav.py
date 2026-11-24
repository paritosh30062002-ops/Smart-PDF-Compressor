"""Page registry, so any page can jump to another with st.switch_page(nav.page("login"))."""
from __future__ import annotations

_PAGES: dict = {}


def register(pages: dict) -> None:
    _PAGES.clear()
    _PAGES.update(pages)


def page(name: str):
    return _PAGES[name]

from typing import Literal, cast

import streamlit as st
from streamlit.delta_generator import DeltaGenerator


class BaseComponent:
    def __init__(self, key: str | None = None):
        self.key = key

    def render(self) -> DeltaGenerator:
        raise NotImplementedError


class Page(BaseComponent):
    def __init__(
        self,
        title: str,
        icon: str | None = None,
        layout: Literal["centered", "wide"] = "wide",
        key: str | None = None,
    ):
        super().__init__(key=key)
        self.title = title
        self.icon = icon
        self.layout = layout

    def configure(self) -> None:
        st.set_page_config(
            page_title=self.title,
            page_icon=self.icon,
            layout=self.layout,  # type: ignore
        )

    def render(self) -> DeltaGenerator:
        self.configure()
        return cast(DeltaGenerator, st.container())

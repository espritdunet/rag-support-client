"""Type stubs for Streamlit"""

from collections.abc import Sequence
from typing import Any, Literal, NoReturn

from rag_support_client.streamlit.types import DeltaGenerator

class State:
    """State class for session state"""

    def __getattr__(self, key: str) -> Any: ...
    def __setattr__(self, key: str, value: Any) -> None: ...
    def __getitem__(self, key: str) -> Any: ...
    def __setitem__(self, key: str, value: Any) -> None: ...
    def __contains__(self, key: str) -> bool: ...

# Widgets
def title(text: str) -> DeltaGenerator: ...
def header(text: str) -> DeltaGenerator: ...
def subheader(text: str) -> DeltaGenerator: ...
def caption(text: str) -> DeltaGenerator: ...
def markdown(text: str) -> DeltaGenerator: ...
def write(*args: Any, **kwargs: Any) -> DeltaGenerator: ...
def button(
    label: str,
    key: str | None = None,
    help: str | None = None,
    type: Literal["primary", "secondary"] = "secondary",
) -> bool: ...
def radio(
    label: str,
    options: Sequence[Any],
    index: int = 0,
    key: str | None = None,
    help: str | None = None,
) -> Any: ...
def spinner(text: str = "") -> DeltaGenerator: ...
def success(text: str) -> DeltaGenerator: ...
def info(text: str) -> DeltaGenerator: ...
def error(text: str) -> DeltaGenerator: ...
def warning(text: str) -> DeltaGenerator: ...
def container() -> DeltaGenerator: ...
def expander(
    label: str,
    expanded: bool = False,
) -> DeltaGenerator: ...
def file_uploader(
    label: str,
    type: str | Sequence[str] | None = None,
    accept_multiple_files: bool = False,
    key: str | None = None,
    help: str | None = None,
) -> Any: ...
def columns(
    spec: int | Sequence[int], gap: str = "small"
) -> Sequence[DeltaGenerator]: ...
def tabs(tabs: Sequence[str]) -> Sequence[DeltaGenerator]: ...
def json(obj: Any) -> DeltaGenerator: ...
def code(code: str, language: str | None = None) -> DeltaGenerator: ...

# Data display widgets
def set_page_config(
    page_title: str | None = None,
    page_icon: str | None = None,
    layout: str = "centered",
    initial_sidebar_state: str = "auto",
    menu_items: dict[str, str] | None = None,
) -> None: ...
def dataframe(
    data: Any,
    use_container_width: bool = False,
    column_config: dict[str, Any] | None = None,
) -> DeltaGenerator: ...
def metric(
    label: str,
    value: Any,
    delta: Any | None = None,
) -> DeltaGenerator: ...
def progress(
    value: float,
    text: str | None = None,
) -> DeltaGenerator: ...
def form(
    key: str,
) -> DeltaGenerator: ...
def form_submit_button(
    label: str = "Submit",
    type: Literal["primary", "secondary"] = "secondary",
) -> bool: ...
def number_input(
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
    value: float | None = None,
    key: str | None = None,
    help: str | None = None,
) -> float: ...
def slider(
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
    value: float | None = None,
    key: str | None = None,
) -> float: ...

# Control flow
def rerun() -> NoReturn: ...

# Special Objects
sidebar: DeltaGenerator
session_state: State

# Types
class UploadedFile:
    """Class representing an uploaded file"""

    name: str
    type: str
    size: int
    def read(self, size: int | None = None) -> bytes: ...

# Column config
class column_config:
    @staticmethod
    def TextColumn(
        label: str,
        help: str | None = None,
        width: Literal["small", "medium", "large"] = "medium",
    ) -> Any: ...
    @staticmethod
    def DatetimeColumn(
        label: str,
        help: str | None = None,
        format: str = "medium",
        width: Literal["small", "medium", "large"] = "medium",
    ) -> Any: ...

def chat_message(
    message: str,
    key: str | None = None,
) -> DeltaGenerator: ...
def chat_input(
    placeholder: str = "",
    key: str | None = None,
    max_chars: int | None = None,
    disabled: bool = False,
) -> str | None: ...

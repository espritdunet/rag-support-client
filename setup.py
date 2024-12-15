from setuptools import setup

setup(
    package_dir={"": "src"},
    packages=[
        "rag_support_client",
        "rag_support_client.api",
        "rag_support_client.config",
        "rag_support_client.rag",
        "rag_support_client.streamlit",
        "rag_support_client.utils",
    ],
)

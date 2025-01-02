from setuptools import setup, find_packages

setup(
    name="paper_assistant",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask",
        "requests",
        "arxiv",
        # Add other dependencies as needed
    ],
    python_requires=">=3.8",
    package_data={
        "paper_assistant": [
            "config/*",
            "templates/*",
        ],
    },
    entry_points={
        "console_scripts": [
            "paper-assistant=paper_assistant.core.main:main",
        ],
    },
)

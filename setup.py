"""Setup for cli-anything-everything."""
from setuptools import setup, find_namespace_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cli-anything-everything",
    version="1.0.0",
    description="Lightning-fast Windows file search CLI for AI agents — powered by voidtools Everything",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="wuykjl",
    url="https://github.com/wuykjl/everything-cli-anything",
    license="MIT",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "everything=cli_anything.everything.everything_cli:main",
            "cli-anything-everything=cli_anything.everything.everything_cli:main",
        ],
    },
    package_data={
        "cli_anything.everything": ["skills/SKILL.md"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Desktop Environment :: File Managers",
        "Topic :: Utilities",
    ],
    keywords="everything, everything-search, voidtools, file-search, windows, cli, ai-agent, agent-native",
)

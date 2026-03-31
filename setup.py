"""Setup configuration for message-to-iaac."""

from setuptools import setup, find_packages

setup(
    name="iacraft",
    version="1.0.0",
    description="IaCraft — Craft Cloud Infrastructure from Natural Language",
    author="Cloud Architect AI",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.40.0",
        "openai>=1.40.0",
        "google-genai>=1.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "python-dotenv>=1.0.0",
        "httpx>=0.27.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "jinja2>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "iacraft=src.cli:main",
            "message-to-iaac=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Programming Language :: Python :: 3",
    ],
)

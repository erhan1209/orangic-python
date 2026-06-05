from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="orangic",
    version="0.1.0",  # Pre-release version
    author="Orangic Technologies",
    author_email="support@orangic.tech",
    description="The official Python library for the Orangic API (Pre-release)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/erhan1209/orangic-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",  # Changed to Pre-Alpha
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Minimal dependencies for placeholder
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/erhan1209/orangic-python/issues",
        "Source": "https://github.com/erhan1209/orangic-python",
        "Website": "https://orangic.tech",
    },
)

"""
Setup configuration for alkoteka_parser
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="alkoteka-parser",
    version="0.1.0",
    author="Leo-ich",
    author_email="email@example.com",
    description="Scrapy parser for Alkoteka products",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Leo-ich/alkoteka_parser",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Framework :: Scrapy",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    package_data={
        "alkoteka_parser": [
            "*.txt",
            "*.md",
        ],
    },
)

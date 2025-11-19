from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="clihelper",
    version="0.1.0",
    author="Rob KN",
    author_email="robgknicholson@gmail.com",
    description="Instant AI-powered help for command-line errors",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RobGKN/clihelper",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Topic :: System :: Shells",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
    install_requires=[
        "anthropic>=0.18.0",
    ],
    entry_points={
        "console_scripts": [
            "clihelper=clihelper.cli:main",
        ],
    },
)
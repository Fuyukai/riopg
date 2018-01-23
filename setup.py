import sys
from pathlib import Path

from setuptools import setup

if sys.version_info[0:2] < (3, 6):
    raise RuntimeError("This package requires Python 3.6+.")

setup(
    name="riopg",
    use_scm_version={
        "version_scheme": "guess-next-dev",
        "local_scheme": "dirty-tag"
    },
    packages=[
        "riopg",
    ],
    url="https://github.com/SunDwarf",
    license="LGPLv3",
    author="Laura Dickinson",
    author_email="l@veriny.tf",
    description="A postgresql library for (cu|t)rio",
    long_description=Path(__file__).with_name("README.rst").read_text(encoding="utf-8"),
    setup_requires=[
        "setuptools_scm",
    ],
    install_requires=[
        "multio~=0.2.0",
        "psycopg2~=2.7",
    ],
    extras_require={
    },
    test_requires=[],
    python_requires=">=3.5.2",
)

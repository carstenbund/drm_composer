"""Build entry point for drm-composer.

Pure-Python package — there is no custom build step here (unlike drm-display,
whose setup.py compiles a C helper).  All metadata lives in pyproject.toml; this
shim exists so the repo mirrors the drm-display scaffold and keeps working with
toolchains that still invoke setup.py.
"""
from setuptools import setup

setup()

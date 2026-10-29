"""
Version information for zomi-g2p.

This module resolves the installed package version using importlib.metadata.
During development (editable installs or source checkouts), the version falls
back to "0.0.0" to avoid import errors before packaging.

Compatibility re-export. The authoritative version lives in pyproject.toml.
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("zomi-g2p")
except PackageNotFoundError:
    # Fallback for development environments
    # Editable install / running from source without metadata
    __version__ = "0.0.0"

__all__ = ["__version__"]
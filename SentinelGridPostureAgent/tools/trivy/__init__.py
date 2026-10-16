"""Trivy vulnerability scanner wrapper."""

from .trivy_wrapper import scan_image, scan_filesystem

__all__ = ["scan_image", "scan_filesystem"]


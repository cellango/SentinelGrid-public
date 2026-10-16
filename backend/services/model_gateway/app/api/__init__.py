"""API routers for Model Gateway."""

import os

from . import unified_chat, adapters

__all__ = ["unified_chat", "adapters"]

if os.getenv("DISABLE_RAG_ROUTES", "false").lower() not in ("1", "true", "yes"):
    from . import rag, knowledge_base_loader
    __all__.extend(["rag", "knowledge_base_loader"])

if os.getenv("DISABLE_TRAINING_ROUTES", "false").lower() not in ("1", "true", "yes"):
    from . import training, git_ingestion

    __all__.extend(["training", "git_ingestion"])

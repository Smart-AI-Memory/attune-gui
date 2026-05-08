"""Process-wide service singletons consumed by route handlers.

Phase D4 of the architecture-realignment spec moved
``attune_gui.routes.rag._get_pipeline`` here as the public
:func:`pipeline_for` so multiple route modules can share the cache
without crossing route boundaries.
"""

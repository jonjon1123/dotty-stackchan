"""FastAPI routers for dotty-behaviour, split by concern.

The daemon's app.main mounts each module's `router` at the right
prefix. Routers take the singleton dependencies (PerceptionState etc.)
via FastAPI's `Depends` so tests can override them.
"""

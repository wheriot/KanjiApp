"""Phone reviews over HTTP: a FastAPI app on top of ``services`` (optional ``web`` extra).

Sits beside ``ui`` in the layering: ``web -> services -> core / data``. No Qt here, and
nothing in ``web`` imports ``data`` directly.
"""

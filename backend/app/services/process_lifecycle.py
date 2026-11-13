"""Stop at a paid-call boundary so deployments can persist in-flight results."""

from threading import Event

_draining = Event()


def reset():
    _draining.clear()


def begin_shutdown():
    _draining.set()


def draining():
    return _draining.is_set()

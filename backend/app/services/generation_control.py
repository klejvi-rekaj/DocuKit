from __future__ import annotations

from threading import Event, Lock


_generation_lock = Lock()
_active_generations: dict[str, Event] = {}


def build_generation_key(*, user_id: str, notebook_id: str) -> str:
    return f"{user_id}:{notebook_id}"


def begin_generation(key: str) -> Event:
    event = Event()
    with _generation_lock:
        previous = _active_generations.get(key)
        if previous is not None:
            previous.set()
        _active_generations[key] = event
    return event


def request_stop(key: str) -> bool:
    with _generation_lock:
        event = _active_generations.get(key)
        if event is None:
            return False
        event.set()
        return True


def is_generation_active(key: str) -> bool:
    with _generation_lock:
        event = _active_generations.get(key)
        return event is not None and not event.is_set()


def finish_generation(key: str, event: Event | None = None) -> None:
    with _generation_lock:
        current = _active_generations.get(key)
        if current is None:
            return
        if event is not None and current is not event:
            return
        _active_generations.pop(key, None)

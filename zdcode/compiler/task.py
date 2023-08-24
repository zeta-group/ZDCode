"""Pending tasks in the compiler."""
import functools


@functools.total_ordering
class PendingTask:
    """A compiler task to be queued."""

    def __init__(self, priority, func):
        self.priority = priority
        self.func = func

    def __lt__(self, other):
        return self.priority < other.priority

    def __eq__(self, other):
        return self.priority == other.priority


def pending_task(priority):
    """Decorates a function to be a task to be qeuued, a [PendingTask]."""

    def _decorator(func):
        return PendingTask(priority, func)

    return _decorator

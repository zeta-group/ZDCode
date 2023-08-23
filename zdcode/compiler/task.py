@functools.total_ordering
class PendingTask:
    def __init__(self, priority, func):
        self.priority = priority
        self.func = func

    def __lt__(self, other):
        return self.priority < other.priority

    def __eq__(self, other):
        return self.priority == other.priority


def pending_task(priority):
    def _decorator(func):
        return PendingTask(priority, func)

    return _decorator

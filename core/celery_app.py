import os


class _FallbackTask:
    def __init__(self, func):
        self.func = func
        self.__name__ = getattr(func, "__name__", "task")

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class _FallbackCelery:
    def task(self, func=None, **_kwargs):
        def decorator(f):
            return _FallbackTask(f)

        if func is None:
            return decorator
        return decorator(func)


try:  # pragma: no cover
    from celery import Celery
except Exception:  # pragma: no cover
    celery_app = _FallbackCelery()
else:  # pragma: no cover
    celery_app = Celery(
        "upos",
        broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    )
    celery_app.conf.task_always_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1"

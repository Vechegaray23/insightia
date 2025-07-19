class wait_random_exponential:
    def __init__(self, multiplier=1, max=60, **kwargs):
        self.multiplier = multiplier
        self.max = max


def stop_after_attempt(n):
    return n


def retry(*dargs, **dkwargs):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    return decorator


class AsyncRetrying:
    pass

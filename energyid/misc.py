from collections.abc import Iterator, Callable
import itertools


def skip_tops(
    amount: int | None = None, skip: int = 0, top: int = 200
) -> Iterator[tuple[int, int]]:
    """
    Generate skip-top pairs, based on the total amount of elements you want
    """
    count = 0
    while amount is None or count < amount:
        if amount is not None:
            top = min(top, amount - count)
        yield skip, top
        skip = skip + top
        count = count + top


def handle_skip_take_limit(
    func: Callable, *args, amount: int | None = None, chunk_size=200, **kwargs
):
    for skip, take in skip_tops(amount=amount, top=chunk_size):
        elements = func(*args, skip=skip, take=take, **kwargs)
        if len(elements) != 0:
            yield from elements
        else:
            break


def groupby(collection: list[dict], key: str) -> tuple[str, list[dict]]:
    """Groups a list of dicts by a key"""
    collection = collection.copy()
    collection.sort(key=lambda x: x[key])
    for k, v in itertools.groupby(collection, key=lambda x: x[key]):
        yield k, list(v)

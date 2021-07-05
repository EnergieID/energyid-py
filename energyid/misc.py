from typing import Optional, Iterator, Tuple, Callable, List, Any, Dict
import itertools



def skip_tops(amount: Optional[int]=None, skip: int=0, top: int=200) -> Iterator[Tuple[int, int]]:
    """
    Generate skip-top pairs, based on the total amount of elements you want
    """
    count = 0
    while amount is None or count < amount:
        if amount is not None:
            top = min(top, amount-count)
        yield skip, top
        skip = skip + top
        count = count + top


def handle_skip_top_limit(func: Callable, *args, amount: Optional[int]=None, chunk_size=200, **kwargs):
    for skip, top in skip_tops(amount=amount, top=chunk_size):
        elements = func(*args, skip=skip, top=top, **kwargs)
        if len(elements) != 0:
            for element in elements:
                yield element
        else:
            break


def groupby(collection: List[Dict], key: str) -> Tuple[str, List[Dict]]:
    """Groups a list of dicts by a key"""
    collection = collection.copy()
    collection.sort(key=lambda x: x[key])
    for k, v in itertools.groupby(collection, key=lambda x: x[key]):
        yield k, list(v)

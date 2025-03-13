import asyncio
from typing import Callable

from energyid.misc import skip_tops


async def handle_skip_take_limit(
        func: Callable, *args, amount: int, chunk_size=200, **kwargs
):
    if amount is None:
        raise ValueError("Amount must be an integer")
    tasks = []
    for skip, take in skip_tops(amount=amount, top=chunk_size):
        tasks.append(func(*args, skip=skip, take=take, **kwargs))
    # Yield elements as they come in
    for task in asyncio.as_completed(tasks):
        elements = await task
        if len(elements) != 0:
            for element in elements:
                yield element
        else:
            break
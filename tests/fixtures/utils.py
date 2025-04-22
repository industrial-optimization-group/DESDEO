import time

import pytest


@pytest.fixture
def timer(request):
    start_time = time.time()
    yield
    end_time = time.time()
    print(f"\n{request.node.name} took {end_time - start_time} seconds")

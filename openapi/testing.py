"""Testing utilities
"""
from openapi.json import loads, dumps


async def jsonBody(response, status=200):
    assert response.status == status
    assert response.content_type == 'application/json'
    return await response.json(loads=loads)


def equal_dict(d1, d2):
    """Check if two dictionaries are the same"""
    d1, d2 = map(dumps, (d1, d2))
    return d1 == d2

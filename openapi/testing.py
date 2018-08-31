"""Testing utilities
"""
import json

from openapi.json import loads, dumps


async def jsonBody(response, status=200):
    assert response.content_type == 'application/json'
    data = await response.json(loads=loads)
    if response.status != status:   # pragma    no cover
        print(json.dumps({
            'status': response.status,
            'data': data
        }, indent=4))
    assert response.status == status
    return data


def equal_dict(d1, d2):
    """Check if two dictionaries are the same"""
    d1, d2 = map(dumps, (d1, d2))
    return d1 == d2

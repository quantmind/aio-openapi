import dataclasses

from ..example.models import TaskOrderableQuery


def test_search_docstring():
    fields = {f.name: f for f in dataclasses.fields(TaskOrderableQuery)}
    assert fields["search"].metadata["description"] == (
        "Search query string. "
        "The search is performed on ``title``, ``unique_title`` fields."
    )

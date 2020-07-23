import yarl
from typing import NamedTuple, Dict
from aiohttp.web import Application


class FakeRequest(NamedTuple):
    app: Application
    headers: Dict
    url: yarl.URL

    @classmethod
    def from_app(cls, app: Application) -> "FakeRequest":
        return cls(app, {}, yarl.URL("https://fake.com"))

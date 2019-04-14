import os

from aiohttp import web
from multidict import MultiDict

from openapi.json import dumps

MAX_PAGINATION_LIMIT = int(os.environ.get("MAX_PAGINATION_LIMIT") or 100)
DEF_PAGINATION_LIMIT = int(os.environ.get("DEF_PAGINATION_LIMIT") or 50)


class PaginatedData:
    def __init__(self, data, pagination, total, offset, limit):
        self.data = data
        self.pagination = pagination
        self.total = total
        self.offset = offset
        self.limit = limit

    def json_response(self, headers=None, **kwargs):
        headers = headers or {}
        links = self.header_links()
        if links:
            headers["Link"] = links
        headers["X-Total-Count"] = f"{self.total}"
        return web.json_response(self.data, headers=headers, **kwargs, dumps=dumps)

    def header_links(self):
        links = self.pagination.links(self.total, self.limit, self.offset)
        return ", ".join(f'<{value}>; rel="{name}"' for name, value in links.items())


class Pagination:
    def __init__(self, url):
        self.url = url
        self.query = MultiDict(url.query)

    def paginated(self, data, total, offset, limit):
        return PaginatedData(data, self, total, offset, limit)

    def first_link(self, total, limit, offset):
        n = self._count_part(offset, limit, 0)
        if n:
            offset -= n * limit
        if offset > 0:
            return self.link(0, min(limit, offset))

    def prev_link(self, total, limit, offset):
        if offset:
            olimit = min(limit, offset)
            prev_offset = offset - olimit
            return self.link(prev_offset, olimit)

    def next_link(self, total, limit, offset):
        next_offset = offset + limit
        if total > next_offset:
            return self.link(next_offset, limit)

    def last_link(self, total, limit, offset):
        n = self._count_part(total, limit, offset)
        if n > 0:
            return self.link(offset + n * limit, limit)

    def link(self, offset, limit):
        query = self.query.copy()
        query.update({"offset": offset, "limit": limit})
        return self.url.with_query(query)

    def _count_part(self, total, limit, offset):
        n = (total - offset) // limit
        # make sure we account for perfect matching
        if n * limit + offset == total:
            n -= 1
        return max(0, n)

    def links(self, total, limit, offset):
        links = {}
        first = self.first_link(total, limit, offset)
        if first:
            links["first"] = first
            prev = self.prev_link(total, limit, offset)
            if prev != first:
                links["prev"] = prev
        next_ = self.next_link(total, limit, offset)
        if next_:
            last = self.last_link(total, limit, offset)
            if last != next_:
                links["next"] = next_
            links["last"] = last
        return links

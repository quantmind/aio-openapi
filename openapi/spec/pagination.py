import os

from multidict import MultiDict


MAX_PAGINATION_LIMIT = int(os.environ.get('MAX_PAGINATION_LIMIT') or 100)
DEF_PAGINATION_LIMIT = int(os.environ.get('DEF_PAGINATION_LIMIT') or 50)


class Pagination:
    def __init__(self, url):
        self.url = url
        self.query = MultiDict(url.query)

    def first_link(self, total, limit, offset):
        n = self._count_part(offset, limit, 0)
        if n:
            offset -= n*limit
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
            return self.link(offset + n*limit, limit)

    def link(self, offset, limit):
        query = self.query.copy()
        query.update({'offset': offset, 'limit': limit})
        return self.url.with_query(query)

    def _count_part(self, total, limit, offset):
        n = (total - offset) // limit
        # make sure we account for perfect matching
        if n*limit + offset == total:
            n -= 1
        return max(0, n)

    def links(self, total, limit, offset):
        links = {}
        first = self.first_link(total, limit, offset)
        if first:
            links['first'] = first
            prev = self.prev_link(total, limit, offset)
            if prev != first:
                links['prev'] = prev
        next = self.next_link(total, limit, offset)
        if next:
            last = self.last_link(total, limit, offset)
            if last != next:
                links['next'] = next
            links['last'] = last
        return links

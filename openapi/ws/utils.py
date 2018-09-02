def redis_to_py_pattern(pattern):
    return ''.join(_redis_to_py_pattern(pattern))


def _redis_to_py_pattern(pattern):
    clear, esc = False, False
    s, q, op, cp, e = '*', '?', '[', ']', '\\'

    for v in pattern:
        if v == s and not esc:
            yield '(.*)'
        elif v == q and not esc:
            yield '.'
        elif v == op and not esc:
            esc = True
            yield v
        elif v == cp and esc:
            esc = False
            yield v
        elif v == e:
            clear, esc = True
            yield v
        elif clear:
            clear, esc = False, False
            yield v
        else:
            yield v
    yield '$'

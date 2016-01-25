import re
import operator


def instructions():
    instructions = """<h1>Here is how to use my calculator.</h1>"""
    return instructions


def calculate(num1, op_str, num2):
    ops = {'+': operator.add,
           '-': operator.sub,
           '*': operator.mul,
           '/': operator.truediv}
    result = ops[op_str](int(num1), int(num2))
    calculation = "<h1>{} {} {} equals {}.</h1>"
    return calculation.format(num1, op_str, num2, result)


def resolve_path(path):
    urls = [(r'^$', instructions),
            (r'^([\d]+)(\+|\-|\*|\/)([\d]+)$', calculate)]
    matchpath = path.lstrip('/')
    for regexp, func in urls:
        match = re.match(regexp, matchpath)
        if match is None:
            continue
        args = match.groups([])
        return func, args
    # we get here if no url matches
    raise NameError


def application(environ, start_response):
    headers = [("Content-type", "text/html")]
    try:
        path = environ.get('PATH_INFO', None)
        if path is None:
            raise NameError
        func, args = resolve_path(path)
        body = func(*args)
        status = "200 OK"
    except NameError:
        status = "404 Not Found"
        body = "<h1>Not Found</h1>"
    except ZeroDivisionError:
        status = "400 Bad Request"
        body = "<h1>You can't divide by zero!</h1>"
    except Exception:
        status = "500 Internal Server Error"
        body = "<h1>Internal Server Error</h1>"
    finally:
        headers.append(('Content-length', str(len(body))))
        start_response(status, headers)
        return [body.encode('utf8')]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 8080, application)
    srv.serve_forever()

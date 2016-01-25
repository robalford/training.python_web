import re
import operator
from urllib.parse import parse_qsl


def header():
    header = """<html>
<head>
<title>Calculator</title>
</head>
<body>
<header><h1>Python Does Math For You</h1></header></br>"""
    return header


def footer():
    footer = """
</br></br>
<footer>&copy; pythondoesmathforyou.com</footer>
</body>
</html>"""
    return footer


def html_doc(body):
    head = header()
    foot = footer()
    return head + body + foot


def calculator():
    calculator = """
<form>
  Enter a calculation (e.g. '5+2'):</br></br>
  <input type="text" name="calculation"></br></br>
  <input type="submit" value="Calculate">
</form>"""
    return calculator


def calculate(num1, op_str, num2):
    ops = {'+': operator.add,
           '-': operator.sub,
           '*': operator.mul,
           '/': operator.truediv}
    result = ops[op_str](int(num1), int(num2))
    calculation = """<p>{} {} {} equals {}</p></br></br>
    <a href='/'>Make another calculation.</a>"""
    return calculation.format(num1, op_str, num2, result)


def resolve_path(path):
    urls = [(r'^$', calculator),
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
        qs = environ.get('QUERY_STRING', None)
        if path is None:
            raise NameError
        if qs:
            qsl = parse_qsl(qs)  # urllib function to convert query string to list
            path = qsl[0][1].replace(' ', '')  # grab the calculation value, strip whitespace and store it in path
        func, args = resolve_path(path)
        body = func(*args)
        status = "200 OK"
    except NameError:
        status = "404 Not Found"
        body = """<h1>Not Found</h1>
        <a href='/'>Make another calculation.</a>"""  # DRY
    except ZeroDivisionError:
        status = "400 Bad Request"
        body = """<h1>You can't divide by zero!</h1>
        <a href='/'>Make another calculation.</a>"""
    except Exception:
        status = "500 Internal Server Error"
        body = """<h1>Internal Server Error</h1>
        <a href='/'>Make another calculation.</a>"""
    finally:
        html = html_doc(body)
        headers.append(('Content-length', str(len(html))))
        start_response(status, headers)
        return [html.encode('utf8')]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 8080, application)
    srv.serve_forever()

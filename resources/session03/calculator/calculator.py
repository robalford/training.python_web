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


def html_doc(doc_body):
    doc_header = header()
    doc_footer = footer()
    return doc_header + doc_body + doc_footer


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
        request = environ.get('PATH_INFO', None)
        qs = environ.get('QUERY_STRING', None)
        if request is None:
            raise NameError
        if qs:
            qsl = parse_qsl(qs)  # urllib function to convert query string to list of keys and values
            request = qsl[0][1].replace(' ', '')  # grab the calculation from the query string, strip whitespace and store it in request
        func, args = resolve_path(request)
        body = func(*args)
        status = "200 OK"
    except NameError:
        status = "400 Bad Request"
        body = """<h1>Please re-enter your calculation using only digits and the following operands: +, -, *, /. Thanks!</h1>
        <a href='/'>Try another calculation.</a>"""
    except ZeroDivisionError:
        status = "400 Bad Request"
        body = """<h1>You can't divide by zero!</h1>
        <a href='/'>Let's try something more reasonable.</a>"""
    except Exception:
        status = "500 Internal Server Error"
        body = """<h1>Something bad has happened, but it's not your fault. Sorry.</h1>
        <a href='/'>Give us another chance.</a>"""
    finally:
        html = html_doc(body)
        headers.append(('Content-length', str(len(html))))
        start_response(status, headers)
        return [html.encode('utf8')]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 8080, application)
    srv.serve_forever()

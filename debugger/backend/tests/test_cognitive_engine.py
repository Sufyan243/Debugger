from app.cognitive.engine import parse_exception, classify


def test_classify_name_error():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 1, in <module>
    print(x)
NameError: name 'x' is not defined'''
    result = classify(traceback)
    assert result is not None
    assert result.concept_category == "Variable Initialization"
    assert result.cognitive_skill == "State awareness"


def test_classify_type_error():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 1, in <module>
    "hello" + 5
TypeError: can only concatenate str (not "int") to str'''
    result = classify(traceback)
    assert result is not None
    assert result.concept_category == "Data Type Compatibility"
    assert result.cognitive_skill == "Type reasoning"


def test_classify_index_error():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 2, in <module>
    print(lst[5])
IndexError: list index out of range'''
    result = classify(traceback)
    assert result is not None
    assert result.concept_category == "List Management"
    assert result.cognitive_skill == "Boundary reasoning"


def test_classify_key_error():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 2, in <module>
    print(d['missing'])
KeyError: 'missing' '''
    result = classify(traceback)
    assert result is not None
    assert result.concept_category == "Dictionary Usage"
    assert result.cognitive_skill == "Mapping reasoning"


def test_classify_zero_division_error():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 1, in <module>
    1/0
ZeroDivisionError: division by zero'''
    result = classify(traceback)
    assert result is None


def test_classify_syntax_error():
    traceback = '''  File "/code/submission.py", line 1
    if True
           ^
SyntaxError: invalid syntax'''
    result = classify(traceback)
    assert result is None


def test_parse_exception_empty():
    result = parse_exception("")
    assert result is None


def test_parse_exception_with_line_number():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 42, in <module>
    print(x)
NameError: name 'x' is not defined'''
    result = parse_exception(traceback)
    assert result is not None
    assert result.line_number == 42
    assert result.exception_type == "NameError"


def test_parse_exception_bare():
    traceback = '''Traceback (most recent call last):
  File "/code/submission.py", line 1, in <module>
    raise ValueError
ValueError'''
    result = parse_exception(traceback)
    assert result is not None
    assert result.exception_type == "ValueError"
    assert result.message == ""

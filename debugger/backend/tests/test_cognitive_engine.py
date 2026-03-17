from app.cognitive.engine import (
    parse_exception,
    classify,
    get_reflection_question,
    generate_contextual_hint,
    generate_solution,
)


# ---------------------------------------------------------------------------
# parse_exception
# ---------------------------------------------------------------------------

def test_parse_exception_empty():
    assert parse_exception("") is None


def test_parse_exception_with_line_number():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 42, in <module>\n'
        "    print(x)\n"
        "NameError: name 'x' is not defined"
    )
    result = parse_exception(tb)
    assert result is not None
    assert result.exception_type == "NameError"
    assert result.line_number == 42


def test_parse_exception_bare():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    raise ValueError\n"
        "ValueError"
    )
    result = parse_exception(tb)
    assert result is not None
    assert result.exception_type == "ValueError"
    assert result.message == ""


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

def test_classify_name_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    print(x)\n"
        "NameError: name 'x' is not defined"
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "Variable Initialization"
    assert result.cognitive_skill == "State awareness"


def test_classify_name_error_typo():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    pint('hello')\n"
        "NameError: name 'pint' is not defined"
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "Typo / Spelling"
    assert result.cognitive_skill == "Attention to detail"


def test_classify_type_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        '    "hello" + 5\n'
        'TypeError: can only concatenate str (not "int") to str'
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "Data Type Compatibility"
    assert result.cognitive_skill == "Type reasoning"


def test_classify_attribute_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 2, in <module>\n'
        "    x.upper()\n"
        "AttributeError: 'int' object has no attribute 'upper'"
    )
    result = classify(tb)
    assert result is not None
    assert result.exception_type == "AttributeError"
    assert result.concept_category == "Object Attributes"
    assert result.cognitive_skill == "Object model reasoning"


def test_classify_value_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    int('abc')\n"
        "ValueError: invalid literal for int() with base 10: 'abc'"
    )
    result = classify(tb)
    assert result is not None
    assert result.exception_type == "ValueError"
    assert result.concept_category == "Value Validity"
    assert result.cognitive_skill == "Input validation reasoning"


def test_classify_index_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 2, in <module>\n'
        "    print(lst[5])\n"
        "IndexError: list index out of range"
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "List Management"
    assert result.cognitive_skill == "Boundary reasoning"


def test_classify_key_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 2, in <module>\n'
        "    print(d['missing'])\n"
        "KeyError: 'missing'"
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "Dictionary Usage"
    assert result.cognitive_skill == "Mapping reasoning"


def test_classify_zero_division_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    1/0\n"
        "ZeroDivisionError: division by zero"
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "Mathematical Operations"
    assert result.cognitive_skill == "Logic reasoning"


def test_classify_syntax_error():
    tb = (
        '  File "/code/submission.py", line 1\n'
        "    if True\n"
        "           ^\n"
        "SyntaxError: invalid syntax"
    )
    result = classify(tb)
    assert result is not None
    assert result.concept_category == "Syntax"
    assert result.cognitive_skill == "Code structure"


def test_classify_unknown_returns_none():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    raise RuntimeError('boom')\n"
        "RuntimeError: boom"
    )
    assert classify(tb) is None


# ---------------------------------------------------------------------------
# get_reflection_question
# ---------------------------------------------------------------------------

def test_reflection_question_attribute_error():
    q = get_reflection_question("Object Attributes")
    assert "attribute" in q.lower() or "method" in q.lower() or "type" in q.lower()


def test_reflection_question_value_error():
    q = get_reflection_question("Value Validity")
    assert "value" in q.lower()


def test_reflection_question_variable_initialization():
    q = get_reflection_question("Variable Initialization")
    assert q != "What do you think caused this error?"


def test_reflection_question_unknown_falls_back():
    q = get_reflection_question("Something Unknown")
    assert q == "What do you think caused this error?"


# ---------------------------------------------------------------------------
# generate_contextual_hint
# ---------------------------------------------------------------------------

def test_contextual_hint_attribute_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 2, in <module>\n'
        "    x.upper()\n"
        "AttributeError: 'int' object has no attribute 'upper'"
    )
    hint = generate_contextual_hint(tb, "x = 5\nx.upper()")
    assert hint is not None
    assert "attribute" in hint.hint_text.lower() or "method" in hint.hint_text.lower()
    assert hint.affected_line == 2


def test_contextual_hint_value_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    int('abc')\n"
        "ValueError: invalid literal for int() with base 10: 'abc'"
    )
    hint = generate_contextual_hint(tb, "int('abc')")
    assert hint is not None
    assert "value" in hint.hint_text.lower()
    assert hint.affected_line == 1


def test_contextual_hint_name_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    print(x)\n"
        "NameError: name 'x' is not defined"
    )
    hint = generate_contextual_hint(tb, "print(x)")
    assert hint is not None
    assert "x" in hint.hint_text


# ---------------------------------------------------------------------------
# generate_solution
# ---------------------------------------------------------------------------

def test_solution_attribute_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 2, in <module>\n'
        "    x.upper()\n"
        "AttributeError: 'int' object has no attribute 'upper'"
    )
    sol = generate_solution(tb, "x = 5\nx.upper()")
    assert sol is not None
    assert len(sol.changes_needed) > 0
    assert sol.explanation != ""


def test_solution_value_error():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    int('abc')\n"
        "ValueError: invalid literal for int() with base 10: 'abc'"
    )
    sol = generate_solution(tb, "int('abc')")
    assert sol is not None
    assert len(sol.changes_needed) > 0
    assert sol.explanation != ""


def test_solution_name_error_typo_fixes_code():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    pint('hello')\n"
        "NameError: name 'pint' is not defined"
    )
    sol = generate_solution(tb, "pint('hello')")
    assert sol is not None
    assert "print" in sol.solution_code


def test_solution_unknown_error_returns_generic():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "/code/submission.py", line 1, in <module>\n'
        "    raise RuntimeError('boom')\n"
        "RuntimeError: boom"
    )
    sol = generate_solution(tb, "raise RuntimeError('boom')")
    assert sol is not None
    assert len(sol.changes_needed) > 0

from dataclasses import dataclass
import re
from difflib import get_close_matches
from typing import Optional

PYTHON_BUILTINS = [
    "print", "len", "range", "int", "str", "float", "list", "dict", "set", "tuple",
    "input", "type", "isinstance", "enumerate", "zip", "map", "filter", "sorted",
    "min", "max", "sum", "abs", "round", "open", "bool", "bytes", "repr", "format",
    "hasattr", "getattr", "setattr", "append", "extend", "insert", "remove", "pop",
]


@dataclass
class ParsedError:
    exception_type: str
    message: str
    line_number: Optional[int]


@dataclass
class ClassificationResult:
    exception_type: str
    concept_category: str
    cognitive_skill: str


@dataclass
class ContextualHint:
    hint_text: str
    affected_line: Optional[int]
    explanation: str


@dataclass
class SolutionData:
    solution_code: str
    explanation: str
    changes_needed: list[str]


TYPO_CLASSIFICATION = ClassificationResult("NameError", "Typo / Spelling", "Attention to detail")

TAXONOMY = {
    "NameError": ClassificationResult("NameError", "Variable Initialization", "State awareness"),
    "TypeError": ClassificationResult("TypeError", "Data Type Compatibility", "Type reasoning"),
    "IndexError": ClassificationResult("IndexError", "List Management", "Boundary reasoning"),
    "KeyError": ClassificationResult("KeyError", "Dictionary Usage", "Mapping reasoning"),
    "SyntaxError": ClassificationResult("SyntaxError", "Syntax", "Code structure"),
    "ZeroDivisionError": ClassificationResult("ZeroDivisionError", "Mathematical Operations", "Logic reasoning"),
}

REFLECTION_QUESTIONS = {
    "Typo / Spelling": "Look closely at the function or variable name — does it match the correct Python spelling?",
    "Variable Initialization": "Where in your code should the variable have been created before it was used?",
    "Data Type Compatibility": "What types of values are you trying to combine, and do they work together in Python?",
    "List Management": "What is the length of your list, and which index are you trying to access?",
    "Dictionary Usage": "What keys does your dictionary actually contain, and which one were you trying to access?",
    "Syntax": "Check the syntax on the highlighted line. Is something missing or misplaced?",
    "Mathematical Operations": "What value are you dividing by? Can it ever be zero?",
}

CONTEXTUAL_HINTS = {
    "NameError": lambda var_name, line: ContextualHint(
        hint_text=f"The variable '{var_name}' is being used before it's defined.",
        affected_line=line,
        explanation=f"Python doesn't know what '{var_name}' is. You need to create it (assign a value) before using it."
    ),
    "TypeError": lambda msg, line: ContextualHint(
        hint_text="You're trying to combine incompatible data types.",
        affected_line=line,
        explanation=f"Check the types of values you're working with. {msg}"
    ),
    "IndexError": lambda msg, line: ContextualHint(
        hint_text="You're trying to access an index that doesn't exist.",
        affected_line=line,
        explanation="Lists are zero-indexed. If your list has 3 items, valid indices are 0, 1, 2."
    ),
    "SyntaxError": lambda msg, line: ContextualHint(
        hint_text="There's a syntax error in your code.",
        affected_line=line,
        explanation=f"Check for missing parentheses, quotes, or colons. {msg}"
    ),
    "ZeroDivisionError": lambda msg, line: ContextualHint(
        hint_text="You're dividing by zero.",
        affected_line=line,
        explanation="Division by zero is undefined. Check if your divisor could be zero."
    ),
}

SOLUTION_TEMPLATES = {
    "NameError": lambda var_name, user_code: SolutionData(
        solution_code=f"# Define the variable before using it\n{var_name} = 0  # or appropriate value\nprint({var_name})",
        explanation=f"You need to initialize '{var_name}' before using it.",
        changes_needed=[f"Add '{var_name} = <value>' before line where it's used"]
    ),
    "TypeError": lambda msg, user_code: SolutionData(
        solution_code="# Convert types to match\nresult = str(5) + ' items'  # or int('5') + 10",
        explanation="Make sure you're combining compatible types.",
        changes_needed=["Convert one value to match the other's type using str(), int(), or float()"]
    ),
    "IndexError": lambda msg, user_code: SolutionData(
        solution_code="# Check list length before accessing\nif index < len(my_list):\n    print(my_list[index])",
        explanation="Always verify the index is within the list's range.",
        changes_needed=["Add bounds checking", "Use len() to verify index is valid"]
    ),
}


def parse_exception(traceback: str) -> Optional[ParsedError]:
    if not traceback.strip():
        return None
    
    line_number = None
    matches = list(re.finditer(r'File ".+", line (\d+)', traceback))
    if matches:
        line_number = int(matches[-1].group(1))
    
    lines = [line for line in traceback.split("\n") if line.strip()]
    if not lines:
        return None
    
    last_line = lines[-1]
    
    match = re.match(r"^(\w+(?:\.\w+)*): (.+)$", last_line)
    if match:
        return ParsedError(
            exception_type=match.group(1),
            message=match.group(2),
            line_number=line_number
        )
    
    match = re.match(r"^(\w+(?:\.\w+)*)$", last_line)
    if match:
        return ParsedError(
            exception_type=match.group(1),
            message="",
            line_number=line_number
        )
    
    return None


def classify(traceback: str) -> Optional[ClassificationResult]:
    parsed = parse_exception(traceback)
    if parsed is None:
        return None
    if parsed.exception_type == "NameError":
        match = re.search(r"name '(\w+)' is not defined", parsed.message)
        var_name = match.group(1) if match else ""
        if var_name and _detect_typo(var_name):
            return TYPO_CLASSIFICATION
    return TAXONOMY.get(parsed.exception_type)


def get_reflection_question(concept_category: str) -> str:
    return REFLECTION_QUESTIONS.get(concept_category, "What do you think caused this error?")


def _detect_typo(var_name: str) -> Optional[str]:
    """Return the likely intended builtin if var_name looks like a typo."""
    matches = get_close_matches(var_name, PYTHON_BUILTINS, n=1, cutoff=0.6)
    return matches[0] if matches else None


def generate_contextual_hint(traceback: str, user_code: str) -> Optional[ContextualHint]:
    """Generate a single, actionable hint based on the error and user's code."""
    parsed = parse_exception(traceback)
    if parsed is None:
        return None
    
    hint_generator = CONTEXTUAL_HINTS.get(parsed.exception_type)
    if hint_generator is None:
        return ContextualHint(
            hint_text="An error occurred in your code.",
            affected_line=parsed.line_number,
            explanation="Review the error message and check the highlighted line."
        )
    
    if parsed.exception_type == "NameError":
        match = re.search(r"name '(\w+)' is not defined", parsed.message)
        var_name = match.group(1) if match else "variable"
        suggestion = _detect_typo(var_name)
        if suggestion:
            return ContextualHint(
                hint_text=f"'{var_name}' is not defined — did you mean '{suggestion}'?",
                affected_line=parsed.line_number,
                explanation=f"It looks like a typo. '{var_name}' is not a Python builtin, but '{suggestion}' is."
            )
        return hint_generator(var_name, parsed.line_number)
    
    return hint_generator(parsed.message, parsed.line_number)


def generate_solution(traceback: str, user_code: str) -> Optional[SolutionData]:
    """Generate solution code with specific changes needed."""
    parsed = parse_exception(traceback)
    if parsed is None:
        return None
    
    if parsed.exception_type == "NameError":
        match = re.search(r"name '(\w+)' is not defined", parsed.message)
        var_name = match.group(1) if match else "variable"
        suggestion = _detect_typo(var_name)
        if suggestion:
            fixed_code = re.sub(r'\b' + re.escape(var_name) + r'\b', suggestion, user_code)
            return SolutionData(
                solution_code=fixed_code,
                explanation=f"Replace '{var_name}' with '{suggestion}'.",
                changes_needed=[f"Rename '{var_name}' → '{suggestion}' on line {parsed.line_number}"]
            )
        solution_generator = SOLUTION_TEMPLATES.get("NameError")
        return solution_generator(var_name, user_code)
    
    solution_generator = SOLUTION_TEMPLATES.get(parsed.exception_type)
    if solution_generator is None:
        return SolutionData(
            solution_code="# Review your code and fix the error\n" + user_code,
            explanation="Check the error message for clues.",
            changes_needed=["Review the traceback", "Fix the highlighted line"]
        )
    
    return solution_generator(parsed.message, user_code)

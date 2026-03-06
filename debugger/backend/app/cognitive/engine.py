from dataclasses import dataclass
import re
from typing import Optional


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


TAXONOMY = {
    "NameError": ClassificationResult("NameError", "Variable Initialization", "State awareness"),
    "TypeError": ClassificationResult("TypeError", "Data Type Compatibility", "Type reasoning"),
    "IndexError": ClassificationResult("IndexError", "List Management", "Boundary reasoning"),
    "KeyError": ClassificationResult("KeyError", "Dictionary Usage", "Mapping reasoning"),
}

REFLECTION_QUESTIONS = {
    "Variable Initialization": "Where in your code should the variable have been created before it was used?",
    "Data Type Compatibility": "What types of values are you trying to combine, and do they work together in Python?",
    "List Management": "What is the length of your list, and which index are you trying to access?",
    "Dictionary Usage": "What keys does your dictionary actually contain, and which one were you trying to access?",
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
    return TAXONOMY.get(parsed.exception_type)


def get_reflection_question(concept_category: str) -> str:
    return REFLECTION_QUESTIONS.get(concept_category, "What do you think caused this error?")

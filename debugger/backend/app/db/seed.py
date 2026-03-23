from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def run_seed(db: AsyncSession) -> None:
    seed_data = [
        ("Variable Initialization", "Variable used before being assigned a value", "State awareness"),
        ("Typo / Spelling", "Identifier name is a misspelling of a known builtin or variable", "Attention to detail"),
        ("Data Type Compatibility", "Operation attempted between incompatible types", "Type reasoning"),
        ("Object Attributes", "Attribute or method accessed on wrong object type", "Object model reasoning"),
        ("Value Validity", "Value passed is the right type but semantically invalid", "Input validation reasoning"),
        ("List Management", "Index access outside list bounds", "Boundary reasoning"),
        ("Dictionary Usage", "Key accessed that does not exist in dictionary", "Mapping reasoning"),
        ("Syntax", "Code structure violates Python grammar rules", "Code structure"),
        ("Mathematical Operations", "Arithmetic operation produces undefined result", "Logic reasoning"),
        ("Module Usage", "Import of a module that is missing or misspelled", "Dependency reasoning"),
        ("Recursion", "Recursive function lacks a reachable base case", "Recursive logic reasoning"),
        ("Runtime Behaviour", "Error raised during execution due to unexpected program state", "Execution flow reasoning"),
        ("Iteration", "Iterator exhausted or used incorrectly", "Iterator reasoning"),
        ("Resource Management", "Program exceeds memory or resource limits", "Memory reasoning"),
        ("File I/O", "File path missing, inaccessible, or permission denied", "File system reasoning"),
        ("String Encoding", "String decoded or encoded with wrong codec", "Encoding reasoning"),
        ("Assertions", "Assert statement condition evaluated to False", "Defensive programming"),
    ]

    for name, description, cognitive_skill in seed_data:
        stmt = text("""
            INSERT INTO concept_categories (name, description, cognitive_skill)
            VALUES (:name, :description, :cognitive_skill)
            ON CONFLICT (name) DO NOTHING
        """)
        await db.execute(stmt, {"name": name, "description": description, "cognitive_skill": cognitive_skill})

    await db.commit()


async def run_hint_seed(db: AsyncSession) -> None:
    hint_data = [
        # Variable Initialization
        ("Variable Initialization", 1, "Concept", "Check where variables are defined before use."),
        ("Variable Initialization", 2, "Directional", "Initialize the variable before the line that uses it."),
        ("Variable Initialization", 3, "Near-Solution", "You need to assign a value to the variable on a line before you reference it."),
        # Typo / Spelling
        ("Typo / Spelling", 1, "Concept", "Look carefully at the name — does it match the correct Python spelling?"),
        ("Typo / Spelling", 2, "Directional", "Compare the name character by character against the Python documentation or your earlier definition."),
        ("Typo / Spelling", 3, "Near-Solution", "Correct the spelling of the identifier. Python names are case-sensitive and must match exactly."),
        # Data Type Compatibility
        ("Data Type Compatibility", 1, "Concept", "Check the types of the values you are combining."),
        ("Data Type Compatibility", 2, "Directional", "Python cannot add a string and an integer directly — convert one first."),
        ("Data Type Compatibility", 3, "Near-Solution", "Use `str()` or `int()` to convert one value to match the other's type."),
        # Object Attributes
        ("Object Attributes", 1, "Concept", "Check what type your variable actually is before calling a method on it."),
        ("Object Attributes", 2, "Directional", "Use `print(type(my_var))` to confirm the type, then look up which methods it supports."),
        ("Object Attributes", 3, "Near-Solution", "The method or attribute you called does not exist on this type. Replace it with the correct one from the Python docs."),
        # Value Validity
        ("Value Validity", 1, "Concept", "The type is correct but the value itself is not valid for this operation."),
        ("Value Validity", 2, "Directional", "Add a check before the operation to ensure the value is within the expected range or format."),
        ("Value Validity", 3, "Near-Solution", "Validate the value with an `if` statement or try/except before passing it to the function."),
        # List Management
        ("List Management", 1, "Concept", "Check the valid index range for your list before accessing it."),
        ("List Management", 2, "Directional", "List indices start at 0 — the last valid index is `len(list) - 1`."),
        ("List Management", 3, "Near-Solution", "Your list has fewer items than the index you are using. Check the list length first."),
        # Dictionary Usage
        ("Dictionary Usage", 1, "Concept", "Check which keys actually exist in your dictionary before accessing them."),
        ("Dictionary Usage", 2, "Directional", "Use `in` to check if a key exists before accessing it, or use `.get()` with a default."),
        ("Dictionary Usage", 3, "Near-Solution", "The key you are accessing was never added to the dictionary. Print the dictionary to see its actual contents."),
        # Syntax
        ("Syntax", 1, "Concept", "Python requires specific punctuation to define code structure — check the highlighted line."),
        ("Syntax", 2, "Directional", "Look for a missing colon at the end of an `if`, `for`, `def`, or `class` statement, or unmatched parentheses/quotes."),
        ("Syntax", 3, "Near-Solution", "Add the missing punctuation on the indicated line. Common fixes: add `:` after a block header, close an open `(` or `\"`."),
        # Mathematical Operations
        ("Mathematical Operations", 1, "Concept", "Check the value of the denominator before dividing."),
        ("Mathematical Operations", 2, "Directional", "Add a guard: `if divisor != 0:` before the division to prevent a ZeroDivisionError."),
        ("Mathematical Operations", 3, "Near-Solution", "The divisor is zero. Either change the logic so it cannot be zero, or handle the zero case explicitly with an `if` check."),
        # Module Usage
        ("Module Usage", 1, "Concept", "Check that the module name is spelled correctly and that it is available in this environment."),
        ("Module Usage", 2, "Directional", "Standard library modules are always available. Third-party modules must be installed with `pip install <name>`."),
        ("Module Usage", 3, "Near-Solution", "Correct the module name spelling, or install the missing package. Check `pip list` to see what is installed."),
        # Recursion
        ("Recursion", 1, "Concept", "Every recursive function must have a base case that stops the recursion."),
        ("Recursion", 2, "Directional", "Trace through your function manually: does it always reach a return statement without calling itself again?"),
        ("Recursion", 3, "Near-Solution", "Add a base case `if <condition>: return <value>` at the top of your function so recursion terminates."),
        # Runtime Behaviour
        ("Runtime Behaviour", 1, "Concept", "A RuntimeError means Python reached a state it cannot recover from during execution."),
        ("Runtime Behaviour", 2, "Directional", "Read the error message carefully — it usually describes the exact condition that failed."),
        ("Runtime Behaviour", 3, "Near-Solution", "Fix the condition described in the error message. Add defensive checks before the failing line."),
        # Iteration
        ("Iteration", 1, "Concept", "Check whether you are calling `next()` on an iterator that may already be exhausted."),
        ("Iteration", 2, "Directional", "Iterators can only be traversed once. Convert to a list first if you need to iterate multiple times."),
        ("Iteration", 3, "Near-Solution", "Replace the exhausted iterator with a fresh one, or convert it to a list with `list(iterator)` before iterating."),
        # Resource Management
        ("Resource Management", 1, "Concept", "Your program is using more memory than the sandbox allows."),
        ("Resource Management", 2, "Directional", "Look for loops that create large lists or strings. Avoid storing all data in memory at once."),
        ("Resource Management", 3, "Near-Solution", "Reduce the size of the data structure being built, or process data in smaller chunks instead of all at once."),
        # File I/O
        ("File I/O", 1, "Concept", "Check that the file path you are using actually exists and is spelled correctly."),
        ("File I/O", 2, "Directional", "Use `os.path.exists(path)` to verify the path before opening the file."),
        ("File I/O", 3, "Near-Solution", "Correct the file path. Remember that relative paths are resolved from the working directory, not the script location."),
        # String Encoding
        ("String Encoding", 1, "Concept", "The file or string uses a different character encoding than the one you specified."),
        ("String Encoding", 2, "Directional", "Try opening the file with `encoding='utf-8'` or `encoding='latin-1'` depending on its origin."),
        ("String Encoding", 3, "Near-Solution", "Add `errors='replace'` or `errors='ignore'` to the `open()` call to handle undecodable bytes gracefully."),
        # Assertions
        ("Assertions", 1, "Concept", "An `assert` statement failed because its condition evaluated to False."),
        ("Assertions", 2, "Directional", "Print the value being asserted before the assert line to understand why the condition is False."),
        ("Assertions", 3, "Near-Solution", "Fix the logic so the asserted condition is True, or update the assertion to match the actual expected value."),
    ]

    for concept_category, tier, tier_name, hint_text in hint_data:
        stmt = text("""
            INSERT INTO hint_sequences (concept_category, tier, tier_name, hint_text)
            VALUES (:concept_category, :tier, :tier_name, :hint_text)
            ON CONFLICT (concept_category, tier) DO NOTHING
        """)
        await db.execute(stmt, {
            "concept_category": concept_category,
            "tier": tier,
            "tier_name": tier_name,
            "hint_text": hint_text,
        })

    await db.commit()

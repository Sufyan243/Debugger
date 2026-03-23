import re


def compare_predictions(prediction: str, actual_output: str) -> bool:
    """
    Compare prediction with actual output using normalized string comparison.
    
    Normalizes both strings by:
    - Stripping leading/trailing whitespace
    - Collapsing internal whitespace runs to single space
    - Case-insensitive comparison
    
    Args:
        prediction: Student's predicted output
        actual_output: Actual execution output
        
    Returns:
        True if normalized strings match, False otherwise
    """
    def normalize(s: str) -> str:
        # Preserve case — Python is case-sensitive and students must learn that.
        # Only collapse internal whitespace runs and strip edges.
        return re.sub(r'\s+', ' ', s).strip()

    return normalize(prediction) == normalize(actual_output)


def compute_accuracy(correct: int, total: int) -> float:
    """
    Compute accuracy ratio from correct and total prediction counts.
    
    Args:
        correct: Number of correct predictions
        total: Total number of predictions
        
    Returns:
        Accuracy ratio rounded to 4 decimal places, or 0.0 if total is 0
    """
    if total == 0:
        return 0.0
    
    return round(correct / total, 4)

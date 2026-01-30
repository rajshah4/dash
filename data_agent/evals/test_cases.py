"""
Test Cases
==========

Test cases for evaluating the Data Agent.

Each test case is a tuple of:
- question: The natural language question
- expected_values: List of strings that should appear in the response
- category: Category for filtering (basic, aggregation, data_quality, complex, edge_case)

Test cases are designed to verify:
1. Basic query functionality
2. Aggregation and grouping
3. Data quality handling (type mismatches, date parsing)
4. Complex multi-table queries
5. Edge cases and error handling
"""

from typing import NamedTuple


class TestCase(NamedTuple):
    """A test case for evaluation."""

    question: str
    expected_values: list[str]
    category: str


# ============================================================================
# Test Cases
# ============================================================================

TEST_CASES: list[TestCase] = [
    # Basic queries
    TestCase(
        question="Who won the most races in 2019?",
        expected_values=["Lewis Hamilton", "11"],
        category="basic",
    ),
    TestCase(
        question="Which team won the 2020 constructors championship?",
        expected_values=["Mercedes"],
        category="basic",
    ),
    TestCase(
        question="Who won the 2020 drivers championship?",
        expected_values=["Lewis Hamilton"],
        category="basic",
    ),
    # Aggregation queries
    TestCase(
        question="Which driver has won the most world championships?",
        expected_values=["Michael Schumacher", "7"],
        category="aggregation",
    ),
    TestCase(
        question="Which constructor has won the most championships?",
        expected_values=["Ferrari"],
        category="aggregation",
    ),
    TestCase(
        question="Who has the most fastest laps at Monaco?",
        expected_values=["Michael Schumacher"],
        category="aggregation",
    ),
    TestCase(
        question="How many race wins does Lewis Hamilton have?",
        expected_values=["Hamilton"],
        category="aggregation",
    ),
    # Data quality tests (these verify the agent handles type mismatches correctly)
    TestCase(
        question="Who finished second in the 2019 drivers championship?",
        expected_values=["Valtteri Bottas"],
        category="data_quality",
    ),
    TestCase(
        question="Which team came third in the 2020 constructors championship?",
        expected_values=["Racing Point"],
        category="data_quality",
    ),
    TestCase(
        question="How many races did Ferrari win in 2019?",
        expected_values=["3"],
        category="data_quality",
    ),
    # Complex queries (multi-table, time ranges)
    TestCase(
        question="Compare Ferrari vs Mercedes championship points from 2015-2020",
        expected_values=["Ferrari", "Mercedes"],
        category="complex",
    ),
    TestCase(
        question="Who had the most podium finishes in 2019?",
        expected_values=["Lewis Hamilton"],
        category="complex",
    ),
    # Edge cases
    TestCase(
        question="How many retirements were there in 2020?",
        expected_values=["Ret"],
        category="edge_case",
    ),
    TestCase(
        question="List all constructors championships Ferrari has won",
        expected_values=["Ferrari"],
        category="edge_case",
    ),
]

# Categories for filtering
CATEGORIES = ["basic", "aggregation", "data_quality", "complex", "edge_case"]


def get_test_cases(category: str | None = None) -> list[TestCase]:
    """Get test cases, optionally filtered by category.

    Args:
        category: Category to filter by, or None for all.

    Returns:
        List of matching test cases.
    """
    if category is None:
        return TEST_CASES
    return [tc for tc in TEST_CASES if tc.category == category]

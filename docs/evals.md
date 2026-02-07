# Evaluations

Dash includes an end-to-end evaluation harness that sends questions to the agent, checks responses, and reports results. Test cases live in `dash/evals/test_cases.py`.

## Run Evals

```sh
python -m dash.evals.run_evals                  # Run all evals (string matching)
python -m dash.evals.run_evals -c basic         # Run specific category
python -m dash.evals.run_evals -v               # Verbose mode (show responses)
python -m dash.evals.run_evals -g               # Use LLM grader
python -m dash.evals.run_evals -r               # Compare against golden SQL results
python -m dash.evals.run_evals -g -r -v         # All modes combined
```

## Test Case Format

Each test case is a `TestCase` dataclass in `dash/evals/test_cases.py`:

```python
from dash.evals.test_cases import TestCase

TestCase(
    question="Who won the most races in 2019?",       # Natural language question
    expected_strings=["Hamilton", "11"],                # Strings that must appear in the response
    category="basic",                                   # Category for filtering
    golden_sql="""                                      # Optional: SQL that produces the expected result
        SELECT name, COUNT(*) as wins
        FROM race_wins
        WHERE TO_DATE(date, 'DD Mon YYYY') >= '2019-01-01'
          AND TO_DATE(date, 'DD Mon YYYY') < '2020-01-01'
        GROUP BY name
        ORDER BY wins DESC
        LIMIT 1
    """,
    expected_result="Hamilton",                         # Optional: simple expected value
)
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `question` | Yes | The question sent to the agent |
| `expected_strings` | Yes | Strings that should appear in the response (case-insensitive) |
| `category` | Yes | One of: `basic`, `aggregation`, `data_quality`, `complex`, `edge_case` |
| `golden_sql` | No | SQL query that produces the correct result — used for result comparison (`-r`) and LLM grading (`-g`) |
| `expected_result` | No | Simple expected value (e.g., a count) — for documentation/reference |

## Adding a New Test Case

1. Open `dash/evals/test_cases.py`
2. Add a `TestCase` to the `TEST_CASES` list
3. Choose a category or add a new one to `CATEGORIES`

**Example — adding a new aggregation test:**

```python
TestCase(
    question="Which driver has the most pole positions?",
    expected_strings=["Hamilton"],
    category="aggregation",
    golden_sql="""
        SELECT name, COUNT(*) as poles
        FROM qualifying_results
        WHERE position = 1
        GROUP BY name
        ORDER BY poles DESC
        LIMIT 1
    """,
),
```

**Tips:**
- Keep `expected_strings` short — just the key values that must appear (names, numbers).
- Use `golden_sql` when you can write a reference query. This enables the `-r` and `-g` modes.
- For questions with no clear SQL answer (e.g., "explain X"), omit `golden_sql` and rely on string matching.
- If you add a new category, also add it to `CATEGORIES` at the bottom of the file.

## Categories

| Category | Tests | What It Covers |
|----------|------:|----------------|
| `basic` | Simple lookups | Single-table queries, direct answers |
| `aggregation` | GROUP BY | Counts, rankings, top-N queries |
| `data_quality` | Type handling | `position` as TEXT vs INTEGER, date parsing |
| `complex` | Multi-table | JOINs, comparisons, multiple conditions |
| `edge_case` | Boundary conditions | Empty results, missing data, historical gaps |

## Grading Modes

### String Matching (default)

Checks whether each string in `expected_strings` appears in the agent's response (case-insensitive). Fast and deterministic.

### Result Comparison (`-r`)

When `golden_sql` is provided, executes the SQL against the live database and checks that the golden result values appear in the agent's response. Catches cases where the agent generates plausible but incorrect SQL.

### LLM Grading (`-g`)

Sends the question, agent response, expected values, and golden SQL results to a small LLM (`gpt-5-mini` by default) which scores the response on correctness, completeness, and absence of hallucinations. Returns a 0.0–1.0 score.

Requires `OPENAI_API_KEY` in your environment (or any OpenAI-compatible endpoint).

### Combined (`-g -r -v`)

Runs all three modes. The final pass/fail is determined by: LLM grade if available, then result comparison, then string matching as a fallback.

## Output

The eval runner uses [Rich](https://rich.readthedocs.io/) for formatted output:

- **Results table** — status, category, question, time, and notes for each test
- **Category breakdown** — pass rate per category
- **Summary** — total pass rate, average time, average LLM score (if grading)
- **Verbose failures** — full agent responses for failed tests (with `-v`)

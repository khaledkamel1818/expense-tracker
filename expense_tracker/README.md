# Expense Tracker

A clean, object-oriented personal expense tracker written in **pure
Python** (standard library only). It records expenses by category, edits
and deletes them, filters by category, month, date range or amount, tracks
monthly budgets with warnings, and produces reports such as category
breakdowns, monthly totals, top expenses, statistics and CSV export, with
input validation and clear error handling throughout.

## Features

- **Full CRUD**: add, view, update and delete expenses.
- **Exact money**: amounts use `decimal.Decimal`, rounded to cents, so
  totals never suffer from floating-point errors.
- **Categories**: a fixed `Category` enum (Food, Transport, Housing,
  Utilities, Health, Entertainment, Education, Other), accepted in any case.
- **Filtering**: by category, month (`YYYY-MM`), date range and minimum
  amount, combined freely.
- **Budgets**: a monthly limit per category with `OK`, `WARNING` (80% used)
  and `OVER` statuses.
- **Reports**: category breakdown with percentages, monthly totals, top
  expenses and overall statistics.
- **CSV export**: any list of expenses as CSV text.
- **Validation and errors**: a custom exception hierarchy for invalid
  amounts, categories, dates and unknown expenses.
- **Zero dependencies**: runs anywhere Python 3.8+ is installed.

## Project structure

```
expense_tracker/
├── expense_tracker.py   # Classes and a runnable demonstration
├── README.md            # This file
└── requirements.txt     # No external dependencies
```

## Installation

```bash
git clone https://github.com/khaledkamel1818/expense-tracker.git
cd expense-tracker/expense_tracker
python expense_tracker.py
```

No `pip install` is needed.

## Usage

```python
from datetime import date
from expense_tracker import Category, ExpenseTracker, ExpenseTrackerError

tracker = ExpenseTracker(currency="EGP")

# Record expenses (category as an enum or as text)
tracker.add_expense(6500, "Housing", "Monthly rent", date(2024, 9, 1))
tracker.add_expense(1350.25, Category.FOOD, "Groceries", date(2024, 9, 6))
coffee = tracker.add_expense("45.50", "food", "Coffee")   # today

# Edit and delete
tracker.update_expense(coffee.expense_id, amount=50)
tracker.delete_expense(coffee.expense_id)

# Filter and report
food = tracker.filter(category="Food", month="2024-09")
print(tracker.total(food))                    # 1350.25
print(tracker.category_breakdown("2024-09"))
print(tracker.monthly_totals())
print(tracker.top_expenses(3))
print(tracker.get_statistics())

# Budgets
tracker.set_budget("Food", 1500)
print(tracker.budget_report("2024-09"))       # Food: 90.0% used, WARNING

# Output
tracker.display_expenses()
print(tracker.export_csv())

# Errors are explicit and catchable
try:
    tracker.add_expense(-50, "Food", "Refund?")
except ExpenseTrackerError as error:
    print(error)   # Amount must be greater than zero.
```

## Classes and methods

### `Category` (Enum)

| Member | Description |
|---|---|
| `FOOD`, `TRANSPORT`, `HOUSING`, ... | The supported categories. |
| `Category.parse(value)` | Accepts a `Category` or its name/value in any case. |

### `Expense` (immutable value object)

| Member | Description |
|---|---|
| `expense_id`, `amount`, `category`, `description`, `spent_on` | Validated on creation; cannot be changed afterwards. |
| `month` | The month as `'YYYY-MM'`. |

### `Budget`

| Member | Description |
|---|---|
| `Budget(category, monthly_limit, warning_ratio=0.8)` | A validated monthly limit. |
| `status(spent)` | `'OK'`, `'WARNING'` or `'OVER'`. |

### `ExpenseTracker`

| Method | Description |
|---|---|
| `add_expense(amount, category, description, spent_on=None)` | Records an expense and returns it. |
| `get_expense(expense_id)` | Returns an expense or raises `ExpenseNotFoundError`. |
| `update_expense(expense_id, **changes)` | Replaces fields; the new record is validated first. |
| `delete_expense(expense_id)` | Removes and returns an expense. |
| `filter(category=, month=, start=, end=, min_amount=)` | Expenses matching every given filter. |
| `total(expenses)` | Sum of a list of expenses. |
| `totals_by_category(expenses)` | Sum per category. |
| `category_breakdown(month=None)` | Total and share per category, largest first. |
| `monthly_totals()` | Total per month. |
| `top_expenses(n=3)` | The largest expenses. |
| `set_budget(category, monthly_limit)` | Creates or replaces a budget. |
| `budget_report(month)` | Spending against every budget for a month. |
| `get_statistics()` | A dictionary of overall statistics. |
| `export_csv(expenses=None)` | CSV text of the given (or all) expenses. |
| `display_expenses(expenses=None)` | Prints a formatted table with a total. |
| `len(tracker)` | Number of expenses. |

### Exceptions

```
ExpenseTrackerError
├── ValidationError        # bad amount, category, text, date or month
└── ExpenseNotFoundError   # unknown expense ID
```

## OOP concepts used

- **Encapsulation**: expenses and budgets are stored privately and only
  change through validated methods.
- **Abstraction**: callers ask for `budget_report("2024-09")` without
  knowing how expenses are grouped and summed.
- **Immutability**: `Expense` is a frozen dataclass; `update_expense`
  builds a new, re-validated record with `dataclasses.replace`.
- **Enumerations**: `Category` makes invalid categories impossible.
- **Composition**: an `ExpenseTracker` *has* expenses and budgets.
- **Inheritance**: the exception hierarchy derives from a common base class.
- **Static methods**: `total` and `totals_by_category` work on any list of
  expenses, not only the tracker's own.

### SOLID principles

- **Single Responsibility**: `Expense` validates one record, `Budget`
  judges spending against a limit, `ExpenseTracker` manages the collection
  and reports.
- **Open/Closed**: adding a category is one new `Category` member; nothing
  else changes.
- **Liskov Substitution**: each custom exception works wherever its base
  (`ExpenseTrackerError`, `ValueError` or `KeyError`) is expected.
- **Interface Segregation**: reports, budgets and CRUD are separate,
  focused methods.
- **Dependency Inversion**: money handling lives in one helper
  (`to_money`) that every class relies on instead of re-implementing it.

## Expected output

Running `python expense_tracker.py` prints:

```
================================================================
1. Recording expenses
================================================================
Recorded 12 expenses.

================================================================
2. All expenses
================================================================
ID   Date        Category       Description               Amount
----------------------------------------------------------------
#1   2024-08-01  Housing        Monthly rent             6500.00
#2   2024-08-03  Utilities      Electricity bill          450.75
#3   2024-08-04  Food           Groceries                1200.00
#4   2024-08-05  Transport      Metro card top-up          85.50
#5   2024-08-10  Entertainment  Cinema and dinner         320.00
#6   2024-08-18  Food           Groceries                 950.00
#7   2024-08-20  Education      Python course            1500.00
#8   2024-08-27  Health         Dentist                   600.00
#9   2024-09-01  Housing        Monthly rent             6500.00
#10  2024-09-06  Food           Groceries                1350.25
#11  2024-09-09  Transport      Taxi rides                210.00
#12  2024-09-14  Entertainment  Concert tickets           780.00
----------------------------------------------------------------
Total (EGP)                                             20446.50

================================================================
3. Editing and deleting
================================================================
  Updated  #6   2024-08-18  Food           Groceries                1010.00
  Deleted  #4   2024-08-05  Transport      Metro card top-up          85.50

================================================================
4. Filtering: Food in August 2024
================================================================
ID   Date        Category       Description               Amount
----------------------------------------------------------------
#3   2024-08-04  Food           Groceries                1200.00
#6   2024-08-18  Food           Groceries                1010.00
----------------------------------------------------------------
Total (EGP)                                              2210.00

================================================================
5. Category breakdown for August 2024
================================================================
  Housing          6500.00   56.1%
  Food             2210.00   19.1%
  Education        1500.00   13.0%
  Health            600.00    5.2%
  Utilities         450.75    3.9%
  Entertainment     320.00    2.8%

================================================================
6. Budgets for September 2024
================================================================
  Entertainment  spent   780.00 of   500.00 (156.0%)  OVER
  Food           spent  1350.25 of  1500.00 ( 90.0%)  WARNING
  Transport      spent   210.00 of   400.00 ( 52.5%)  OK

================================================================
7. Monthly totals, top expenses and statistics
================================================================
  2024-08:  11580.75
  2024-09:   8840.25

  #1   2024-08-01  Housing        Monthly rent             6500.00
  #9   2024-09-01  Housing        Monthly rent             6500.00
  #7   2024-08-20  Education      Python course            1500.00

  expenses          : 11
  total             : 20421.00
  average_expense   : 1856.45
  largest_expense   : 6500.00
  smallest_expense  : 210.00
  first_date        : 2024-08-01
  last_date         : 2024-09-14
  average_per_month : 10210.50
  top_category      : Housing

================================================================
8. CSV export (September 2024)
================================================================
id,date,category,description,amount
9,2024-09-01,Housing,Monthly rent,6500.00
10,2024-09-06,Food,Groceries,1350.25
11,2024-09-09,Transport,Taxi rides,210.00
12,2024-09-14,Entertainment,Concert tickets,780.00

================================================================
9. Error handling
================================================================
  Negative amount    -> ValidationError: Amount must be greater than zero.
  Not a number       -> ValidationError: Amount is not a valid number: 'abc'.
  Unknown category   -> ValidationError: Unknown category 'Pets'. Choose one of: Food, Transport, Housing, Utilities, Health, Entertainment, Education, Other.
  Empty description  -> ValidationError: Description must be a non-empty string.
  Future date        -> ValidationError: Date cannot be in the future.
  Unknown expense    -> ExpenseNotFoundError: No expense with ID 99.
  Bad month          -> ValidationError: Month must look like 'YYYY-MM', got 'Sept 2024'.
  Bad update field   -> ValidationError: Cannot update field(s): owner.
```

## Author

**Khaled Kamel** · [GitHub](https://github.com/khaledkamel1818)

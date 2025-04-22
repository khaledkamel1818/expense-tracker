"""
Expense Tracker.

A small, dependency-free personal finance tracker. It demonstrates
object-oriented design in pure Python:

* ``Category``        - the fixed set of spending categories (an Enum).
* ``Expense``         - one immutable spending record.
* ``Budget``          - a monthly spending limit for one category.
* ``ExpenseTracker``  - stores expenses and budgets and produces reports.

Money is handled with ``decimal.Decimal`` so totals are always exact
(``0.1 + 0.2`` really is ``0.3``).

Run this file directly to see a full demonstration::

    python expense_tracker.py
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from itertools import count
from typing import Dict, Iterable, List, Optional, Union


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------

class ExpenseTrackerError(Exception):
    """Base class for every error raised by this module."""


class ValidationError(ExpenseTrackerError, ValueError):
    """Raised when input data is invalid (negative amount, bad date...)."""


class ExpenseNotFoundError(ExpenseTrackerError, KeyError):
    """Raised when an expense ID does not exist."""

    def __str__(self) -> str:  # KeyError would otherwise wrap it in quotes
        return str(self.args[0]) if self.args else ""


# --------------------------------------------------------------------------
# Money and validation helpers
# --------------------------------------------------------------------------

Number = Union[int, float, str, Decimal]
CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000")


def to_money(value: Number, field_name: str = "Amount") -> Decimal:
    """Convert ``value`` to a positive Decimal rounded to cents.

    Floats are converted through ``str`` so that ``19.99`` stays exactly
    ``19.99`` instead of ``19.989999999...``.
    """
    if isinstance(value, bool) or not isinstance(value,
                                                 (int, float, str, Decimal)):
        raise ValidationError(f"{field_name} must be a number.")
    try:
        amount = Decimal(str(value).strip())
    except InvalidOperation:
        amount = Decimal("NaN")
    if not amount.is_finite():
        raise ValidationError(
            f"{field_name} is not a valid number: {value!r}.")
    if amount > MAX_AMOUNT:
        raise ValidationError(f"{field_name} cannot exceed {MAX_AMOUNT}.")
    amount = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return amount


def _require_text(value: str, field_name: str) -> str:
    """Return ``value`` stripped, or raise if it is empty or not a string."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _validate_date(value: date) -> date:
    if not isinstance(value, date):
        raise ValidationError("Date must be a datetime.date.")
    if value > date.today():
        raise ValidationError("Date cannot be in the future.")
    return value


def _validate_month(month: str) -> str:
    """Accept a month as ``'YYYY-MM'`` and return it unchanged."""
    try:
        date.fromisoformat(f"{month}-01")
    except (TypeError, ValueError):
        raise ValidationError(
            f"Month must look like 'YYYY-MM', got {month!r}.") from None
    return month


def _percent(part: Decimal, whole: Decimal) -> float:
    return round(float(part / whole * 100), 1) if whole else 0.0


# --------------------------------------------------------------------------
# Domain classes
# --------------------------------------------------------------------------

class Category(Enum):
    """Spending categories. Add a member here to support a new one."""

    FOOD = "Food"
    TRANSPORT = "Transport"
    HOUSING = "Housing"
    UTILITIES = "Utilities"
    HEALTH = "Health"
    ENTERTAINMENT = "Entertainment"
    EDUCATION = "Education"
    OTHER = "Other"

    @classmethod
    def parse(cls, value: Union["Category", str]) -> "Category":
        """Accept a ``Category`` or its name/value in any case."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            for category in cls:
                if value.strip().lower() in (category.name.lower(),
                                             category.value.lower()):
                    return category
        valid = ", ".join(c.value for c in cls)
        raise ValidationError(
            f"Unknown category {value!r}. Choose one of: {valid}.")


@dataclass(frozen=True)
class Expense:
    """One spending record (immutable; edits create a new record)."""

    expense_id: int
    amount: Decimal
    category: Category
    description: str
    spent_on: date

    def __post_init__(self) -> None:
        # frozen dataclasses need object.__setattr__ to normalize fields.
        object.__setattr__(self, "amount", to_money(self.amount))
        object.__setattr__(self, "category", Category.parse(self.category))
        object.__setattr__(self, "description",
                           _require_text(self.description, "Description"))
        object.__setattr__(self, "spent_on", _validate_date(self.spent_on))

    @property
    def month(self) -> str:
        """The month of the expense as ``'YYYY-MM'``."""
        return self.spent_on.strftime("%Y-%m")

    def __str__(self) -> str:
        return (f"#{self.expense_id:<3} {self.spent_on}  "
                f"{self.category.value:<14} {self.description:<22} "
                f"{self.amount:>9.2f}")


@dataclass
class Budget:
    """A monthly spending limit for one category."""

    category: Category
    monthly_limit: Decimal
    warning_ratio: float = 0.8

    def __post_init__(self) -> None:
        self.category = Category.parse(self.category)
        self.monthly_limit = to_money(self.monthly_limit, "Monthly limit")
        if not 0 < self.warning_ratio <= 1:
            raise ValidationError("Warning ratio must be in (0, 1].")

    def status(self, spent: Decimal) -> str:
        """``'OK'``, ``'WARNING'`` (near the limit) or ``'OVER'``."""
        if spent > self.monthly_limit:
            return "OVER"
        if spent >= self.monthly_limit * Decimal(str(self.warning_ratio)):
            return "WARNING"
        return "OK"


class ExpenseTracker:
    """Stores expenses and budgets and builds reports from them.

    Responsibility (SRP): manage the collection. Validation of a single
    record lives in ``Expense`` and ``Budget``; reports only read data.
    """

    def __init__(self, currency: str = "EGP") -> None:
        self.currency = _require_text(currency, "Currency").upper()
        self._expenses: Dict[int, Expense] = {}
        self._budgets: Dict[Category, Budget] = {}
        self._ids = count(1)

    # ----- CRUD -----------------------------------------------------------

    def add_expense(self, amount: Number, category: Union[Category, str],
                    description: str,
                    spent_on: Optional[date] = None) -> Expense:
        """Record a new expense and return it."""
        expense = Expense(next(self._ids), amount, category, description,
                          spent_on or date.today())
        self._expenses[expense.expense_id] = expense
        return expense

    def get_expense(self, expense_id: int) -> Expense:
        try:
            return self._expenses[expense_id]
        except KeyError:
            raise ExpenseNotFoundError(
                f"No expense with ID {expense_id!r}.") from None

    def update_expense(self, expense_id: int, **changes: object) -> Expense:
        """Replace fields of an expense (amount, category, description,
        spent_on). The new record is validated before it is stored.
        """
        allowed = {"amount", "category", "description", "spent_on"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValidationError(
                f"Cannot update field(s): {', '.join(sorted(unknown))}.")
        updated = replace(self.get_expense(expense_id), **changes)
        self._expenses[expense_id] = updated
        return updated

    def delete_expense(self, expense_id: int) -> Expense:
        expense = self.get_expense(expense_id)
        del self._expenses[expense_id]
        return expense

    # ----- budgets --------------------------------------------------------

    def set_budget(self, category: Union[Category, str],
                   monthly_limit: Number) -> Budget:
        """Create or replace the monthly budget for a category."""
        budget = Budget(category, monthly_limit)
        self._budgets[budget.category] = budget
        return budget

    def budget_report(self, month: str) -> List[Dict[str, object]]:
        """Spending against every budget for ``month`` ('YYYY-MM')."""
        spent = self.totals_by_category(self.filter(month=month))
        report = []
        for category, budget in sorted(self._budgets.items(),
                                       key=lambda kv: kv[0].value):
            used = spent.get(category, Decimal("0.00"))
            report.append({
                "category": category.value,
                "limit": budget.monthly_limit,
                "spent": used,
                "remaining": budget.monthly_limit - used,
                "used_pct": _percent(used, budget.monthly_limit),
                "status": budget.status(used),
            })
        return report

    # ----- queries --------------------------------------------------------

    def __len__(self) -> int:
        return len(self._expenses)

    def filter(self, *, category: Union[Category, str, None] = None,
               month: Optional[str] = None,
               start: Optional[date] = None, end: Optional[date] = None,
               min_amount: Optional[Number] = None) -> List[Expense]:
        """Expenses matching every given filter, oldest first."""
        wanted = Category.parse(category) if category is not None else None
        if month is not None:
            _validate_month(month)
        if start and end and start > end:
            raise ValidationError("Start date is after end date.")
        floor = to_money(min_amount, "Minimum amount") if min_amount else None

        result = [
            e for e in self._expenses.values()
            if (wanted is None or e.category is wanted)
            and (month is None or e.month == month)
            and (start is None or e.spent_on >= start)
            and (end is None or e.spent_on <= end)
            and (floor is None or e.amount >= floor)
        ]
        return sorted(result, key=lambda e: (e.spent_on, e.expense_id))

    @staticmethod
    def total(expenses: Iterable[Expense]) -> Decimal:
        return sum((e.amount for e in expenses), Decimal("0.00"))

    @staticmethod
    def totals_by_category(
            expenses: Iterable[Expense]) -> Dict[Category, Decimal]:
        totals: Dict[Category, Decimal] = {}
        for e in expenses:
            totals[e.category] = totals.get(e.category,
                                            Decimal("0.00")) + e.amount
        return totals

    def category_breakdown(
            self, month: Optional[str] = None) -> List[Dict[str, object]]:
        """Total and share of spending per category, largest first."""
        expenses = self.filter(month=month)
        grand_total = self.total(expenses)
        totals = self.totals_by_category(expenses)
        return [
            {"category": cat.value, "total": amount,
             "share_pct": _percent(amount, grand_total)}
            for cat, amount in sorted(totals.items(),
                                      key=lambda kv: (-kv[1], kv[0].value))
        ]

    def monthly_totals(self) -> Dict[str, Decimal]:
        """Total spending per month, in date order."""
        totals: Dict[str, Decimal] = {}
        for e in self.filter():
            totals[e.month] = totals.get(e.month, Decimal("0.00")) + e.amount
        return totals

    def top_expenses(self, n: int = 3) -> List[Expense]:
        """The ``n`` largest expenses."""
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValidationError("n must be a positive integer.")
        return sorted(self._expenses.values(),
                      key=lambda e: (-e.amount, e.expense_id))[:n]

    def get_statistics(self) -> Dict[str, object]:
        """Overall statistics as a dictionary."""
        expenses = self.filter()
        if not expenses:
            return {"expenses": 0, "total": Decimal("0.00")}
        total = self.total(expenses)
        months = self.monthly_totals()
        breakdown = self.category_breakdown()
        return {
            "expenses": len(expenses),
            "total": total,
            "average_expense": (total / len(expenses)).quantize(CENT),
            "largest_expense": max(e.amount for e in expenses),
            "smallest_expense": min(e.amount for e in expenses),
            "first_date": expenses[0].spent_on.isoformat(),
            "last_date": expenses[-1].spent_on.isoformat(),
            "average_per_month": (total / len(months)).quantize(CENT),
            "top_category": breakdown[0]["category"],
        }

    # ----- output ---------------------------------------------------------

    def export_csv(self, expenses: Optional[Iterable[Expense]] = None) -> str:
        """Return expenses as CSV text (all of them by default)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["id", "date", "category", "description", "amount"])
        for e in (self.filter() if expenses is None else expenses):
            writer.writerow([e.expense_id, e.spent_on.isoformat(),
                             e.category.value, e.description, e.amount])
        return buffer.getvalue()

    def display_expenses(self,
                         expenses: Optional[Iterable[Expense]] = None) -> None:
        """Print expenses as a table with a total line."""
        rows = self.filter() if expenses is None else list(expenses)
        if not rows:
            print("No expenses recorded.")
            return
        print(f"{'ID':<4} {'Date':<11} {'Category':<14} "
              f"{'Description':<22} {'Amount':>9}")
        print("-" * 64)
        for e in rows:
            print(e)
        print("-" * 64)
        print(f"{'Total (' + self.currency + ')':<53}"
              f"{self.total(rows):>11.2f}")


# --------------------------------------------------------------------------
# Demonstration
# --------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def main() -> None:
    """Walk through every feature of the tracker."""
    tracker = ExpenseTracker("EGP")

    _section("1. Recording expenses")
    entries = [
        (6500, "Housing", "Monthly rent", date(2024, 8, 1)),
        (450.75, "Utilities", "Electricity bill", date(2024, 8, 3)),
        (1200, "food", "Groceries", date(2024, 8, 4)),
        (85.50, Category.TRANSPORT, "Metro card top-up", date(2024, 8, 5)),
        (320, "Entertainment", "Cinema and dinner", date(2024, 8, 10)),
        (950, "Food", "Groceries", date(2024, 8, 18)),
        (1500, "Education", "Python course", date(2024, 8, 20)),
        (600, "Health", "Dentist", date(2024, 8, 27)),
        (6500, "Housing", "Monthly rent", date(2024, 9, 1)),
        (1350.25, "Food", "Groceries", date(2024, 9, 6)),
        (210, "Transport", "Taxi rides", date(2024, 9, 9)),
        (780, "Entertainment", "Concert tickets", date(2024, 9, 14)),
    ]
    for amount, category, description, spent_on in entries:
        tracker.add_expense(amount, category, description, spent_on)
    print(f"Recorded {len(tracker)} expenses.")

    _section("2. All expenses")
    tracker.display_expenses()

    _section("3. Editing and deleting")
    updated = tracker.update_expense(6, amount=1010, description="Groceries")
    print(f"  Updated  {updated}")
    removed = tracker.delete_expense(4)
    print(f"  Deleted  {removed}")

    _section("4. Filtering: Food in August 2024")
    tracker.display_expenses(tracker.filter(category="Food", month="2024-08"))

    _section("5. Category breakdown for August 2024")
    for row in tracker.category_breakdown("2024-08"):
        print(f"  {row['category']:<14} {row['total']:>9.2f}  "
              f"{row['share_pct']:>5.1f}%")

    _section("6. Budgets for September 2024")
    tracker.set_budget("Food", 1500)
    tracker.set_budget("Entertainment", 500)
    tracker.set_budget("Transport", 400)
    for row in tracker.budget_report("2024-09"):
        print(f"  {row['category']:<14} spent {row['spent']:>8.2f} of "
              f"{row['limit']:>8.2f} ({row['used_pct']:>5.1f}%)  "
              f"{row['status']}")

    _section("7. Monthly totals, top expenses and statistics")
    for month, amount in tracker.monthly_totals().items():
        print(f"  {month}: {amount:>9.2f}")
    print()
    for expense in tracker.top_expenses(3):
        print(f"  {expense}")
    print()
    for key, value in tracker.get_statistics().items():
        print(f"  {key:<18}: {value}")

    _section("8. CSV export (September 2024)")
    print(tracker.export_csv(tracker.filter(month="2024-09")), end="")

    _section("9. Error handling")
    bad_calls = [
        ("Negative amount",
         lambda: tracker.add_expense(-50, "Food", "Refund?")),
        ("Not a number",
         lambda: tracker.add_expense("abc", "Food", "Snack")),
        ("Unknown category",
         lambda: tracker.add_expense(100, "Pets", "Cat food")),
        ("Empty description",
         lambda: tracker.add_expense(100, "Food", "   ")),
        ("Future date",
         lambda: tracker.add_expense(100, "Food", "Lunch",
                                     date(2999, 1, 1))),
        ("Unknown expense", lambda: tracker.delete_expense(99)),
        ("Bad month", lambda: tracker.filter(month="Sept 2024")),
        ("Bad update field",
         lambda: tracker.update_expense(1, owner="Khaled")),
    ]
    for label, call in bad_calls:
        try:
            call()
        except ExpenseTrackerError as error:
            print(f"  {label:<18} -> {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()

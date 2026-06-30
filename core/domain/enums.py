"""Domain enumerations."""

from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class ProfileType(str, Enum):
    PERSONAL = "personal"
    MEI = "mei"
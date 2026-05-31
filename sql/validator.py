"""
SQL Safety Validator
Blocks any non-SELECT SQL to prevent accidental or malicious data modification.
"""
import re
from typing import TypedDict


BLOCKED_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "replace", "merge", "grant", "revoke",
    "execute", "exec", "call", "do", "copy",
]

# Patterns that indicate SQL injection or dangerous constructs
DANGEROUS_PATTERNS = [
    r";\s*(drop|alter|create|delete|update|insert|truncate)",
    r"--\s*bypass",
    r"\/\*.*bypass.*\*\/",
    r"xp_cmdshell",
    r"information_schema\.(routines|user_privileges)",
]


class ValidationResult(TypedDict):
    is_safe: bool
    reason: str
    sql_type: str


class SQLValidator:
    def validate(self, sql: str) -> ValidationResult:
        if not sql or not sql.strip():
            return ValidationResult(is_safe=False, reason="Empty SQL", sql_type="unknown")

        sql_clean = sql.strip().lower()

        # Must start with SELECT
        if not sql_clean.startswith("select"):
            first_word = sql_clean.split()[0] if sql_clean.split() else ""
            return ValidationResult(
                is_safe=False,
                reason=f"Only SELECT statements are allowed. Got: {first_word.upper()}",
                sql_type=first_word,
            )

        # Check for blocked keywords
        tokens = re.split(r"[\s;,()]+", sql_clean)
        for token in tokens:
            if token in BLOCKED_KEYWORDS:
                return ValidationResult(
                    is_safe=False,
                    reason=f"Blocked keyword found: {token.upper()}",
                    sql_type="blocked",
                )

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, sql_clean, re.IGNORECASE):
                return ValidationResult(
                    is_safe=False,
                    reason=f"Dangerous SQL pattern detected",
                    sql_type="injection_attempt",
                )

        return ValidationResult(is_safe=True, reason="SQL is safe", sql_type="select")

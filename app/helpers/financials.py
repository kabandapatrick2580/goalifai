from decimal import Decimal, ROUND_DOWN
"""
    Helper functions for financial calculations.
    These functions can be used to ensure consistent handling of financial data.
"""

def quantize(amount):
    """Ensure decimals are to 2 decimal places."""
    return (Decimal(amount or 0)).quantize(Decimal('0.01'), rounding=ROUND_DOWN)


def ensure_profile_balances(profile):
    """Ensure financial profile has numeric balances."""
    if profile.deficit_balance is None:
        profile.deficit_balance = Decimal('0.00')
    if profile.savings_balance is None:
        profile.savings_balance = Decimal('0.00')
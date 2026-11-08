"""Research-only Matrix installation-core reference package."""

from .policy import (
    Decision,
    activate_installation,
    decide_activation,
    decide_referral,
    decide_revenue_allocation,
    request_installation_stop,
    validate_records,
    withdraw_participant,
)
from .store import ReferenceStore

__all__ = [
    "Decision",
    "ReferenceStore",
    "activate_installation",
    "decide_activation",
    "decide_referral",
    "decide_revenue_allocation",
    "request_installation_stop",
    "validate_records",
    "withdraw_participant",
]

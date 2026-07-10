# -*- coding: utf-8 -*-
"""
State transition table for SBC automation.

Declarative mapping: state_class → [(action_instance, expected_next_state_class)]

The machine runner uses this table to decide which action to take from each state.
For branching outcomes, the machine re-detects state after each action rather
than relying on a predicted next state.
"""
from src.sbc.states import (
    SBCHome, SetDetail, SquadBuilder, SubmitReady, SubmitDisabled,
    FSUWarning, RewardReady, ConfirmPopup
)
from src.sbc.actions import (
    CheckAvailableSBCs, EnterSBCSet, ClickStartChallenge, ClickFSUFill,
    ClickSubmit, DismissFSUWarning, ClaimReward, ClickConfirm
)

TRANSITIONS = {
    # ── SBC Home / Listing ─────────────────────────────────────────
    SBCHome: [
        (CheckAvailableSBCs(), SBCHome),        # Check what's available
        (EnterSBCSet(""), None),                # Enter specific SBC (set_name filled at runtime)
    ],

    # ── Set Detail / Challenge Overview ────────────────────────────
    SetDetail: [
        (ClickStartChallenge(), SquadBuilder),  # Click into squad builder
    ],

    # ── Squad Builder ──────────────────────────────────────────────
    SquadBuilder: [
        (ClickFSUFill(), SubmitReady),          # Auto-fill squad
    ],

    SubmitReady: [
        (ClickSubmit(), None),                  # Submit — outcome detected next cycle
    ],

    SubmitDisabled: [
        (ClickFSUFill(), SubmitReady),          # Try FSU fill again
    ],

    # ── Post-submit branching ──────────────────────────────────────
    FSUWarning: [
        (DismissFSUWarning(), RewardReady),     # Dismiss → claim reward
    ],

    RewardReady: [
        (ClaimReward(), SBCHome),               # Claim → back to listing
    ],

    # ── Misc ───────────────────────────────────────────────────────
    ConfirmPopup: [
        (ClickConfirm(), SBCHome),              # Confirm → back to listing
    ],
}


def get_transitions(state_cls):
    """Get transitions for a state class. Returns empty list if none."""
    return TRANSITIONS.get(state_cls, [])


def has_transitions(state_cls):
    """Check if a state has any registered transitions."""
    return state_cls in TRANSITIONS

"""Twilio calling logic, kept separate from the GUI.

Two code paths place a "call":

- ``_place_call_mock``  — dry-run, no network call, no Twilio SDK required.
- ``_place_call_live``  — real Twilio SDK call using a Standard API Key.

``place_call`` picks between them based on ``TwilioConfig.dry_run``, which is
True whenever required .env values are missing/invalid, or when
TWILIO_DRY_RUN is explicitly set. Once real credentials are filled into
.env, dry-run mode turns off automatically — no code change needed.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")

REQUIRED_ENV_VARS = [
    "TWILIO_ACCOUNT_SID",
    "TWILIO_API_KEY_SID",
    "TWILIO_API_KEY_SECRET",
    "TWILIO_FROM_NUMBER",
    "BDM_PHONE_NUMBER",
    "TWILIO_TWIML_URL",
]


class CallError(Exception):
    """Raised for invalid input or a failed call attempt. Safe to show to the user."""


@dataclass
class TwilioConfig:
    account_sid: Optional[str]
    api_key_sid: Optional[str]
    api_key_secret: Optional[str]
    from_number: Optional[str]
    bdm_phone_number: Optional[str]
    twiml_url: Optional[str]
    dry_run: bool
    missing_vars: List[str] = field(default_factory=list)


@dataclass
class CallResult:
    success: bool
    message: str
    call_sid: Optional[str] = None
    dry_run: bool = False


def load_config() -> TwilioConfig:
    """Read Twilio settings from the environment. Never raises on missing values."""
    values = {name: os.getenv(name) for name in REQUIRED_ENV_VARS}
    missing = [name for name, val in values.items() if not val]

    explicit_dry_run = os.getenv("TWILIO_DRY_RUN", "").strip().lower() in ("1", "true", "yes")
    forced_dry_run = bool(missing)

    return TwilioConfig(
        account_sid=values["TWILIO_ACCOUNT_SID"],
        api_key_sid=values["TWILIO_API_KEY_SID"],
        api_key_secret=values["TWILIO_API_KEY_SECRET"],
        from_number=values["TWILIO_FROM_NUMBER"],
        bdm_phone_number=values["BDM_PHONE_NUMBER"],
        twiml_url=values["TWILIO_TWIML_URL"],
        dry_run=forced_dry_run or explicit_dry_run,
        missing_vars=missing,
    )


def is_valid_e164(number: str) -> bool:
    return bool(E164_PATTERN.match(number.strip()))


def place_call(to_number: str, config: Optional[TwilioConfig] = None) -> CallResult:
    """Validate ``to_number`` and place a call (real or dry-run).

    Raises CallError on invalid input or a failed live call. Never raises on
    missing/invalid .env — that just forces dry-run mode.
    """
    if config is None:
        config = load_config()

    to_number = to_number.strip()
    if not is_valid_e164(to_number):
        raise CallError(f"'{to_number}' is not a valid E.164 phone number (e.g. +14155552671).")

    if config.dry_run:
        return _place_call_mock(to_number, config)
    return _place_call_live(to_number, config)


def _place_call_mock(to_number: str, config: TwilioConfig) -> CallResult:
    if config.missing_vars:
        reason = f"missing .env values: {', '.join(config.missing_vars)}"
    else:
        reason = "TWILIO_DRY_RUN is set"

    from_number = config.from_number or "(unset TWILIO_FROM_NUMBER)"
    bdm_number = config.bdm_phone_number or "(unset BDM_PHONE_NUMBER)"
    return CallResult(
        success=True,
        message=(
            f"[DRY RUN] Would call you at {bdm_number} from {from_number}, then bridge "
            f"you to {to_number} ({reason}). No real call was placed."
        ),
        call_sid="DRY-RUN-NO-SID",
        dry_run=True,
    )


def _place_call_live(to_number: str, config: TwilioConfig) -> CallResult:
    from twilio.base.exceptions import TwilioException
    from twilio.rest import Client

    if not config.bdm_phone_number or not is_valid_e164(config.bdm_phone_number):
        raise CallError(
            "BDM_PHONE_NUMBER is missing or invalid in .env. Set it to the BDM's own "
            "phone number in E.164 format (e.g. +14155552671) so calls can be bridged."
        )
    if not config.twiml_url:
        raise CallError(
            "TWILIO_TWIML_URL is not set in .env. Point it at your /connect endpoint "
            "(see twiml_server.py) so the BDM can be bridged to the prospect."
        )

    client = Client(config.api_key_sid, config.api_key_secret, config.account_sid)
    connect_url = f"{config.twiml_url.rstrip('/')}/connect?to={quote(to_number)}"

    try:
        # Call the BDM first. Once they pick up, the /connect TwiML dials the
        # prospect and bridges the two legs together so they can talk live.
        call = client.calls.create(
            to=config.bdm_phone_number,
            from_=config.from_number,
            url="https://handler.twilio.com/twiml/EHb5680885d8680da496af67d773b00d12",
            url=connect_url,
        )
    except TwilioException as exc:
        raise CallError(f"Twilio API error: {exc}") from exc
    except Exception as exc:
        raise CallError(f"Unexpected error placing call: {exc}") from exc

    return CallResult(
        success=True,
        message=f"Calling you now to connect to {to_number}. SID: {call.sid}",
        call_sid=call.sid,
        dry_run=False,
    )

"""Version-one cloud capture requests and immutable run identities."""

from datetime import datetime, timezone
import hashlib
import json
import re

STATUS = {"dataset_mode": "retrospective_demo", "historical_availability_verified": False,
          "approved_for_point_in_time_forecasting": False, "approved_for_predictor_use": False}


class ContractError(ValueError):
    """A safe error with no event or credential contents."""


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate(event):
    """Reject unknown fields (including secrets) before any external calls."""
    required = {"schema_version", "season", "idempotency_token"}
    if not isinstance(event, dict) or not required <= event.keys() or event.keys() - required - {"week"}:
        raise ContractError("Expected only schema_version, season, idempotency_token and optional week.")
    if type(event["schema_version"]) is not int or event["schema_version"] != 1:
        raise ContractError("Expected request schema_version 1.")
    if type(event["season"]) is not int or not 1869 <= event["season"] <= 9999:
        raise ContractError("Season must be an integer year between 1869 and 9999.")
    if "week" in event and (type(event["week"]) is not int or event["week"] < 0 or event["week"] > 99):
        raise ContractError("Week must be an integer between 0 and 99; omit for a full season.")
    token = event["idempotency_token"]
    if not isinstance(token, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,63}", token):
        raise ContractError("Token must contain 8–64 lowercase letters, digits or hyphens.")
    request = {"schema_version": 1, "season": event["season"], "week": event.get("week"),
               "endpoint": "cfbd/games", "season_type": "regular", "classification": "fbs"}
    return request, digest(token.encode()), digest(encode(request))


def receipt(state, token_hash=None, request_hash=None, **facts):
    return {"receipt_version": 1, "state": state, "token_sha256": token_hash,
            "request_sha256": request_hash, **STATUS, **facts}

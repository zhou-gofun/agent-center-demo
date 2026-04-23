"""Small helpers for consistent HTTP responses."""
from typing import Any, Dict, Optional, Tuple


def success_response(data: Any, status_code: int = 200) -> Tuple[Dict[str, Any], int]:
    return {"success": True, "data": data}, status_code


def error_response(
    message: str,
    status_code: int = 400,
    *,
    code: Optional[str] = None,
    details: Any = None,
) -> Tuple[Dict[str, Any], int]:
    payload: Dict[str, Any] = {"success": False, "error": message}
    if code:
        payload["code"] = code
    if details is not None:
        payload["details"] = details
    return payload, status_code

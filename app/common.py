from __future__ import annotations
from typing import Any, Dict
from fastapi.responses import JSONResponse

SUCCESS_RESPONSE = {"success": True}

def success(**kwargs: Any) -> Dict[str, Any]:
    payload = dict(SUCCESS_RESPONSE)
    payload.update(kwargs)
    return payload

def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "message": message})

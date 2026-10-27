import base64
import binascii
import time

from fastapi import Header, HTTPException


LEGACY_SECRET = "WORKSHOP_SECRET_2026"


def legacy_identity(authorization: str = Header(default="")) -> dict[str, str]:
    try:
        token = authorization.replace("Bearer ", "")
        decoded = base64.b64decode(token).decode("utf-8")
        parts = decoded.split("|")
        if len(parts) != 4 or parts[3] != LEGACY_SECRET or int(parts[2]) < int(time.time()):
            raise ValueError("invalid token")
        return {"username": parts[0], "role": parts[1]}
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error


def ensure_owner_access(owner: str, identity: dict[str, str]) -> str:
    if owner != identity["username"]:
        raise HTTPException(status_code=403, detail="Owner access denied")
    return owner
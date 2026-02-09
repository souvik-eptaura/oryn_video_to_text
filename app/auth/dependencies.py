from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.firebase import verify_firebase_jwt


bearer = HTTPBearer(auto_error=False)


def require_firebase_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        return verify_firebase_jwt(creds.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

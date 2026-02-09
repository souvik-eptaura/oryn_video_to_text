from __future__ import annotations

from typing import Any, Dict

from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import get_settings


def verify_firebase_jwt(token: str) -> Dict[str, Any]:
    settings = get_settings()
    request = requests.Request()

    claims = id_token.verify_firebase_token(token, request, audience=settings.FIREBASE_PROJECT_ID)

    iss = f"https://securetoken.google.com/{settings.FIREBASE_PROJECT_ID}"
    if claims.get("iss") != iss:
        raise ValueError("Invalid issuer")
    if claims.get("aud") != settings.FIREBASE_PROJECT_ID:
        raise ValueError("Invalid audience")
    if settings.REQUIRE_INTERNAL_CLAIM and claims.get("internal") is not True:
        raise ValueError("Missing internal claim")

    return claims

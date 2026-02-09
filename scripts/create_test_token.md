# Firebase JWT Notes

Generate tokens from your Firebase backend service account. Do not store secrets here.

Common approach:
- Use Google service account credentials in your backend
- Mint a custom token for internal service-to-service calls
- Exchange it for an ID token, then use it as the `Authorization: Bearer` token

This file is documentation only.

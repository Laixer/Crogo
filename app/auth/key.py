from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class KeyBearer(HTTPBearer):
    def __init__(self, key: str):
        super().__init__()
        self.key = key

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            if credentials.credentials != self.security_key:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid credentials",
                )
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
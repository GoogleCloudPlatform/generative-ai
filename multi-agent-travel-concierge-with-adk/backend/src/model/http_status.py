from fastapi import HTTPException

class ResourceAlreadyExists(HTTPException):
    def __init__(self, detail="Resource already exists"):
        super().__init__(status_code=400, detail=detail)

class BadRequest(HTTPException):
    def __init__(self, detail="Resource already exists"):
        super().__init__(status_code=400, detail=detail)
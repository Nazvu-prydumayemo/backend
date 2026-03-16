from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import api_router

app = FastAPI(title="NP-API")

VALIDATION_ERROR_CODE = "REQUEST_VALIDATION_ERROR"
VALIDATION_ERROR_DETAIL = "Request validation failed"


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": VALIDATION_ERROR_CODE,
            "detail": VALIDATION_ERROR_DETAIL,
            "errors": exc.errors(),
        },
    )


app.include_router(api_router, prefix="/api/v1")

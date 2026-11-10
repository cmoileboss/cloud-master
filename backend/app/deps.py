"""Dépendances injectées dans les routes : session de base de données, service LLM, stockage."""

from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.llm import LLMService
from app.storage import BlobStorage


def get_db(request: Request):
    with Session(request.app.state.engine) as db:
        yield db


def get_llm(request: Request) -> LLMService:
    return request.app.state.llm


def get_blob_storage(request: Request) -> BlobStorage:
    return request.app.state.blob_storage


DB = Annotated[Session, Depends(get_db)]
LLM = Annotated[LLMService, Depends(get_llm)]
BlobStorage = Annotated[BlobStorage, Depends(get_blob_storage)]
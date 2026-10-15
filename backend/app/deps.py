"""Dépendances injectées dans les routes : session de base de données, service LLM, stockage."""

from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.llm import LLMService
from app.storage import LocalStorage


def get_db(request: Request):
    with Session(request.app.state.engine) as db:
        yield db


def get_llm(request: Request) -> LLMService:
    return request.app.state.llm


def get_storage(request: Request) -> LocalStorage:
    return request.app.state.storage


DB = Annotated[Session, Depends(get_db)]
LLM = Annotated[LLMService, Depends(get_llm)]
Storage = Annotated[LocalStorage, Depends(get_storage)]

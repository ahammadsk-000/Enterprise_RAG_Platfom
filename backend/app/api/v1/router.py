"""Aggregate router for API v1.

Each domain registers its router here as it is implemented. Phase 1 ships health;
subsequent phases add auth, users, workspaces, documents, search, chat, agents, etc.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.ws import chat as ws_chat
from app.api.v1.routes import (
    admin,
    agents,
    assist,
    auth,
    chat,
    documents,
    evaluation,
    graph,
    health,
    oauth,
    rag,
    search,
    users,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["auth", "sso"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(assist.router, prefix="/assist", tags=["assist"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph-rag"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(ws_chat.router, prefix="/ws", tags=["chat", "ws"])

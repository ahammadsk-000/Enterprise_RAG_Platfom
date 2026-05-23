"""Shared FastAPI dependencies: DB session, auth, tenant scoping, RBAC.

Route modules import their dependencies from here so there is a single, stable
surface. Providers (vector/graph/LLM) are added to this module in later phases.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.db.session import get_db
from app.domains.identity.permissions import Permission
from app.domains.identity.repositories.membership_repository import SqlAlchemyMembershipRepository
from app.domains.identity.repositories.oauth_account_repository import SqlAlchemyOAuthAccountRepository
from app.domains.identity.repositories.organization_repository import SqlAlchemyOrganizationRepository
from app.domains.identity.repositories.role_repository import SqlAlchemyRoleRepository
from app.domains.identity.repositories.user_repository import SqlAlchemyUserRepository
from app.domains.identity.schemas.auth import Principal
from app.domains.identity.services.auth_service import AuthService
from app.domains.identity.services.rbac import ensure_permission
from app.domains.chunking.repositories.chunk_repository import SqlAlchemyChunkRepository
from app.domains.documents.repositories.document_repository import SqlAlchemyDocumentRepository
from app.domains.documents.repositories.ingestion_job_repository import SqlAlchemyIngestionJobRepository
from app.domains.documents.services.document_service import DocumentService
from app.domains.ingestion.task_bus import CeleryTaskBus, TaskBus
from app.domains.chat.repositories.conversation_repository import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
)
from app.domains.chat.services.chat_service import ChatService
from app.domains.rag.services.rag_service import RagService
from app.domains.retrieval.repositories.retrieval_log_repository import SqlAlchemyRetrievalLogRepository
from app.domains.workspaces.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from app.domains.workspaces.services.workspace_service import WorkspaceService
from app.domains.graphrag.extractors.factory import get_entity_extractor
from app.domains.graphrag.services.graph_service import GraphRetrievalService
from app.integrations.graphstore.factory import get_graph_store
from app.domains.agents.graph.orchestrator import ResearchAgentGraph
from app.domains.agents.repositories.agent_repository import SqlAlchemyAgentRunRepository
from app.domains.agents.services.agent_service import AgentService
from app.domains.evaluation.repositories.eval_repository import SqlAlchemyEvalRepository
from app.domains.evaluation.services.eval_service import EvalService
from app.domains.retrieval.retrievers.bm25 import BM25Retriever
from app.domains.retrieval.retrievers.dense import DenseRetriever
from app.domains.retrieval.services.retrieval_service import RetrievalService
from app.integrations.embeddings.factory import get_embedding_provider
from app.integrations.llm.factory import get_llm_provider
from app.integrations.reranker.factory import get_reranker
from app.integrations.storage.factory import get_object_storage
from app.integrations.vectorstore.factory import get_vector_store

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(
        session=session,
        users=SqlAlchemyUserRepository(session),
        organizations=SqlAlchemyOrganizationRepository(session),
        memberships=SqlAlchemyMembershipRepository(session),
        roles=SqlAlchemyRoleRepository(session),
        oauth_accounts=SqlAlchemyOAuthAccountRepository(session),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_principal(
    service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise AuthError("Missing bearer token.")
    return await service.principal_from_access_token(credentials.credentials)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def require_permission(
    permission: Permission,
) -> Callable[[Principal], Coroutine[Any, Any, Principal]]:
    """Return a dependency that enforces `permission` on the current principal."""

    async def _dependency(principal: CurrentPrincipal) -> Principal:
        ensure_permission(principal, permission)
        return principal

    return _dependency


# ── Documents / ingestion ────────────────────────────────────────────────────
def get_task_bus() -> TaskBus:
    """Default task bus (Celery). Overridden in tests with a NullTaskBus."""
    return CeleryTaskBus()


TaskBusDep = Annotated[TaskBus, Depends(get_task_bus)]


def get_document_service(session: DbSession, task_bus: TaskBusDep) -> DocumentService:
    return DocumentService(
        session=session,
        documents=SqlAlchemyDocumentRepository(session),
        jobs=SqlAlchemyIngestionJobRepository(session),
        chunks=SqlAlchemyChunkRepository(session),
        storage=get_object_storage(),
        vector_store=get_vector_store(),
        task_bus=task_bus,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


# ── Retrieval / RAG ──────────────────────────────────────────────────────────
def _build_retrieval_service(session: AsyncSession) -> RetrievalService:
    chunks = SqlAlchemyChunkRepository(session)
    return RetrievalService(
        dense=DenseRetriever(get_embedding_provider(), get_vector_store(), chunks),
        bm25=BM25Retriever(chunks),
        reranker=get_reranker(),
        logs=SqlAlchemyRetrievalLogRepository(session),
    )


def get_retrieval_service(session: DbSession) -> RetrievalService:
    return _build_retrieval_service(session)


def get_rag_service(session: DbSession) -> RagService:
    return RagService(retrieval=_build_retrieval_service(session), llm=get_llm_provider())


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
RagServiceDep = Annotated[RagService, Depends(get_rag_service)]


# ── Workspaces / Chat ────────────────────────────────────────────────────────
def get_workspace_service(session: DbSession) -> WorkspaceService:
    return WorkspaceService(session, SqlAlchemyWorkspaceRepository(session))


def build_chat_service(session: AsyncSession) -> ChatService:
    return ChatService(
        session=session,
        conversations=SqlAlchemyConversationRepository(session),
        messages=SqlAlchemyMessageRepository(session),
        retrieval=_build_retrieval_service(session),
        llm=get_llm_provider(),
    )


def get_chat_service(session: DbSession) -> ChatService:
    return build_chat_service(session)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


# ── Graph RAG ────────────────────────────────────────────────────────────────
def get_graph_retrieval_service() -> GraphRetrievalService:
    return GraphRetrievalService(get_entity_extractor(), get_graph_store())


GraphRetrievalDep = Annotated[GraphRetrievalService, Depends(get_graph_retrieval_service)]


# ── Agents ───────────────────────────────────────────────────────────────────
def get_agent_service(session: DbSession) -> AgentService:
    graph = ResearchAgentGraph(_build_retrieval_service(session), get_llm_provider())
    return AgentService(session, graph, SqlAlchemyAgentRunRepository(session))


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


# ── Evaluation ───────────────────────────────────────────────────────────────
def get_eval_service(session: DbSession) -> EvalService:
    return EvalService(session, SqlAlchemyEvalRepository(session), get_llm_provider())


EvalServiceDep = Annotated[EvalService, Depends(get_eval_service)]

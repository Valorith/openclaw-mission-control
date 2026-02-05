from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api import agents as agents_api
from app.api import approvals as approvals_api
from app.api import board_memory as board_memory_api
from app.api import board_onboarding as onboarding_api
from app.api import tasks as tasks_api
from app.api.deps import ActorContext, get_board_or_404, get_task_or_404
from app.core.agent_auth import AgentAuthContext, get_agent_auth_context
from app.db.session import get_session
from app.models.boards import Board
from app.schemas.approvals import ApprovalCreate, ApprovalRead
from app.schemas.board_memory import BoardMemoryCreate, BoardMemoryRead
from app.schemas.board_onboarding import BoardOnboardingRead
from app.schemas.boards import BoardRead
from app.schemas.tasks import TaskCommentCreate, TaskCommentRead, TaskRead, TaskUpdate
from app.schemas.agents import AgentCreate, AgentHeartbeatCreate, AgentRead

router = APIRouter(prefix="/agent", tags=["agent"])


def _actor(agent_ctx: AgentAuthContext) -> ActorContext:
    return ActorContext(actor_type="agent", agent=agent_ctx.agent)


def _guard_board_access(agent_ctx: AgentAuthContext, board: Board) -> None:
    if agent_ctx.agent.board_id and agent_ctx.agent.board_id != board.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


@router.get("/boards", response_model=list[BoardRead])
def list_boards(
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> list[Board]:
    if agent_ctx.agent.board_id:
        board = session.get(Board, agent_ctx.agent.board_id)
        return [board] if board else []
    return list(session.exec(select(Board)))


@router.get("/boards/{board_id}", response_model=BoardRead)
def get_board(
    board: Board = Depends(get_board_or_404),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> Board:
    _guard_board_access(agent_ctx, board)
    return board


@router.get("/boards/{board_id}/tasks", response_model=list[TaskRead])
def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    assigned_agent_id: UUID | None = None,
    unassigned: bool | None = None,
    limit: int | None = Query(default=None, ge=1, le=200),
    board: Board = Depends(get_board_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> list[TaskRead]:
    _guard_board_access(agent_ctx, board)
    return tasks_api.list_tasks(
        status_filter=status_filter,
        assigned_agent_id=assigned_agent_id,
        unassigned=unassigned,
        limit=limit,
        board=board,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.patch("/boards/{board_id}/tasks/{task_id}", response_model=TaskRead)
def update_task(
    payload: TaskUpdate,
    task=Depends(get_task_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> TaskRead:
    if agent_ctx.agent.board_id and task.board_id and agent_ctx.agent.board_id != task.board_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return tasks_api.update_task(
        payload=payload,
        task=task,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.get("/boards/{board_id}/tasks/{task_id}/comments", response_model=list[TaskCommentRead])
def list_task_comments(
    task=Depends(get_task_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> list[TaskCommentRead]:
    if agent_ctx.agent.board_id and task.board_id and agent_ctx.agent.board_id != task.board_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return tasks_api.list_task_comments(
        task=task,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.post("/boards/{board_id}/tasks/{task_id}/comments", response_model=TaskCommentRead)
def create_task_comment(
    payload: TaskCommentCreate,
    task=Depends(get_task_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> TaskCommentRead:
    if agent_ctx.agent.board_id and task.board_id and agent_ctx.agent.board_id != task.board_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return tasks_api.create_task_comment(
        payload=payload,
        task=task,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.get("/boards/{board_id}/memory", response_model=list[BoardMemoryRead])
def list_board_memory(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    board=Depends(get_board_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> list[BoardMemoryRead]:
    _guard_board_access(agent_ctx, board)
    return board_memory_api.list_board_memory(
        limit=limit,
        offset=offset,
        board=board,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.post("/boards/{board_id}/memory", response_model=BoardMemoryRead)
def create_board_memory(
    payload: BoardMemoryCreate,
    board=Depends(get_board_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> BoardMemoryRead:
    _guard_board_access(agent_ctx, board)
    return board_memory_api.create_board_memory(
        payload=payload,
        board=board,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.get("/boards/{board_id}/approvals", response_model=list[ApprovalRead])
def list_approvals(
    status_filter: str | None = Query(default=None, alias="status"),
    board=Depends(get_board_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> list[ApprovalRead]:
    _guard_board_access(agent_ctx, board)
    return approvals_api.list_approvals(
        status_filter=status_filter,
        board=board,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.post("/boards/{board_id}/approvals", response_model=ApprovalRead)
def create_approval(
    payload: ApprovalCreate,
    board=Depends(get_board_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> ApprovalRead:
    _guard_board_access(agent_ctx, board)
    return approvals_api.create_approval(
        payload=payload,
        board=board,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.post("/boards/{board_id}/onboarding", response_model=BoardOnboardingRead)
def update_onboarding(
    payload: dict[str, object],
    board: Board = Depends(get_board_or_404),
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> BoardOnboardingRead:
    _guard_board_access(agent_ctx, board)
    return onboarding_api.agent_onboarding_update(
        payload=payload,
        board=board,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.post("/agents", response_model=AgentRead)
def create_agent(
    payload: AgentCreate,
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> AgentRead:
    if not agent_ctx.agent.is_board_lead:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if not agent_ctx.agent.board_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    payload = AgentCreate(**{**payload.model_dump(), "board_id": agent_ctx.agent.board_id})
    return agents_api.create_agent(
        payload=payload,
        session=session,
        actor=_actor(agent_ctx),
    )


@router.post("/heartbeat", response_model=AgentRead)
async def agent_heartbeat(
    payload: AgentHeartbeatCreate,
    session: Session = Depends(get_session),
    agent_ctx: AgentAuthContext = Depends(get_agent_auth_context),
) -> AgentRead:
    if agent_ctx.agent.name != payload.name:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return await agents_api.heartbeat_or_create_agent(  # type: ignore[attr-defined]
        payload=payload,
        session=session,
        actor=_actor(agent_ctx),
    )

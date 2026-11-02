"""Cash flow events API — CRUD + runway projection."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.engines.cashflow import CashflowEngine
from app.models.cashflow_event import CashflowEvent
from app.schemas.cashflow import (
    CashflowEventCreate,
    CashflowEventResponse,
    CashflowEventUpdate,
    RunwayResponse,
)

router = APIRouter(prefix="/api/cashflow", tags=["cashflow"])


@router.get("/events", response_model=list[CashflowEventResponse])
async def list_events(
    status: str | None = None,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(CashflowEvent).order_by(CashflowEvent.date)
    if status:
        q = q.where(CashflowEvent.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/events", response_model=CashflowEventResponse)
async def create_event(
    data: CashflowEventCreate,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = CashflowEvent(
        name=data.name,
        event_type=data.event_type,
        amount_cents=int(round(data.amount * 100)),
        date=data.date,
        is_recurring=data.is_recurring,
        recurrence=data.recurrence,
        end_date=data.end_date,
        probability=data.probability,
        status=data.status,
        category=data.category,
        linked_account_id=data.linked_account_id,
        notes=data.notes,
        custom_data=(
            {"end_at": anchor}
            if (anchor := data.end_at or ("retirement" if data.ends_at_retirement else None))
            else None
        ),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.put("/events/{event_id}", response_model=CashflowEventResponse)
async def update_event(
    event_id: UUID,
    data: CashflowEventUpdate,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CashflowEvent).where(CashflowEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = data.model_dump(exclude_unset=True)
    if "amount" in update_data:
        update_data["amount_cents"] = int(round(update_data.pop("amount") * 100))
    if "end_at" in update_data or "ends_at_retirement" in update_data:
        flag = update_data.pop("ends_at_retirement", None)
        anchor = update_data.pop("end_at") if "end_at" in data.model_fields_set else (
            "retirement" if flag else None
        )
        cd = dict(event.custom_data or {})
        if anchor:
            cd["end_at"] = anchor
        else:
            cd.pop("end_at", None)
        event.custom_data = cd or None  # reassigned dict → SQLAlchemy sees the JSONB change

    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: UUID,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CashflowEvent).where(CashflowEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.delete(event)
    await db.commit()
    return {"detail": "deleted"}


@router.get("/runway", response_model=RunwayResponse)
async def get_runway(
    months: int = 24,
    income_override: float | None = Query(
        None, description="Override monthly income baseline (dollars). If omitted, uses trailing 3-month average."
    ),
    burn_override: float | None = Query(
        None, description="Override monthly expense baseline (dollars). If omitted, uses trailing 3-month average."
    ),
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    engine = CashflowEngine(db)
    return await engine.project_runway(
        months=months,
        income_override=income_override,
        burn_override=burn_override,
    )


@router.get("/phases")
async def get_cash_flow_phases(
    spending_override: int | None = None,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The active plan's monthly cash flow grouped into phases (today → life
    expectancy): income, expenses and net per month in each stretch, with line
    items, plus one-time flows. Same engine and real dollars as the Retirement page."""
    from app.engines.cashflow_phases import cash_flow_phases
    from app.engines.fire_projections import FireProjectionsEngine

    engine = FireProjectionsEngine(db)
    config = await engine.get_effective_config()
    end_age = config.life_expectancy
    proj = await engine.project_wealth_pools(
        end_age=end_age, bridge_months=12 * 100, spending_override_cents=spending_override,
        capture_lines=True,
    )
    retire = engine._get_retirement_date(config)
    out = cash_flow_phases(proj.points)
    out["retirement_month"] = retire.strftime("%Y-%m") if retire else None
    last = proj.points[-1] if proj.points else None
    out["runs_out_age"] = round(last.age, 1) if last and last.age < end_age - 1 else None
    return out

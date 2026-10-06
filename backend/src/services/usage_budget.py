from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from src.config import Settings
from src.database import Database

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    pass


class LLMCallLimitExceededError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BudgetIdentity:
    session_id: str = "unknown"
    client_ip: str = "unknown"
    conversation_id: str = ""
    trace_id: str = ""


@dataclass(frozen=True, slots=True)
class CostEstimate:
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


def identity_from_metadata(metadata: dict[str, Any] | None) -> BudgetIdentity:
    meta = metadata or {}
    return BudgetIdentity(
        session_id=str(meta.get("anon_session_id") or "unknown"),
        client_ip=str(meta.get("client_ip") or "unknown"),
        conversation_id=str(meta.get("conversation_id") or ""),
        trace_id=str(meta.get("trace_id") or ""),
    )


def _message_chars(value: Any) -> int:
    if isinstance(value, BaseMessage):
        return len(str(value.content or ""))
    if isinstance(value, str):
        return len(value)
    if isinstance(value, list):
        return sum(_message_chars(item) for item in value)
    if isinstance(value, tuple):
        return sum(_message_chars(item) for item in value)
    if isinstance(value, dict):
        return sum(len(str(key)) + _message_chars(item) for key, item in value.items())
    return len(str(value or ""))


def _extract_usage_tokens(response: Any) -> tuple[int | None, int | None]:
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
        return (
            int(input_tokens) if input_tokens is not None else None,
            int(output_tokens) if output_tokens is not None else None,
        )
    response_metadata = getattr(response, "response_metadata", None)
    token_usage = response_metadata.get("token_usage") if isinstance(response_metadata, dict) else None
    if isinstance(token_usage, dict):
        input_tokens = token_usage.get("prompt_tokens")
        output_tokens = token_usage.get("completion_tokens")
        return (
            int(input_tokens) if input_tokens is not None else None,
            int(output_tokens) if output_tokens is not None else None,
        )
    return None, None


def _budget_lock_key(usage_date: str) -> int:
    digest = hashlib.blake2b(f"llm-budget:{usage_date}".encode("ascii"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


def _is_ambiguous_provider_error(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    class_name = type(exc).__name__.lower()
    return "timeout" in class_name or "connection" in class_name


class UsageBudgetService:
    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    def estimate(self, *, model: str, payload: Any) -> CostEstimate:
        input_tokens = max(1, math.ceil(_message_chars(payload) / 4))
        output_tokens = self.settings.llm_estimated_output_tokens_per_call
        cost = self._cost(input_tokens=input_tokens, output_tokens=output_tokens)
        return CostEstimate(model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost)

    def reserve(self, *, identity: BudgetIdentity, estimate: CostEstimate, call_purpose: str) -> str:
        if not self.settings.llm_daily_budget_enabled:
            return ""
        now = datetime.now(UTC)
        usage_date = now.date().isoformat()
        reservation_id = "llm_budget_" + secrets.token_hex(16)
        with self.database.transaction(immediate=True) as connection:
            if connection.dialect == "postgres":
                connection.execute("SELECT pg_advisory_xact_lock(?)", (_budget_lock_key(usage_date),)).fetchone()
            global_used = self._sum_cost(connection, usage_date=usage_date)
            session_used = self._sum_cost(connection, usage_date=usage_date, session_id=identity.session_id)
            if global_used + estimate.cost_usd > Decimal(str(self.settings.llm_daily_max_cost_usd)):
                raise BudgetExceededError("GLOBAL_LLM_BUDGET_EXCEEDED")
            if session_used + estimate.cost_usd > Decimal(str(self.settings.llm_session_max_cost_usd_per_day)):
                raise BudgetExceededError("SESSION_LLM_BUDGET_EXCEEDED")
            connection.execute(
                "INSERT INTO llm_budget_ledger("
                "id,usage_date,session_id,client_ip,conversation_id,model,estimated_cost_usd,"
                "actual_cost_usd,estimated_input_tokens,estimated_output_tokens,actual_input_tokens,"
                "actual_output_tokens,status,created_at,finalized_at"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    reservation_id,
                    usage_date,
                    identity.session_id,
                    identity.client_ip,
                    identity.conversation_id,
                    estimate.model,
                    float(estimate.cost_usd),
                    None,
                    estimate.input_tokens,
                    estimate.output_tokens,
                    None,
                    None,
                    "reserved",
                    now.isoformat(),
                    None,
                ),
            )
        logger.info(
            "llm_budget_reserved trace_id=%s reservation_id=%s purpose=%s model=%s estimated_tokens=%s/%s estimated_cost_usd=%s",
            identity.trace_id,
            reservation_id,
            call_purpose,
            estimate.model,
            estimate.input_tokens,
            estimate.output_tokens,
            estimate.cost_usd,
        )
        return reservation_id

    def finalize(
        self,
        *,
        reservation_id: str,
        response: Any,
        fallback_estimate: CostEstimate,
        identity: BudgetIdentity,
        call_purpose: str,
    ) -> None:
        if not reservation_id:
            return
        input_tokens, output_tokens = _extract_usage_tokens(response)
        input_tokens = input_tokens if input_tokens is not None else fallback_estimate.input_tokens
        output_tokens = output_tokens if output_tokens is not None else fallback_estimate.output_tokens
        actual_cost = self._cost(input_tokens=input_tokens, output_tokens=output_tokens)
        now = datetime.now(UTC).isoformat()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE llm_budget_ledger SET actual_cost_usd=?,actual_input_tokens=?,"
                "actual_output_tokens=?,status=?,finalized_at=? WHERE id=?",
                (float(actual_cost), input_tokens, output_tokens, "finalized", now, reservation_id),
            )
        logger.info(
            "llm_budget_finalized trace_id=%s reservation_id=%s purpose=%s model=%s actual_tokens=%s/%s actual_cost_usd=%s",
            identity.trace_id,
            reservation_id,
            call_purpose,
            fallback_estimate.model,
            input_tokens,
            output_tokens,
            actual_cost,
        )

    def release(self, *, reservation_id: str, identity: BudgetIdentity, call_purpose: str) -> None:
        if not reservation_id:
            return
        now = datetime.now(UTC).isoformat()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE llm_budget_ledger SET actual_cost_usd=?,status=?,finalized_at=? WHERE id=?",
                (0.0, "failed", now, reservation_id),
            )
        logger.info(
            "llm_budget_released trace_id=%s reservation_id=%s purpose=%s",
            identity.trace_id,
            reservation_id,
            call_purpose,
        )

    def mark_unknown(self, *, reservation_id: str, identity: BudgetIdentity, call_purpose: str) -> None:
        if not reservation_id:
            return
        now = datetime.now(UTC).isoformat()
        with self.database.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE llm_budget_ledger SET status=?,finalized_at=? WHERE id=?",
                ("unknown", now, reservation_id),
            )
        logger.warning(
            "llm_budget_unknown trace_id=%s reservation_id=%s purpose=%s",
            identity.trace_id,
            reservation_id,
            call_purpose,
        )

    def _cost(self, *, input_tokens: int, output_tokens: int) -> Decimal:
        input_price = Decimal(str(self.settings.llm_estimated_input_token_price_per_1m))
        output_price = Decimal(str(self.settings.llm_estimated_output_token_price_per_1m))
        token_unit = Decimal(1_000_000)
        return Decimal(input_tokens) / token_unit * input_price + Decimal(output_tokens) / token_unit * output_price

    @staticmethod
    def _sum_cost(connection, *, usage_date: str, session_id: str | None = None) -> Decimal:
        sql = (
            "SELECT COALESCE(SUM(COALESCE(actual_cost_usd,estimated_cost_usd)),0) total "
            "FROM llm_budget_ledger WHERE usage_date=? AND status IN ('reserved','finalized','unknown')"
        )
        params: list[Any] = [usage_date]
        if session_id is not None:
            sql += " AND session_id=?"
            params.append(session_id)
        row = connection.execute(sql, tuple(params)).fetchone()
        return Decimal(str(row["total"] if row else 0))


async def invoke_with_budget(
    llm: Any,
    payload: Any,
    *,
    model: str,
    metadata: dict[str, Any] | None,
    budget: UsageBudgetService,
    call_purpose: str = "chat",
    config: RunnableConfig | None = None,
):
    metadata = metadata if metadata is not None else {}
    call_count = int(metadata.get("llm_call_count") or 0)
    if call_count >= budget.settings.llm_max_calls_per_turn:
        raise LLMCallLimitExceededError("LLM_CALL_LIMIT_EXCEEDED")
    metadata["llm_call_count"] = call_count + 1

    identity = identity_from_metadata(metadata)
    bound_options = getattr(llm, "kwargs", None)
    estimate_payload = {"payload": payload, "bound_options": bound_options or {}}
    estimate = budget.estimate(model=model, payload=estimate_payload)
    reservation_id = budget.reserve(identity=identity, estimate=estimate, call_purpose=call_purpose)
    try:
        response = await llm.ainvoke(payload, config=config)
    except Exception as exc:
        if _is_ambiguous_provider_error(exc):
            budget.mark_unknown(reservation_id=reservation_id, identity=identity, call_purpose=call_purpose)
        else:
            budget.release(reservation_id=reservation_id, identity=identity, call_purpose=call_purpose)
        raise
    budget.finalize(
        reservation_id=reservation_id,
        response=response,
        fallback_estimate=estimate,
        identity=identity,
        call_purpose=call_purpose,
    )
    return response

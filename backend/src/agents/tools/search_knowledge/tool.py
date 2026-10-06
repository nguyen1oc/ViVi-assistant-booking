import json

from langchain_core.tools import tool
from src.dependencies import knowledge_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("KnowledgeService.search")
def search_knowledge(
    query: str,
    model_code: str = "",
    topics: list[str] | None = None,
    market: str = "VN",
    trim: str = "",
    model_year: str = "",
) -> str:
    """Search one evidence scope in the provenance-aware post-booking knowledge base.

    Use this tool when a response needs factual vehicle, feature, charging, range,
    battery, ADAS, warranty, after-sales, policy, availability-boundary, or other
    domain-dependent VinFast knowledge.

    Args:
        query: One focused factual question for exactly one evidence scope. Ask for
            the information needed, not the user's entire message.
        model_code: Exact vehicle model when the requested fact is model-specific
            and the model is known, for example ``VF 6``. Leave unset when unknown;
            never guess a model.
        topics: Optional related topic filters for this same evidence scope. Combine
            related topics only when model, trim, model year, market, and policy
            scope are the same.
        market: Market scope. Defaults to Vietnam unless another market is explicitly
            established. Do not reuse evidence across markets.
        trim: Exact vehicle trim when known and relevant. Leave unset when unknown;
            never infer a trim.
        model_year: Exact four-digit model year when known and relevant. Leave unset
            when unknown; do not assume the current model year.

    Returns:
        JSON containing scoped facts, citations, review status, and live-data
        boundaries.

    Scope and parameter rules:
        - Treat model, trim, model year, market, policy scope, and returned revision
          as evidence boundaries.
        - For related topics within one scope, prefer one call with multiple
          ``topics``.
        - For comparisons or questions spanning different models, trims, years,
          markets, or unrelated policies, make one distinct call per evidence scope.
        - Use at most two distinct ``search_knowledge`` calls in one assistant turn;
          if more scopes exist, prioritize the scopes most relevant to the current
          question.
        - Never use a fact returned for one scope as evidence for another scope.
        - Model/trim-specific claims require returned evidence covering that exact
          model/trim scope.

    Result interpretation:
        - Never invent specifications, trim equipment, range, charging performance,
          prices, warranty/policy, availability, or showroom details.
        - Respect the scope, revision, citations, and status returned with each fact.
        - ``review_warning`` means the evidence is review-pending; do not present it
          as fully verified.
        - ``live_data_boundaries`` means the request belongs to an appropriate live
          service rather than this knowledge base.
        - An empty ``facts`` array, or otherwise inadequate evidence, means there is
          no verified answer for that scope. Do not guess. Ask for a missing scope
          only when it can resolve the question, otherwise recommend verification
          through an official VinFast source or the showroom.
        - Profile or booking signals may determine relevance, but they are not
          factual evidence for vehicle or policy claims.
    """
    return json.dumps(
        knowledge_service.search(
            query,
            model_code=model_code,
            topics=topics,
            market=market,
            trim=trim,
            model_year=model_year,
        ),
        ensure_ascii=False,
    )

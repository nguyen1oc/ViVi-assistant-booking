from src.agents.tools.search_knowledge.tool import search_knowledge


def test_search_knowledge_returns_query_context():
    """Smoke test for the knowledge tool used by the advise skill."""
    query = "VF6 Plus"

    result = search_knowledge.invoke({"query": query})

    assert query in result

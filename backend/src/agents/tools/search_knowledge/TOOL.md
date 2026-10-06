# Search Knowledge Tool

The runtime Python tool schema and docstring are authoritative. This file is a
maintainer reference and must stay aligned with `tool.py`.

## Arguments

- `query` (string): one focused question for one evidence scope.
- `model_code` (string): exact vehicle model, for example `VF 8`.
- `topics` (string array): related topics inside that same evidence scope.
- `market` (string): market scope; defaults to `VN`.
- `trim` and `model_year` (string): provide only when the user specifies them.

For related topics about one model, use one call with multiple `topics`. For a
comparison or scopes differing by model, trim, year, market, or unrelated
policy, use one call per evidence scope. Do not use facts from one scope as
evidence for another. An empty `facts` array means no verified answer exists in
this knowledge base.

## Example

```python
search_knowledge.invoke({
    "query": "Battery warranty for VF 8 in Vietnam",
    "model_code": "VF 8",
    "topics": ["battery", "warranty"],
    "market": "VN",
})
```

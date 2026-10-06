# Advise Skill: VinFast Electric Vehicle Consultation & Inquiries

This skill details how to guide, consult, and answer customer queries about VinFast electric vehicle models (VF3, VF5, VF6, VF7, VF8, VF9, etc.), pricing, battery specifications, and features using the `search_knowledge` tool.

---

## 🔍 1. Knowledge Base Retrieval (`search_knowledge`)

The `search_knowledge` tool is the primary source of truth for all vehicle specifications, ranges, prices, showroom locations, and general guidelines.

### Usage Guidelines:
- **Invoke on demand**: When a user asks about model specs (e.g., "VF8 battery capacity", "VF3 price", "VF7 range"), always call `search_knowledge` with the appropriate query keywords.
- **Synthesize answers**: Do not dump raw tool outputs to the user. Extract the relevant numbers, details, and format them nicely in Vietnamese.
- **Call-to-action**: After providing the requested information, always encourage the user to schedule a test drive to experience the vehicle in person.

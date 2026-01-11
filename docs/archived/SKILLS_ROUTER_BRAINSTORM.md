# Routing Skill Features - Brainstorm

Features for a SKILL.md that acts as a hub/router to delegate to specialized skills.

## A. Routing Mechanism

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 1 | **Keyword mapping** | Map keywords → skills (e.g., "page" → confluence-page) | Simple, predictable | Rigid, can miss synonyms |
| 2 | **Intent classification** | Describe intents, let LLM match | Flexible, handles variations | Less predictable |
| 3 | **Regex patterns** | Pattern-based routing rules | Precise control | Complex to maintain |
| 4 | **Explicit delegation** | "Route to confluence-page skill" in prompt | Clear, debuggable | Verbose |
| 5 | **Weighted scoring** | Score relevance of each skill, pick highest | Handles ambiguity | Overhead |
| 6 | **Multi-skill dispatch** | Route to multiple skills for complex tasks | Powerful | Coordination complexity |
| 7 | **Sequential chaining** | Skill A → Skill B → Skill C | Workflows | Error propagation |
| 8 | **Conditional routing** | If X then skill A, else skill B | Smart decisions | Logic complexity |

## B. Skill Registry

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 9 | **Static registry** | Hardcoded skill list in SKILL.md | Simple, fast | Manual updates |
| 10 | **Dynamic discovery** | Scan available skills at runtime | Auto-updates | Performance hit |
| 11 | **Skill categories** | Group by function (CRUD, search, admin) | Better organization | Category overlap |
| 12 | **Capability matrix** | Table of what each skill can do | Clear reference | Maintenance burden |
| 13 | **Skill aliases** | Multiple names for same skill | User-friendly | Confusion potential |
| 14 | **Skill dependencies** | Define skill prerequisites | Proper ordering | Complexity |

## C. Trigger Design

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 15 | **Broad catch-all** | Generic triggers ("confluence", "wiki") | Captures everything | May over-trigger |
| 16 | **Negative triggers** | "NOT for direct page operations" | Avoids conflicts | Hard to define |
| 17 | **Priority levels** | Hub triggers before/after specialists | Control flow | Priority wars |
| 18 | **Contextual triggers** | Trigger based on conversation state | Smart routing | State complexity |
| 19 | **Fallback trigger** | Only trigger if no specialist matches | Clean separation | Delayed matching |

## D. Request Processing

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 20 | **Entity extraction** | Extract page_id, space_key before routing | Informed routing | Parsing errors |
| 21 | **Request normalization** | Standardize format before dispatch | Consistency | Processing overhead |
| 22 | **Context enrichment** | Add user profile, defaults to request | Richer context | Privacy concerns |
| 23 | **Validation layer** | Validate before routing | Early error catch | Duplication |
| 24 | **Request splitting** | Break complex request into parts | Parallel processing | Reassembly |

## E. User Interaction

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 25 | **Disambiguation prompt** | "Did you mean page or space?" | Accuracy | Extra round-trip |
| 26 | **Skill suggestions** | "You might also want to use..." | Discoverability | Noise |
| 27 | **Help/browse mode** | List all skills and capabilities | Self-documenting | Long output |
| 28 | **Routing explanation** | "I'm using confluence-page because..." | Transparency | Verbose |
| 29 | **Confirmation mode** | "Route to X? [y/n]" | Safety | Friction |

## F. Error Handling & Fallbacks

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 30 | **Default fallback** | Use generic skill if no match | Always responds | May be wrong |
| 31 | **Retry with alt skill** | Try skill B if skill A fails | Resilience | Masking errors |
| 32 | **Error aggregation** | Collect errors from multiple skills | Complete picture | Information overload |
| 33 | **Graceful degradation** | Partial results if some skills fail | Better UX | Incomplete data |
| 34 | **Unknown handler** | Special handling for unmatched requests | Clear feedback | Dead end |

## G. Documentation & Metadata

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 35 | **Skill summary table** | Quick reference of all skills | Scannable | Space |
| 36 | **Example routing** | "For X, use skill Y" examples | Clear guidance | Maintenance |
| 37 | **Decision tree** | Visual/text routing flowchart | Understandable | Complex for many skills |
| 38 | **Capability tags** | #crud #search #admin on each skill | Filterable | Tag sprawl |
| 39 | **Version compatibility** | Which skill versions work together | Stability | Version tracking |

## H. Advanced Features

| # | Feature | Description | Pros | Cons |
|---|---------|-------------|------|------|
| 40 | **Conversation memory** | Route based on prior context | Smarter | State management |
| 41 | **User preferences** | Remember user's preferred skills | Personalized | Storage |
| 42 | **Usage analytics** | Track which skills used most | Insights | Privacy |
| 43 | **A/B routing** | Test different routing strategies | Optimization | Complexity |
| 44 | **Pre/post hooks** | Run logic before/after routing | Extensible | Overhead |

---

## Recommended Core Features

Based on the analysis, here are the **top recommendations** for a routing SKILL.md:

### Must-Have (MVP)

1. **Static skill registry** with capability descriptions
2. **Keyword mapping** for predictable routing
3. **Skill summary table** for quick reference
4. **Help/browse mode** for discoverability
5. **Default fallback** for unmatched requests
6. **Example routing** showing common patterns

### Should-Have

7. **Entity extraction** to inform routing decisions
8. **Disambiguation prompts** for ambiguous requests
9. **Routing explanation** for transparency
10. **Skill categories** for organization

### Nice-to-Have

11. **Multi-skill dispatch** for complex operations
12. **Sequential chaining** for workflows
13. **Contextual triggers** for smarter routing

---

## Example SKILL.md Structure

```markdown
---
name: confluence-assistant
description: Central hub for all Confluence operations - routes to specialized skills
triggers:
  - confluence
  - wiki
  - help with confluence
  - what can you do with confluence
---

# Confluence Assistant Hub

Routes requests to 14 specialized Confluence skills.

## Available Skills

| Skill | Handles | Triggers |
|-------|---------|----------|
| confluence-page | Page CRUD, versions | page, create page, edit page |
| confluence-search | CQL queries, export | search, find, query |
| confluence-space | Space management | space, list spaces |
| ... | ... | ... |

## Routing Rules

1. **Page operations** → confluence-page
2. **Search/CQL** → confluence-search
3. **Space management** → confluence-space
4. **Comments** → confluence-comment
5. **Unknown** → Ask for clarification

## How to Use

- "Create a page" → Routes to confluence-page
- "Search for docs" → Routes to confluence-search
- "What can you do?" → Shows this help
```

---

## Implementation Considerations

### Trigger Conflict Resolution

When a hub skill has broad triggers, it may conflict with specialized skills. Strategies:

1. **Specificity wins** - More specific triggers take precedence
2. **Hub as fallback** - Hub only activates when no specialist matches
3. **Hub as preprocessor** - Hub always activates first, then delegates

### State Management

For conversation memory and contextual routing:

- Store last-used skill for follow-up questions
- Track entities mentioned (page IDs, space keys)
- Remember user preferences per session

### Performance

- Static registries are faster than dynamic discovery
- Cache routing decisions for repeated patterns
- Lazy-load skill details only when needed

---

## Open Questions

1. Should the hub skill have its own scripts, or purely delegate?
2. How to handle requests that span multiple skills?
3. Should routing decisions be logged for debugging?
4. How to version the routing logic separately from skills?
5. Should users be able to bypass the hub and call skills directly?

# Feedback on Skills Router SKILL.md Proposal

**Reviewer:** Claude Code Assistant
**Date:** 2024-12-31
**Document Reviewed:** `~/IdeaProjects/SKILLS_ROUTER_SKILL_PROPOSAL.md`

---

## Overall Assessment

**Rating: Strong foundation, needs Claude Code specifics**

The proposal demonstrates excellent synthesis of 7 brainstorm documents and identifies the right problems. However, it remains too abstract and doesn't address how Claude Code actually processes SKILL.md files. The gap between "what we want" and "how Claude Code works" needs bridging.

---

## Critical Gaps

### 1. Missing: How Claude Code Actually Routes

The proposal never specifies the **execution mechanism**. In Claude Code:

- Skills are loaded based on **frontmatter triggers** matching user intent
- The LLM decides which skill to invoke - there's no runtime "router" code
- Delegation happens via the **Skill tool** or by referencing other skills in prose

**Recommendation:** Add a section explaining that routing in Claude Code is **LLM-mediated**, not code-mediated. The SKILL.md content *guides* the LLM's routing decision, it doesn't *execute* routing logic.

```markdown
## How Routing Actually Works in Claude Code

1. User sends request
2. Claude Code matches triggers → loads relevant SKILL.md files
3. LLM reads SKILL.md content and decides which skill handles the request
4. If hub skill is loaded, its content instructs LLM to delegate to specialized skill
5. LLM invokes specialized skill via Skill tool or direct reference

The router SKILL.md is *instructional*, not *executable*.
```

### 2. Confidence Scoring is LLM-Native

The proposal describes confidence thresholds (>0.85 auto-route, 0.50-0.85 clarify) as if they're computed values. In reality:

- The LLM implicitly has confidence in its routing decisions
- You can't extract a numeric score from the LLM's decision
- Instead, instruct the LLM to **ask for clarification when uncertain**

**Recommendation:** Replace confidence scoring with **instructional uncertainty handling**:

```markdown
## When Uncertain

If the request could reasonably match multiple skills:
1. Do NOT guess - ask the user to clarify
2. Present the top 2-3 options with brief descriptions
3. Example: "Did you mean to search for pages (confluence-search) or list pages in a space (confluence-space)?"
```

### 3. YAML Config vs SKILL.md Confusion

The proposal conflates two different things:

| Concept | Format | Purpose |
|---------|--------|---------|
| SKILL.md | Markdown with YAML frontmatter | Instructions for LLM |
| Router config | Pure YAML | Hypothetical runtime config |

Claude Code uses SKILL.md files, not YAML config files. The splunk-assistant-skills-lib YAML schema is interesting but **doesn't apply** to how Claude Code works.

**Recommendation:** Focus exclusively on SKILL.md structure. Remove references to YAML configuration unless proposing a new feature to Claude Code itself.

### 4. Entity Extraction is Already LLM-Native

The proposal lists entity extraction patterns:
- Issue keys: `[A-Z]+-\d+`
- Project keys: `[A-Z]{2,10}`

This is unnecessary. The LLM already excels at entity extraction. You don't need regex patterns in SKILL.md.

**Recommendation:** Remove entity extraction from P1. Instead, document **what entities each skill expects** so the LLM knows what to extract:

```markdown
## confluence-page

**Requires:** page_id (numeric) OR page title + space_key
**Optional:** parent_id, body content, labels
```

### 5. Progressive Disclosure - How?

The proposal mentions "progressive disclosure" and "3-level loading" but never explains the mechanism. In Claude Code:

- SKILL.md is loaded when triggers match
- There's no built-in "load more details" mechanism
- References can point to additional files, but loading is manual

**Recommendation:** Be explicit about the pattern:

```markdown
## Progressive Disclosure Pattern

1. **SKILL.md** (~100-150 lines): Routing rules, capability matrix, common examples
2. **References folder**: Detailed API docs, edge cases, troubleshooting
3. **Instruction in SKILL.md**: "For detailed API documentation, read `references/api-v2.md`"

The LLM loads references on-demand using the Read tool when needed.
```

---

## Structural Feedback

### 6. Anti-Patterns Section is Excellent

The anti-patterns section is the strongest part of the proposal. Specific, actionable, with before/after examples.

**Suggestion:** Expand this into a standalone reference document. It's valuable beyond just routing.

### 7. Open Questions Need Answers, Not Just Questions

The 8 open questions are real concerns, but a proposal should propose answers:

| Question | Proposed Answer |
|----------|-----------------|
| Stateless vs Stateful | **Stateless** - Claude Code doesn't persist session state. Use explicit references ("the page I just created" won't work; "page 12345" will). |
| Fallback Philosophy | **Ask for clarification** - Better UX than guessing wrong. |
| Context Lifetime | **Per-message only** - No persistence. Instruct users to be explicit. |
| Multi-plugin Federation | **Not in scope for SKILL.md** - This is a Claude Code platform feature, not a skill feature. |

### 8. Phase 1 Should Be Smaller

The proposed Phase 1 has 5 items. For a true MVP:

**Minimal Phase 1:**
1. Complete skill registry (table of skills + descriptions)
2. Routing rules in prose (not config)
3. Disambiguation instructions

That's it. Everything else comes after validating the basic approach works.

### 9. Missing: Concrete Example

The template uses placeholders (`{product}`, `skill-a`). Provide a **real example** for confluence-assistant:

```markdown
---
name: confluence-assistant
description: Central hub for Confluence operations - routes to 14 specialized skills
triggers:
  - confluence
  - wiki
  - help with confluence
  - what can I do in confluence
---

# Confluence Assistant

I route requests to specialized Confluence skills. Don't try to handle requests directly - delegate to the appropriate skill.

## Quick Reference

| If the user wants to... | Use this skill |
|-------------------------|----------------|
| Create, read, update, delete pages | confluence-page |
| Search with CQL | confluence-search |
| Manage spaces | confluence-space |
| Add/remove labels | confluence-label |
| Work with comments | confluence-comment |
| Upload/download files | confluence-attachment |
| Set permissions | confluence-permission |
| View analytics | confluence-analytics |
| Manage watchers | confluence-watch |
| Navigate page hierarchy | confluence-hierarchy |
| Work with templates | confluence-template |
| Manage content properties | confluence-property |
| JIRA integration | confluence-jira |

## Routing Rules

1. **Explicit skill mention wins** - If user says "use confluence-page", use it
2. **Page operations** - create/read/update/delete/copy/move pages → confluence-page
3. **Search/find/query** - CQL, finding content → confluence-search
4. **Labels/tags** - Adding, removing, searching by label → confluence-label
5. **Multiple operations** - Break into steps, route each to appropriate skill

## When Uncertain

If a request could match multiple skills, ask:
> "I can help with that. Did you want to:
> - Search for pages matching criteria (confluence-search)
> - List pages in a specific space (confluence-space)
> - Something else?"

## What I Don't Do

- Don't handle requests directly - always delegate
- Don't guess when uncertain - ask for clarification
- Don't combine operations silently - confirm multi-step workflows
```

---

## Minor Issues

### 10. Capability Matrix Format

The proposed capability matrix uses checkmarks:

```
| Capability | skill-a | skill-b |
|------------|---------|---------|
| Create     | ✓       |         |
```

**Problem:** LLMs process text better than symbols.

**Recommendation:** Use words:

```
| Capability | skill-a | skill-b |
|------------|---------|---------|
| Create     | Yes     | No      |
```

### 11. Trigger Taxonomy Overcomplicates

The proposal suggests: "Verbs + nouns + modifiers + negative triggers"

This is overthinking it. Triggers in Claude Code are simple string matches. The LLM does the semantic heavy lifting.

**Recommendation:** Keep triggers simple and specific:

```yaml
triggers:
  - confluence page
  - create confluence page
  - edit page in confluence
```

### 12. Workflow Templates Are Premature

Multi-skill workflow templates (P1) are premature. First validate that basic routing works well before adding workflow orchestration.

**Recommendation:** Move to P3 or post-MVP.

---

## Summary of Recommendations

| Priority | Recommendation |
|----------|----------------|
| **Critical** | Add section on how Claude Code actually processes SKILL.md |
| **Critical** | Replace confidence scoring with instructional uncertainty handling |
| **Critical** | Provide concrete confluence-assistant example, not abstract template |
| **High** | Clarify SKILL.md vs YAML config - focus on SKILL.md only |
| **High** | Answer open questions with proposed decisions |
| **High** | Shrink Phase 1 to true MVP (3 items) |
| **Medium** | Remove entity extraction from scope (LLM handles this) |
| **Medium** | Explain progressive disclosure mechanism explicitly |
| **Medium** | Use words not symbols in capability matrix |
| **Low** | Simplify trigger taxonomy |
| **Low** | Move workflow templates to P3 |

---

## Conclusion

The proposal is a solid foundation but needs grounding in how Claude Code actually works. The key insight: **routing in Claude Code is LLM-mediated instruction following, not code execution**. The SKILL.md doesn't run routing logic - it provides instructions that guide the LLM's routing decisions.

Reframe the proposal around this reality, provide concrete examples, and shrink the MVP scope. Then it will be ready for implementation.

---

*Feedback provided by Claude Code Assistant*

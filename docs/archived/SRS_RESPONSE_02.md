# Feedback on Skills Router SKILL.md Proposal v2.0

**Reviewer:** Claude Code Assistant
**Date:** 2024-12-31
**Document Reviewed:** `~/IdeaProjects/SKILLS_ROUTER_SKILL_PROPOSAL.md` (v2.0)

---

## Overall Assessment

**Rating: Ready for implementation with minor refinements**

This is a substantial improvement over v1. The proposal now correctly frames routing as LLM-mediated instruction following, provides concrete examples, and makes clear decisions on previously open questions. The jira-assistant reference implementation is actionable.

**Recommendation:** Proceed to implementation. Address the refinements below during implementation, not as blockers.

---

## What's Working Well

### 1. Core Conceptual Framing ✓
The "How Routing Actually Works" section nails it:
> "The router SKILL.md is *instructional*, not *executable*."

This is the key insight that was missing in v1.

### 2. Certainty-Based Routing ✓
Replacing computed confidence scores with natural language certainty instructions is exactly right:
```markdown
## When to Route with High Certainty
Route directly to the skill without asking when:
- User explicitly mentions the skill or its primary trigger
- Request contains a strong entity signal
- Only one skill could reasonably handle the request
```

### 3. Concrete Reference Implementation ✓
The jira-assistant example is actionable and follows the principles. Good balance of brevity and completeness.

### 4. Decision Log ✓
Documenting decisions with rationale and rejected alternatives is excellent practice. Keeps future maintainers informed.

### 5. Anti-Patterns Preserved ✓
The anti-patterns section remains strong and practical.

---

## Refinements Needed

### 1. Skill Tool Invocation Syntax Missing

The proposal says to "invoke the Skill tool" but never shows the actual syntax. Add a concrete example:

```markdown
## How to Invoke a Specialized Skill

When routing to a specialized skill, use the Skill tool:

Example - routing to jira-agile:
1. Determine jira-agile is the correct skill
2. Invoke: `Skill tool with skill="jira-agile"`
3. The jira-agile SKILL.md loads and guides the operation

Do NOT attempt to call scripts directly from the hub skill.
```

**Why this matters:** Implementers need to know the exact mechanism. "Invoke the Skill tool" is vague.

### 2. Hub-as-Entry-Point vs Actual Behavior Mismatch

The Decision Log says:
> D2: Hub-as-entry-point - Catch broad/ambiguous requests first

But the "When This Hub Skill Activates" section describes fallback behavior:
> - User mentions the product broadly
> - User is unsure which skill to use
> - Request is ambiguous between multiple skills

These describe when the hub catches things *others don't*, which is fallback behavior.

**Recommendation:** Clarify the intended pattern. If hub-as-entry-point, the hub should always activate first and delegate. If hub-as-fallback (which the triggers suggest), update the Decision Log.

My assessment: The triggers describe **hub-as-fallback**, which is correct. Update D2 to match.

### 3. Testing Strategy Lacks Execution Method

The golden test set format is good, but how do you actually run the tests?

```yaml
- id: TC001
  input: "create a bug in TES"
  expected_skill: jira-issue
```

**Missing:**
- Manual testing protocol? Automated?
- How to measure "90%+ accuracy on golden test set"?
- Who runs these tests and when?

**Recommendation:** Add a "Test Execution" subsection:

```markdown
## Test Execution

### Manual Protocol
1. Start fresh Claude Code session
2. Load jira-assistant skill
3. Submit each test input
4. Record: which skill was invoked, any disambiguation
5. Compare against expected outcomes

### Tracking
- Spreadsheet with test ID, input, expected, actual, pass/fail
- Run full suite before each release
- Track accuracy trend over time

### Automation (Future)
Consider building a test harness that:
- Submits inputs to Claude Code programmatically
- Captures routing decisions
- Compares against golden set
```

### 4. Context Awareness Overpromises

The proposal states:
> "Claude maintains conversation context naturally."

This is partially true but oversimplified. Context works within a conversation but:
- Tool calls can fragment context
- Long conversations may lose early context
- Pronoun resolution across many turns is unreliable

**Recommendation:** Add caveats:

```markdown
## Context Limitations

Context is maintained within a conversation, but:
- After 10+ exchanges, early context may be summarized away
- When uncertain, ask explicitly rather than assuming
- For critical operations, confirm entity: "Just to confirm, you mean TES-123?"
```

### 5. Token Budget When Both Skills Load

The token budget section addresses hub and specialized skills separately but not together:

| Component | Target |
|-----------|--------|
| Hub SKILL.md | 120-150 lines |
| Specialized SKILL.md | 80-150 lines |

**Missing:** What happens when hub triggers, then invokes specialized skill? Both are in context.

**Recommendation:** Add guidance:

```markdown
## Combined Token Impact

When hub routes to a specialized skill, both SKILL.md files are in context:
- Hub: ~120 lines
- Specialized: ~100 lines
- Combined: ~220 lines

This is acceptable. The hub provides routing context while the specialized skill guides execution.

If token pressure occurs, the hub content becomes less relevant after routing and may be summarized.
```

### 6. No Confluence Example

The proposal uses jira-assistant as the reference implementation. For the Confluence-Assistant-Skills project, a confluence-assistant example would be directly applicable.

**Recommendation:** Add a confluence-assistant variant in an appendix, or note that the jira-assistant pattern applies directly with these substitutions:

| JIRA | Confluence |
|------|------------|
| jira-issue | confluence-page |
| jira-search | confluence-search |
| jira-agile | confluence-hierarchy |
| jira-lifecycle | (N/A - no status transitions) |

### 7. Success Metrics Are Unmeasurable

> - 90%+ accuracy on golden test set

How is accuracy defined? If the test expects `jira-issue` and Claude routes to `jira-issue`, that's a pass. But what about:
- Claude asks for clarification when test expected direct routing?
- Claude routes correctly but to a deprecated skill alias?

**Recommendation:** Define pass/fail criteria explicitly:

```markdown
## Pass/Fail Criteria

### Direct Routing Tests
- PASS: Correct skill invoked without clarification
- FAIL: Wrong skill invoked OR unnecessary clarification

### Disambiguation Tests
- PASS: Appropriate clarification question asked
- FAIL: Wrong options presented OR direct routing when ambiguous

### Context Tests
- PASS: Correct entity resolved from context
- FAIL: Wrong entity OR unnecessary "which one?" question
```

### 8. MVP Could Be Smaller

Phase 1 has 5 items:
1. Complete skill registry
2. Routing rules in natural language
3. Quick reference table
4. Basic context instructions
5. Disambiguation templates

Items 3-5 could be combined or deferred:
- Quick reference table IS routing rules (just formatted)
- Context instructions can be minimal initially
- Disambiguation templates can be two examples, not comprehensive

**True MVP:**
1. Complete skill registry with capabilities
2. Routing rules (including quick reference format)
3. One disambiguation example

Everything else is Phase 1.5.

---

## Minor Issues

### 9. Inconsistent Certainty Terminology

The proposal uses both "certainty" and "confidence" interchangeably:
- Section title: "Certainty-Based Routing"
- Test format: `certainty: high`
- But also: "confidence thresholds" in rejected alternatives

**Recommendation:** Standardize on "certainty" throughout to distinguish from computed confidence scores.

### 10. Workflow Section Could Show Skill Tool Calls

The "Common Workflows" section describes steps but doesn't show how they chain:

```markdown
### Create Epic with Stories
1. Use jira-agile to create the epic
2. Use jira-issue to create each story
3. Use jira-agile to link stories to epic
```

**Better:**
```markdown
### Create Epic with Stories
1. Invoke Skill(jira-agile) → create epic → returns EPIC-123
2. Invoke Skill(jira-issue) → create story, reference EPIC-123
3. Invoke Skill(jira-agile) → link story to EPIC-123
```

### 11. Missing: Error Recovery Examples

The proposal mentions error handling but provides no examples:

```markdown
## Error handling guidance
- What to do when skills fail
- How to suggest alternatives
```

**Recommendation:** Add one concrete example:

```markdown
## When a Skill Fails

If jira-issue fails to create an issue:
1. Report the error clearly: "Failed to create issue: {error message}"
2. Suggest recovery: "You might want to check project permissions or try a different issue type"
3. Offer alternatives: "Would you like to search for similar existing issues instead?"

Do NOT silently retry or switch to a different skill without user consent.
```

---

## Summary of Refinements

| Priority | Refinement |
|----------|------------|
| High | Add Skill tool invocation syntax example |
| High | Clarify hub-as-entry-point vs fallback (update Decision Log) |
| High | Add test execution methodology |
| Medium | Add context limitations/caveats |
| Medium | Address combined token budget scenario |
| Medium | Define pass/fail criteria for metrics |
| Low | Add confluence-assistant variant or mapping |
| Low | Standardize certainty terminology |
| Low | Show Skill tool calls in workflow examples |
| Low | Add error recovery example |

---

## Conclusion

This proposal is **ready for implementation**. The core design is sound, the jira-assistant reference implementation is actionable, and the decisions are well-reasoned.

The refinements above are improvements, not blockers. Address them as you implement:
- Add Skill tool syntax when writing the actual SKILL.md
- Clarify hub behavior based on what works in practice
- Build test methodology alongside the test cases

**Recommended next step:** Implement jira-assistant SKILL.md following this proposal, then adapt the pattern for confluence-assistant.

---

*Feedback provided by Claude Code Assistant*

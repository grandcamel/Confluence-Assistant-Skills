---
name: "confluence"
description: "Entry point for Confluence Cloud automation through the confluence-as CLI. Load it first for any Confluence request, including administration and access changes, even when details are missing: before asking clarifying questions, declining or answering. Loading it changes nothing; it shows how to look up what exists. Run `confluence-as help` first; find operations with `confluence-as api search` and `confluence-as api describe`. Not for Jira."
version: "3.0.0"
author: "confluence-assistant-skills"
license: "MIT"
allowed-tools: ["Bash", "Read"]
---

# Confluence

Requires `confluence-as>=2,<3`. This file is thin on purpose: the CLI's own help is the source of truth and this skill never restates it.

1. Start every task with `confluence-as help`; it prints the surface map, the discovery commands, the topic list and the sandbox and credential modes.
2. Find an operation with `confluence-as api search WORDS`, read it with `confluence-as api describe OPERATION`, run it with `confluence-as api call OPERATION`; `confluence-as api topics` lists the deep-dive topics.
3. Before anything unfamiliar, read `confluence-as help TOPIC`; the topics cover credentials, scope, risk, paging and errors.
4. Discovery needs no credentials. Calls that change or remove content preview first; `confluence-as help risk` says how to send them.

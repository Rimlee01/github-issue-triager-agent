"""
Centralized prompt templates for each LangGraph node.

Decision: prompts live in one module, separate from node logic. This makes
prompt engineering iteration (the actual day-to-day work of tuning an agent)
a diff against this file alone, and keeps node functions focused on
orchestration (calling the LLM, parsing output, updating state) rather than
mixing in long string literals.

Every prompt enforces a strict JSON output contract — we ask Claude to act
as a structured extraction step, not a free-form chatbot, because downstream
nodes and the API response schema depend on parseable fields.
"""

ISSUE_ANALYZER_PROMPT = """You are a senior software engineer triaging a GitHub issue.

Issue title: {issue_title}
Issue description:
{issue_description}

Analyze this issue and respond with ONLY a JSON object (no markdown fences, no preamble):
{{
  "summary": "<one or two sentence neutral summary of the actual problem being reported>",
  "technical_area": "<the likely subsystem/component affected, e.g. 'authentication', 'database layer', 'CLI parsing', 'build pipeline'>"
}}
"""

CLASSIFICATION_PROMPT = """You are classifying a GitHub issue into a category.

Issue summary: {summary}
Technical area: {technical_area}
Original title: {issue_title}
Original description: {issue_description}

Relevant repository context retrieved via search:
{repo_context}

Classify into exactly one category: bug, feature_request, documentation, performance, security, question.

Respond with ONLY a JSON object:
{{
  "category": "<one of: bug, feature_request, documentation, performance, security, question>",
  "category_confidence": <float 0.0-1.0>,
  "suggested_labels": ["<github label 1>", "<github label 2>", "..."]
}}
"""

PRIORITY_PROMPT = """You are assessing the priority of a GitHub issue for a maintainer triaging a backlog.

Issue summary: {summary}
Category: {category}
Technical area: {technical_area}
Original description: {issue_description}

Similar/related issues found in the repository:
{similar_issues_context}

Assess priority using these criteria:
- CRITICAL: data loss, security vulnerability, crash affecting all users, broken core functionality with no workaround
- HIGH: significant functionality broken for many users, no easy workaround
- MEDIUM: functionality impaired but workaround exists, or affects a subset of users
- LOW: minor inconvenience, cosmetic issue, edge case, or a reasonable feature request with no urgency

Respond with ONLY a JSON object:
{{
  "priority": "<critical|high|medium|low>",
  "priority_reason": "<one or two sentences explaining the priority assignment, citing specific evidence from the issue>"
}}
"""

SOLUTION_PROMPT = """You are a senior engineer proposing a fix for a GitHub issue, grounded in actual repository code.

Issue summary: {summary}
Category: {category}
Technical area: {technical_area}
Original description: {issue_description}

Relevant code retrieved from the repository (use this to ground your answer — do not invent file paths or functions not shown here):
{repo_context}

Based ONLY on the issue description and the retrieved code above, propose a solution.
If the retrieved code doesn't clearly show the root cause, say so honestly rather than guessing specifics.

Respond with ONLY a JSON object:
{{
  "root_cause": "<your best hypothesis for the underlying cause, grounded in the retrieved code where possible>",
  "suggested_fix": "<concrete description of what should change>",
  "files_to_modify": ["<file path 1>", "<file path 2>"],
  "implementation_approach": "<2-4 sentence approach a contributor could follow>",
  "solution_confidence": <float 0.0-1.0, lower if retrieved context didn't clearly cover the relevant code>
}}
"""

RESPONSE_GENERATOR_PROMPT = """You are writing a GitHub issue comment as a helpful, professional maintainer.

Issue summary: {summary}
Category: {category}
Priority: {priority}
Root cause hypothesis: {root_cause}
Suggested fix: {suggested_fix}
Implementation approach: {implementation_approach}
Duplicate of: {duplicate_info}

Write a concise, friendly GitHub-style comment (plain text, GitHub-flavored markdown allowed) that:
1. Thanks the reporter
2. Summarizes the diagnosis in plain language
3. Mentions the suggested fix/next step
4. If this is a likely duplicate, politely says so and links to the original issue number
5. Is encouraging and professional, not robotic

Respond with ONLY the comment text — no JSON, no preamble, no markdown fences around the whole thing.
"""

PR_DESCRIPTION_PROMPT = """You are writing a GitHub Pull Request description for a fix.

Issue summary: {summary}
Root cause: {root_cause}
Suggested fix: {suggested_fix}
Files to modify: {files_to_modify}
Implementation approach: {implementation_approach}

Write a professional GitHub PR description in markdown with these sections:
## Summary
## Changes Made
## How to Test
## Related Issue

Respond with ONLY the markdown PR description, no preamble.
"""

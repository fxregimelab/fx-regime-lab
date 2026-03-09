---
name: "Explain File In Depth"
description: "Deeply explain a file or function line by line, including logic, data flow, and library usage."
argument-hint: "File/function to explain and optional depth (for example: pipeline.py or create_html_brief.py:120)"
agent: "Deep Code Explainer"
---
Explain the requested code in full technical depth.

Requirements:
- Cover overall purpose first, then dive into details.
- Explain every import and library used:
  - source package/module
  - standard library vs third-party vs local
  - why this code needs it
- Walk through logic line-by-line (or section-by-section for very large files) in execution order.
- Trace data flow from inputs to transformations to outputs and side effects.
- Call out key conditions, edge cases, error paths, and performance implications.
- Use clickable file references with line numbers where possible.
- Default to an intermediate-developer teaching style unless the user asks for beginner or advanced depth.
- If the target scope is ambiguous, ask one concise clarifying question before analysis.

Use this output structure:
1. What This Code Does
2. Libraries and Imports Used
3. Step-by-Step Logic
4. Data Flow (Inputs -> Transformations -> Outputs)
5. Key Conditions and Edge Cases
6. Quick Recap

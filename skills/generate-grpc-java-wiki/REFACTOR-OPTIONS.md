# Generate Wiki Skill Refactoring Options Comparison

## Current Implementation Scope

This implementation chose:

- `Option 1: Pure Prompt-based`

Post-implementation goals:

- Skill no longer executes generation through `scripts/generate-wiki.js`
- Skill no longer embeds project parsing logic like `parser.js`
- Generation actions are completed by Agent at runtime through tools
- Skill only retains prompts, workflow instructions, style references, and output requirements

## Background

The current `generate-wiki` skill adopts the `code-driven wiki generator` approach:

- Use scripts to parse proto
- Use scripts to scan Java implementations
- Use scripts to calculate method line numbers and end boundaries
- Use scripts to generate markdown/html

The new direction you proposed is:

- Avoid re-implementing code search, code understanding, and project scanning capabilities that Claude Code / Codex agents already have
- Rely more on Agent's built-in tools and LLM capabilities for source code location, function understanding, and interface summarization
- Skill only retains prompts, generation workflow, and unified wiki style

This direction is reasonable. The key is not "whether Agent can do it", but "what form this skill should be consolidated into".

---

## Core Recommendation

It is recommended to change the current skill from:

- `code-driven wiki generator`

To:

- `agent-driven wiki workflow`

That is:

- `Source code discovery, interface identification, function understanding` are delegated to Agent
- `Page structure, style specifications, output requirements` remain in the skill

No longer design the skill as a tool with "built-in parser + built-in generator".

---

## Three Refactoring Options

## Option 1: Pure Prompt-based

### Definition

Delete existing parsing and generation scripts, skill only retains:

- Prompts
- Operation steps
- Fixed wiki page structure description
- Fixed style requirements

Agent at runtime:

- Search proto / grpc / Java implementations
- Find interfaces and corresponding methods
- Organize source code locations
- Generate markdown/html

### Suitable Scenarios

- Primarily used interactively by yourself in Claude Code / Codex
- One generation at a time
- More emphasis on flexibility and low maintenance cost

### Advantages

- Lowest skill maintenance cost
- Maximize use of Agent's built-in tools
- No need to maintain Java/proto specialized parsing code
- Best fits the goal of "write less code, rely more on Agent"

### Disadvantages

- Output stability depends on Agent's current reasoning process
- Results may vary slightly between different Agents
- Page structure and field naming are more prone to drift
- Result consistency is average when batch generating for large projects

### Conclusion

This is the lightest option, suitable for personal high-frequency interactive use.

---

## Option 2: Prompt + Template Skeleton

### Definition

Delete project parsing logic, retain a thin template skeleton, such as:

- `index.html`
- `style.css`
- `nav.js`
- `service page markdown template`
- `architecture/features/ER page templates`

Agent is responsible for first generating document content, then filling it into fixed templates.

### Suitable Scenarios

- Want to maintain unified visual style
- But don't want to continue maintaining heavy parsers

### Advantages

- More stable page style
- Easier to unify document structure than pure Prompt
- Still retains Agent-driven flexibility

### Disadvantages

- Document content organization still highly depends on Agent
- Without unified data structure, final output will still fluctuate
- Not friendly for subsequent batch verification

### Conclusion

This is a more stable intermediate state than Option 1, but not yet "controllable" enough.

---

## Option 3: Prompt + Template Skeleton + Output Contract

### Definition

Delete existing parser and generator, retain:

- Prompts
- Workflow description
- Template skeleton
- Unified output contract

Agent first generates intermediate results with unified structure, then renders them into wiki according to templates.

### Suitable Scenarios

- Want to maximize use of Agent
- Also want subsequent results to be comparable, reusable, and testable

### Advantages

- Retains Agent's flexibility
- Easier to maintain structural consistency than pure Prompt
- Facilitates subsequent comparison of different Agents or different prompts
- Facilitates subsequent automated checking and regression testing

### Disadvantages

- One more layer of constraint design than the first two options
- Need to define an intermediate data structure

### Conclusion

This is the most recommended option currently.

It does not return to the "heavy parser" old path, but also does not degenerate into "just a prompt, completely uncontrollable".

---

## Recommended Option

Recommended to adopt:

- `Option 3: Prompt + Template Skeleton + Output Contract`

Reasons:

1. It aligns with your goal of "maximizing use of Claude Code / Codex Agent capabilities".
2. It avoids continuing to maintain heavy logic parsers like `parser.js`.
3. It retains the most critical structural control capability, facilitating subsequent testing of the effectiveness differences between the three options.

If the current goal is just for your daily use, you can also start with Option 1 or Option 2, then gradually evolve to Option 3.

---

## Responsibility Boundary Recommendations

## Skill Responsibilities

- Generation workflow description
- Page information architecture
- Page style templates
- Output format requirements
- Quality checklist

## Agent Responsibilities

- Search proto, grpc, Java source code
- Determine interface implementation attribution
- Extract key code snippets
- Summarize call flows and business logic
- Generate intermediate results
- Render wiki pages according to templates

## Capabilities No Longer Recommended to be Built into the Skill

- Proto parser
- Java method scanner
- Line number inferrer
- Method end boundary estimator
- JPA entity specialized analyzer
- Business logic rule identifier

---

## Current Repository Recommended Adjustments

## Recommended to Delete or Retire

- `scripts/parser.js`
- `scripts/generate-wiki.js`
- Tests strongly coupled with the above logic

Including but not limited to:

- `test/parser.test.js`
- Generation tests that depend on script parsing results

## Recommended to Retain and Refactor

- `SKILL.md`
- `README.md`
- Content related to presentation layer in `assets/templates.js`

## Recommended to Add

- `docs/workflow.md`
- `docs/output-contract.md`
- `docs/quality-checklist.md`
- `examples/output-example.json`
- `examples/service-example.md`

---

## Recommended Directory Structure

```text
generate-wiki/
├── SKILL.md
├── README.md
├── REFACTOR-OPTIONS.md
├── docs/
│   ├── workflow.md
│   ├── output-contract.md
│   └── quality-checklist.md
├── templates/
│   ├── index.html
│   ├── style.css
│   ├── nav.js
│   ├── page-service.md
│   ├── page-architecture.md
│   ├── page-features.md
│   └── page-er.md
└── examples/
    ├── output-example.json
    └── service-example.md
```

---

## Output Contract Recommendations

It is recommended that Agent first produce intermediate results with unified structure, then render documents.

Example:

```json
{
  "project": {
    "name": "demo-service",
    "repo": "group/demo-service",
    "branch": "main"
  },
  "services": [
    {
      "serviceName": "UserService",
      "methodName": "Login",
      "summary": "User login API",
      "proto": {
        "file": "api/src/main/proto/user.proto",
        "startLine": 42
      },
      "grpcEntry": {
        "file": "service/src/main/java/com/demo/UserGrpcService.java",
        "startLine": 88,
        "endLine": 109
      },
      "businessLogic": {
        "file": "service/src/main/java/com/demo/LoginService.java",
        "startLine": 120,
        "endLine": 168
      },
      "requestType": "LoginRequest",
      "responseType": "LoginResponse",
      "flowSummary": [
        "Parameter validation",
        "Query user",
        "Verify password",
        "Generate token",
        "Return result"
      ],
      "warnings": [
        "Login failure branch needs additional exception description"
      ]
    }
  ]
}
```

The value of this contract is not to replace Agent, but to ensure different Agents' final results fall into a unified structure, facilitating testing and comparison.

---

## Recommended Content for New SKILL

The new `SKILL.md` is recommended to be changed to the following structure:

1. `When to use`
2. `What this skill does`
3. `Required workflow`
4. `Output requirements`
5. `Quality checklist`
6. `Failure / uncertainty handling`

Key points to clarify:

- When code implementation cannot be found, must mark `TODO`
- Fabricating file names or method names is not allowed
- Fabricating precise line numbers is not allowed
- If multiple candidate implementations exist, must clearly list candidates and explain final selection basis

This part is the most important "anti-drift constraint" in the Agent-based approach.

---

## Page Template Strategy

Templates are only responsible for:

- Fixed page skeleton
- Fixed visual style

Templates are no longer responsible for:

- Code parsing
- Business identification
- Method location

Service page template is recommended to fixedly include the following sections:

- Interface definition
- Proto definition
- Proto source location
- Call flow
- gRPC entry layer
- Business logic layer
- Data model
- Call example
- Notes

---

## Recommended Agent Workflow

It is recommended to fixedly adopt the following workflow for actual generation:

1. Scan project, identify proto and Java source code directories.
2. Output complete list of all gRPC services and rpc methods.
3. For each rpc method, locate gRPC entry implementation and business method.
4. Extract key code snippets and logic summaries.
5. First generate intermediate results with unified structure.
6. Then render wiki pages according to templates.
7. Finally execute quality check.

This workflow is more conducive to subsequent comparable testing of the three options.

---

## Risks and Controls

## Main Risks

- Different Agents may have different standards for identifying business implementations
- Line numbers and method end boundaries may fluctuate
- Large repository full generation may easily miss edge interfaces
- Pure Agent reasoning results may appear "reasonable but actually inaccurate"

## Control Recommendations

- Force unified output contract
- Clarify "must mark when uncertain, fabrication is not allowed"
- First generate interface list, then generate pages for each interface
- For each interface, retain "candidate implementations" and "final selection basis"

---

## Suitable Testing Method

If you want to test these three options separately later, it is recommended to do parallel comparison on the same real project:

1. Same project input
2. Same wiki output target
3. Let Option 1, Option 2, and Option 3 execute separately
4. Compare the following indicators:

- Interface identification completeness
- Source code location accuracy
- Page structure consistency
- Document readability
- Generation duration
- Interaction rounds
- Maintenance cost

It is recommended to eventually record the test conclusions as a comparison document.

---

## Final Conclusion

Based on the current goal, it is recommended to adjust the `generate-wiki` skill to:

- `Agent-driven`
- `Template-fixed`
- `Clear output contract`
- `No longer embed heavy code parsers`

If you prioritize "personal efficient use", Option 1 is already feasible.

If you want to do systematic comparison, stable iteration, and quality control later, Option 3 is most suitable.

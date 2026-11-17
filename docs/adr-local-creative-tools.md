# ADR: Registry-backed creative tools over the existing local AI boundary

**Status:** Accepted for this implementation
**Date:** 2026-11-17

## Context

Pictures to CAD already has multiple independent studios, a bounded local text assistant, and specialized depth/vision workers. Navigation metadata was repeated in the header, router and command launcher. The Ollama helper required a repository install even when a usable system installation existed. The chat picker included embedding-only weights.

## Decision

Use one typed frontend studio catalog and an application-owned backend creative-tool registry. Add a creative notes workspace with directions, critique and making-plan tools. Reuse the existing loopback-only transport, verify local completion capability, and share its cancellation-safe inference slot across all web text requests. Prefer existing system Ollama without changing its service configuration or downloading weights.

## Options considered

| Option | Benefits | Costs |
| --- | --- | --- |
| Registry over existing backend (selected) | Reuses model checks and resource bounds; fewer navigation definitions; tools added without another chat endpoint | New input/output types still require explicit engineering |
| Separate inference service per tool | Stronger process isolation and independent scaling | More processes, configuration and model contention for this local app |
| Arbitrary browser plugins/endpoints | Maximum flexibility | Would introduce executable code, endpoint trust and lifecycle contracts beyond this request |

## Consequences

The catalog makes workspaces discoverable and keeps route metadata aligned. Creative text tools remain bounded, typed and testable. Generated notes preserve the submitted inputs for review and export, while CAD geometry stays under its existing measured workflow. The process-local inference lock does not coordinate separate web workers or CLI probes; the supported launcher uses a single worker. Depth, image features, image generation and arbitrary 3D generation remain separate capabilities with their own model and acceptance requirements.

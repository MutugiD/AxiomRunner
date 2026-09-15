# ADR-0004: Rank Only Observed Evidence

- Status: accepted
- Date: 2026-09-15
- Owners: maintainers

## Decision

Candidate ranking uses static checks and sandbox observations. Model confidence
and claims in generated prose have no score. Test design is isolated from
candidate source and evidence retains origin and lineage.

## Consequences

The system may prefer a simpler candidate with stronger tests over a model's
favored strategy. Reports remain auditable and deterministic.

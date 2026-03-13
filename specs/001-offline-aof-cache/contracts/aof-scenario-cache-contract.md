# Contract: AoF Offline Scenario Cache and Runtime Retrieval

## Purpose
Define contract for persistent scenario cache lookup, invalidation, fallback compute, and write-back.

## Runtime Request Contract
Input fields:
- selected_position
- position_actions
- metric
- pot_size
- bet_amount
- strict_current_action
- runtime knobs (simulations, combo_samples, timeout_ms, seed)

Derived identity:
- Request cache key: generated from normalized request context for request-local memory caching.
- Canonical solver key: generated from solver-equivalence semantics (metric, selected action, opponent count, pot/bet, runtime/policy signatures) for persistent reuse across equivalent seat-label permutations.
- Current implementation builds request and canonical keys in provider, and stores signature metadata in `AoFScenarioCacheStore`.

## Runtime Response Contract
Output shape must match existing AoF UI payload:
```json
{
  "context": {"position":"UTG","action":"ALL_IN","metric":"EV","position_actions":{},"active_players":2},
  "cells": [{"row":0,"col":0,"hand_key":"AA","value":1.23,"status":"AVAILABLE","display":"+1.23"}],
  "status_message": null
}
```

## Cache Retrieval Rules
1. If matching current record exists, return persisted payload.
2. If record exists but version/signature mismatch, mark stale and treat as cache miss.
3. If payload cannot deserialize, mark failed/corrupt and treat as cache miss.
4. If canonical key match is served across different request contexts, response MUST preserve the requesting context while reusing persisted cells.

Current implementation:
- Store API: `AoFScenarioCacheStore.get_payload()`
- Metadata checks: schema, solver, policy, runtime signatures
- Stale/corrupt handling: marks stale reason and returns deterministic miss
- Provider hydration: request-local context is applied to payload returned from canonical persistent entry

## Fallback Compute Rules
1. On miss/stale/corrupt, execute deterministic compute path.
2. On compute success, write payload and current metadata, then return payload.
3. On compute timeout or failure, return deterministic timeout/error payload; do not write invalid payload as current.

Current implementation:
- Provider orchestrator: `AoFBrowserDataProvider.get_matrix_payload()`
- Write-back API: `AoFScenarioCacheStore.upsert_payload()`
- No-invalid-write guard: skips write-back when any cell status is `TIMEOUT` or `ERROR`

## Offline Precompute Rules
1. Precompute enumerates selected scenario set and writes records idempotently.
2. Completed current entries may be skipped as SKIPPED_CURRENT.
3. Interrupted runs must resume using run metadata/cursor.

Current implementation:
- Runner: `AoFPrecomputeRunner`
- Entrypoint: `python -m hopilot.gto.aof_precompute_cli`
- Run metadata tables: `aof_precompute_run`, `aof_precompute_write_result`

## Status Semantics
- AVAILABLE: valid value for cell
- MISSING: no valid value for scenario/cell
- NO_CONTEST: no contested pot context
- TIMEOUT: compute exceeded budget
- ERROR: deterministic compute failure

## Observability Contract
Events/log dimensions required:
- cache_hit
- cache_miss
- cache_stale
- cache_corrupt
- fallback_compute_started
- fallback_compute_timeout
- fallback_compute_error
- write_back_inserted_or_updated

Additional emitted event:
- write_back_skipped (reason: degraded status)

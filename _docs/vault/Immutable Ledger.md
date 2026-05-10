# Immutable Ledger

## The Rule

Every regime call in `regime_calls` is timestamped and **must never be modified** after creation.

Every validation entry in `validation_log` is timestamped and **must never be modified** after creation.

## Why Immutability

1. **Credibility:** A track record that can be edited is worthless. PMs and recruiters will not trust mutable results.
2. **Auditability:** Every call is preserved with its inputs. You can trace exactly why a call was made.
3. **Brier score integrity:** If you could delete wrong calls, your Brier score would be fraudulent.
4. **Academic rigor:** SSRN reviewers expect immutable data. Mutable data is suspect.

## Enforcement

### Database Triggers
```sql
-- Blocks UPDATE and DELETE on regime_calls
trigger trg_protect_immutable_calls

-- Blocks UPDATE and DELETE on validation_log (for validated rows)
trigger trg_protect_immutable_validation
```

### Application Logic
```python
# writer.py checks for existing row before insert
def write_regime_call(call):
    if get_existing_call(call.date, call.pair):
        return  # skip, already exists
    insert(call)
```

### Manual Override
If absolutely necessary (e.g., schema migration), triggers can be disabled:
```sql
ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls;
-- ... perform migration ...
ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls;
```

**This requires explicit operator action and is logged.**

## What Is Immutable vs Mutable

| Table | Immutable | Mutable |
|-------|-----------|---------|
| `regime_calls` | Yes | No |
| `validation_log` | Yes | No |
| `signals` | No | Upsert on (pair, date) |
| `validation_stats` | No | Upsert on (as_of_date, pair) |
| `desk_open_cards` | No | Regular updates |
| `brief_log` | Yes | No |

## Connections
- **Enforced by:** [[Database]] triggers, [[writer]] logic
- **Protected:** [[Validation Flow]], [[Signal Flow]]
- **Violated by:** Nothing (intentionally)

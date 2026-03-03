# Range Format Contract

**Version**: 1.0
**Date**: 2026-02-27

## Overview

This contract defines the YAML file format for storing poker hand ranges used in GTO analysis. All range files must conform to this schema for compatibility with the RangeManager and GTO solver components.

## YAML Schema

### Required Fields

```yaml
name: string              # Human-readable range name (1-50 characters)
hands: list[string]       # List of poker hand shorthands
```

### Optional Fields

```yaml
description: string       # Optional description (0-200 characters)
tags: list[string]        # Optional tags for categorization
created: datetime         # ISO 8601 timestamp (auto-generated)
modified: datetime        # ISO 8601 timestamp (auto-generated)
```

## Hand Notation Format

### Valid Shorthand Notations

| Type | Format | Examples | Description |
|------|--------|----------|-------------|
| Pocket Pairs | `{rank}{rank}` | `AA`, `KK`, `22` | Two cards of same rank |
| Suited Hands | `{rank1}{rank2}s` | `AKs`, `T9s`, `76s` | Two cards of different suits |
| Offsuit Hands | `{rank1}{rank2}o` | `AKo`, `T9o`, `76o` | Two cards of different suits |
| Specific Cards | `{rank}{suit}` | `As`, `Kh`, `Td` | Individual card specification |

### Rank Order
Ranks must be in descending order for nonsymmetric hands:
- ✅ `AKs` (Ace-King suited)
- ❌ `KAs` (invalid - should be AKs)

### Suit Indicators
- `s`: suited (same suit)
- `o`: offsuit (different suits)
- No indicator: pocket pair

## Complete Example

```yaml
name: "Tournament Premium"
description: "High-value hands for tournament play with bonus considerations"
hands:
  - "AA"
  - "KK"
  - "QQ"
  - "JJ"
  - "TT"
  - "99"
  - "AKs"
  - "AQs"
  - "AJs"
  - "AKo"
  - "AQo"
tags:
  - "premium"
  - "tournament"
  - "broadway"
created: "2026-02-27T11:00:00Z"
modified: "2026-02-27T11:00:00Z"
```

## Validation Rules

### Syntactic Validation
- YAML must parse without errors
- All required fields must be present
- Field types must match schema
- String lengths must be within limits

### Semantic Validation
- All hand notations must be valid poker hands
- No duplicate hands in the same range
- Ranks must exist (A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2)
- Suits must be valid (s, h, d, c) when specified
- Hand order must follow poker conventions

### Business Rules
- Maximum 1000 hands per range (performance constraint)
- Name must be unique within storage directory
- Tags are optional but recommended for organization

## Error Handling

### Validation Errors
When a range file fails validation, the system must:

1. **Identify the specific error** (e.g., "Invalid hand notation: XYZ")
2. **Provide line number** if possible
3. **Suggest correction** when applicable
4. **Fail gracefully** without loading invalid ranges

### Example Error Messages
- `"Invalid hand notation: 'AAs' - pocket pairs don't use suit indicators"`
- `"Hand order invalid: 'KAs' should be 'AKs'"`
- `"Duplicate hand: 'AA' appears twice in range"`
- `"Unknown rank: '1' - valid ranks are A,K,Q,J,T,9,8,7,6,5,4,3,2"`

## File Naming Convention

- Files use `.yaml` extension
- Names should be lowercase with hyphens
- Examples: `premium-pairs.yaml`, `broadway-hands.yaml`, `suited-connectors.yaml`

## Migration and Compatibility

### Version 1.0 Compatibility
- All existing range formats are supported
- Automatic conversion from older formats (if any)
- Backward compatibility maintained

### Future Extensions
- Additional metadata fields may be added
- Hand notation extensions possible
- Schema versioning for breaking changes

## Tooling Support

### Range Editor
- Syntax highlighting for YAML
- Real-time validation
- Hand notation autocompletion
- Preview of expanded range

### Import/Export
- Support for common poker tools' range formats
- Bulk operations for multiple ranges
- Validation during import

## Performance Considerations

- Range files should be < 100KB (reasonable size limit)
- Loading/parsing should complete in < 500ms
- Validation should complete in < 2 seconds for large ranges
- Memory usage should remain < 50MB during operations
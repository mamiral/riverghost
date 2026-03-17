# Data Mapping Contract: Browser to Database Schema

**Contract ID**: DATA_MAPPING_001  
**Purpose**: Defines how browser conceptual entities map to normalized database tables  
**Version**: 1.0  
**Status**: Active  

## Mapping Overview

The browser's data model is conceptual and poker-specific, while the database schema is normalized for simulation storage. This contract defines the transformation rules between these layers.

## Entity Mappings

### PositionContext → Database Query Parameter

**Browser Entity**: PositionContext (UTG, BTN, SB, BB)  
**Database Mapping**: Simulation parameters JSON field  
**Query Pattern**:
```sql
WHERE s.parameters->>'position' = ?
```
**Validation**: Position must exist in simulation metadata  
**Fallback**: If position not found, return empty matrix with MISSING status

### ActionContext → Database Query Parameter

**Browser Entity**: ActionContext (FOLD, ALL_IN)  
**Database Mapping**: Derived from betting patterns in Bets table  
**Query Pattern**:
```sql
WHERE EXISTS (
    SELECT 1 FROM Bets b
    WHERE b.game_state_id = gs.id
    AND b.action_type = CASE WHEN ? = 'ALL_IN' THEN 'raise' ELSE 'fold' END
)
```
**Validation**: Action must match simulation configuration  
**Fallback**: Return INVALID status for mismatched actions

### MetricType → Database Column Selection

**Browser Entity**: MetricType (WIN_LOSE_PROBABILITY, EV, EQUITY, EQR)  
**Database Mapping**: AggregatedMetrics table columns  
**Column Mapping**:
- WIN_LOSE_PROBABILITY → `equity` (standard win probability)
- EV → `jackpot_adjusted_ev` (expected value including jackpots)
- EQUITY → `equity` (same as WIN_LOSE_PROBABILITY)
- EQR → `jackpot_adjusted_ev` (expected value ratio)
**Validation**: Column must exist and contain valid numeric data  
**Fallback**: Return null value with MISSING status

### HandKey → Matrix Cell Coordinates

**Browser Entity**: HandKey (AKs, 72o, etc.)  
**Database Mapping**: MatrixCells.row_index, col_index via hand combination lookup  
**Transformation Logic**:
1. Parse hand key into ranks and suitedness
2. Map ranks to matrix indices (A=0, K=1, Q=2, ..., 2=12)
3. Apply suitedness rules for off-diagonal elements
**Query Pattern**:
```sql
WHERE mc.row_index = ? AND mc.col_index = ?
```
**Validation**: Hand key must resolve to valid matrix coordinates  
**Fallback**: Return INVALID status for malformed hand keys

### StrategyCellMetricValue → Aggregated Query Result

**Browser Entity**: Complete metric value with metadata  
**Database Mapping**: JOIN across multiple tables  
**Query Pattern**:
```sql
SELECT
    am.equity,
    am.jackpot_adjusted_ev,
    am.last_updated,
    am.convergence_status,
    mc.hand_combination,
    s.parameters
FROM AggregatedMetrics am
JOIN MatrixCells mc ON am.cell_id = mc.id
JOIN HandMatrices hm ON mc.matrix_id = hm.id
JOIN Simulations s ON hm.simulation_id = s.id
WHERE [position/action filters apply]
  AND mc.row_index = ? AND mc.col_index = ?
```
**Validation**: All required joins must succeed  
**Fallback**: Return MISSING status if data unavailable

## Transformation Rules

### Status Mapping
- **AVAILABLE**: Data exists and convergence_status = 'CONVERGED'
- **MISSING**: Data does not exist in database
- **INVALID**: Data exists but fails validation (null values, invalid ranges)

### Value Formatting
- Percent metrics: equity * 100 (display as percentage)
- Decimal metrics: jackpot_adjusted_ev (display as decimal)
- Signed decimal: jackpot_adjusted_ev (display with +/- sign)

### Timestamp Handling
- updated_at maps directly from AggregatedMetrics.last_updated
- Use UTC timezone for consistency
- Null timestamps indicate never-updated data

## Data Integrity Guarantees

### Referential Integrity
- All mappings must resolve to existing database records
- Broken foreign keys result in INVALID status
- Missing related records result in MISSING status

### Consistency Rules
- Position/action combinations must be logically consistent
- Metric values must be within valid ranges (-1.0 to 1.0 for probabilities)
- Hand keys must follow poker notation standards

### Concurrency Handling
- Database transactions ensure atomic updates
- Optimistic locking prevents concurrent modification conflicts
- Read operations are isolated from write operations
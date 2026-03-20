# SQLAlchemy ORM Models Contract

**Feature**: 001-cache-removal | **Component**: Database Layer | **Date**: 2026-03-20

## Purpose

Define the SQLAlchemy ORM models that GUI components, tests, and precompute system will use to query and write to the normalized database. This contract ensures consistency across all data access paths.

## SQLAlchemy Models

### Position Model

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(10), unique=True, nullable=False)  # "UTG", "CO", "BTN", "SB", "BB"
    seat_count = Column(Integer, nullable=False)  # 2-6
    button_position = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    actions = relationship("Action", back_populates="position", cascade="all, delete-orphan")
    strategies = relationship("StrategyMatrix", back_populates="position", cascade="all, delete-orphan")
    convergence = relationship("ConvergenceMetrics", back_populates="position", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Position(name='{self.name}', seats={self.seat_count})>"
```

### Action Model

```python
class Action(Base):
    __tablename__ = "actions"
    
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    name = Column(String(50), nullable=False)  # "open_raise", "3bet", "call", etc.
    action_order = Column(Integer, nullable=False)  # Sequence in tree
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    position = relationship("Position", back_populates="actions")
    strategies = relationship("StrategyMatrix", back_populates="action", cascade="all, delete-orphan")
    convergence = relationship("ConvergenceMetrics", back_populates="action", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Action(name='{self.name}', position_id={self.position_id})>"
```

### StrategyMatrix Model

```python
from sqlalchemy import JSON

class StrategyMatrix(Base):
    __tablename__ = "strategy_matrix"
    
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    action_id = Column(Integer, ForeignKey("actions.id"), nullable=False)
    hero_hand = Column(String(4), nullable=False)  # "AsKs"
    villain_hand_pattern = Column(String(255), nullable=False)  # "AA-QQ, AK+"
    matrix_data = Column(JSON, nullable=True)  # Raw matrix if stored as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    position = relationship("Position", back_populates="strategies")
    action = relationship("Action", back_populates="strategies")
    values = relationship("MatrixValue", back_populates="matrix", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<StrategyMatrix(pos={self.position_id}, act={self.action_id}, hand={self.hero_hand})>"
```

### MatrixValue Model

```python
class MatrixValue(Base):
    __tablename__ = "matrix_values"
    
    id = Column(Integer, primary_key=True)
    strategy_matrix_id = Column(Integer, ForeignKey("strategy_matrix.id"), nullable=False)
    hero_hand = Column(String(4), nullable=False)  # "As", "Kh", etc.
    villain_hand = Column(String(4), nullable=False)
    win_probability = Column(Float, nullable=False)  # 0.0-1.0
    action_frequency = Column(Float, nullable=False)  # 0.0-1.0 (call, fold, raise)
    expected_value = Column(Float, nullable=True)  # EV of action
    confidence = Column(Float, default=0.0)  # Convergence confidence (0-1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    matrix = relationship("StrategyMatrix", back_populates="values")
    
    def __repr__(self):
        return f"<MatrixValue({self.hero_hand} vs {self.villain_hand}: win={self.win_probability:.2%})>"
```

### ConvergenceMetrics Model

```python
class ConvergenceMetrics(Base):
    __tablename__ = "convergence_metrics"
    
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    action_id = Column(Integer, ForeignKey("actions.id"), nullable=False)
    iteration = Column(Integer, nullable=False)  # Simulation iteration count
    error = Column(Float, nullable=False)  # Convergence error at this iteration
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    position = relationship("Position", back_populates="convergence")
    action = relationship("Action", back_populates="convergence")
    
    def __repr__(self):
        return f"<ConvergenceMetrics(iter={self.iteration}, error={self.error:.6f})>"
```

## Database Views (SQLAlchemy Hybrid Properties or Raw SQL)

### strategy_matrix_with_context (Optimized for GUI Queries)

```python
# Option: SQLAlchemy query wrapper (reusable)
def get_matrix_with_context(session, position_name, action_name):
    """
    Query matrix with related position and action info.
    Used by GUI to fetch complete payload.
    """
    return session.query(StrategyMatrix).join(Position).join(Action).filter(
        Position.name == position_name,
        Action.name == action_name
    ).first()
```

## Session Management Contract

### GUI Session Initialization

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# At application startup
engine = create_engine(config.database.url, pool_size=5, max_overflow=10)
Session = sessionmaker(bind=engine)

# Per-request or per-component
session = Session()
# Use session for queries
session.close()  # Or use context manager
```

### Context Manager Pattern (Recommended)

```python
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()

# Usage in GUI
async def display_matrix(self, position, action):
    with get_db_session() as session:
        matrix = session.query(StrategyMatrix).filter(...).first()
        return matrix
```

## Query Patterns (Expected Usage)

### Pattern 1: Fetch Matrix for Display

```python
# GUI needs to display 13×13 starting hands grid for a specific position/action
session = get_db_session()
matrix = session.query(StrategyMatrix).filter(
    StrategyMatrix.position.has(Position.name == "CO"),
    StrategyMatrix.action.has(Action.name == "open_raise")
).first()

# Get all cell values
cells = session.query(MatrixValue).filter(
    MatrixValue.strategy_matrix_id == matrix.id
).all()

# Build payload: {hand_combo: {opponent_hand: [freq, color, ...]}}
```

### Pattern 2: Fetch Convergence Data

```python
# GUI needs convergence plot for a position/action
convergence_points = session.query(ConvergenceMetrics).filter(
    ConvergenceMetrics.position.has(Position.name == "CO"),
    ConvergenceMetrics.action.has(Action.name == "open_raise")
).order_by(ConvergenceMetrics.iteration).all()

# Plot: x=iteration, y=error
```

### Pattern 3: Write Strategy Results (Precompute)

```python
# Precompute system writes computed strategies
position = session.query(Position).filter_by(name="CO").first()
action = session.query(Action).filter_by(name="open_raise").first()

matrix = StrategyMatrix(
    position_id=position.id,
    action_id=action.id,
    hero_hand="AsKs",
    villain_hand_pattern="AA-QQ, AK+"
)

for hero_hand, villain_hand, freq, equity in computed_results:
    value = MatrixValue(
        strategy_matrix_id=matrix.id,
        hero_hand=hero_hand,
        villain_hand=villain_hand,
        action_frequency=freq,
        win_probability=equity,
        confidence=convergence_confidence
    )
    session.add(value)

session.add(matrix)
session.commit()
```

## Constraints & Validation

| Constraint | Rule | Enforcement |
|-----------|------|-------------|
| Unique position names | Each position name (UTG, CO, etc.) appears once | Database UNIQUE constraint + application validation |
| Hand format | Hero/villain hands must be 2 char code (e.g., "As", "KhKd") | Column type String(4) + validation in model |
| Probability bounds | Win probability and action frequency must be [0.0, 1.0] | Check constraint in database + application validation |
| FK integrity | Position, Action, StrategyMatrix references must exist | Database foreign key constraints |

## Contract Versioning

**Version**: 1.0  
**Status**: Approved  
**Effective Date**: 2026-03-20

**Changes if model structure needs updates**:
1. Increment version
2. Update data-model.md with new structure
3. Create migration script (SQLAlchemy Alembic)
4. Document in CHANGELOG.md

---

## Implementation Checklist

- [ ] Verify these models exist in codebase or create if missing
- [ ] Ensure models use `Base = declarative_base()` from SQLAlchemy
- [ ] Add indexes on frequently queried columns: `(position_id, action_id)` on StrategyMatrix, `(strategy_matrix_id)` on MatrixValue
- [ ] Test model relationships (cascade deletes, lazy loading behavior)
- [ ] Create data fixtures for testing (sample positions, actions, matrices)
- [ ] Validate session management in GUI startup

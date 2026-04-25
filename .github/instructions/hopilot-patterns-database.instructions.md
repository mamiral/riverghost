---
description: "Use when working with HoPilot database models, schema design, ORM relationships, or persistence layer. Covers SQLAlchemy patterns and data integrity."
applyTo: "**/orm_models.py", "**/database.py", "**/models.py"
---

# HoPilot Database Patterns

## ORM Model Structure
- Use SQLAlchemy declarative base: `Base = declarative_base()`
- All models inherit from `Base`
- Each model represents one database table
- Use `__tablename__` to explicitly define table name

## Primary Keys & IDs
- Use `id = Column(Integer, primary_key=True, autoincrement=True)`
- IDs are always auto-incrementing integers
- Reference via `ForeignKey('table_name.id')`

## Relationships
- Define bidirectional relationships with `back_populates`
- Use `cascade="all, delete-orphan"` for dependent records
- Example:
  ```python
  # Parent side
  children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")
  
  # Child side
  parent = relationship("Parent", back_populates="children")
  ```
- Real example: [Simulation model](prototyping/aof_orm_models.py#L60) with HandMatrix children

## Enums & Constrained Types
- Define enum classes for fixed value sets:
  ```python
  class ActionType(str, enum.Enum):
      FOLD = "fold"
      ALL_IN = "all_in"
  ```
- Use in models: `Column(Enum, nullable=False)`
- Provides type safety and database constraints

## Timestamps
- Track creation: `created_at = Column(DateTime, default=datetime.utcnow, nullable=False)`
- Track updates: `updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)`
- Use `datetime.utcnow` for consistency (not `timezone.utc`)

## Data Types
- Strings: `Column(String(length))`
- Numbers: `Column(Integer)`, `Column(Float)`, `Column(Numeric(precision, scale))`
- JSON data: `Column(JSON)` for flexible config storage
- Booleans: `Column(Boolean)`

## Computed Properties
- Use `@property` for derived values:
  ```python
  @property
  def hand_name(self) -> str:
      """Compute hand name from row/col indices."""
      return f"{rank1}{rank2}{suffix}"
  ```
- Properties don't require database lookups; compute from existing fields

## Debugging & Representation
- Implement `__repr__()` for readable debugging output:
  ```python
  def __repr__(self):
      return f"<Simulation(id={self.id}, name='{self.name}', games={self.total_games})>"
  ```
- Helps with log output and REPL debugging

## Unique Constraints
- Single column: `Column(String, unique=True)`
- Composite constraint: Define in `__table_args__`:
  ```python
  __table_args__ = (
      UniqueConstraint('matrix_id', 'row_index', 'col_index', name='uq_matrix_cell'),
  )
  ```

## Foreign Key Relationships
- Always specify `ForeignKey('table.id')` with table name
- Use `nullable=False` for required relationships
- Define corresponding `relationship()` on opposite side

## Session & Query Patterns
- Sessions manage transaction lifecycle
- Query via session: `session.query(Model).filter(Model.id == 1).first()`
- Commit after mutations: `session.commit()`
- Rollback on error: `session.rollback()`

## Data Integrity
- Cascade deletes propagate to child records
- Foreign keys enforce referential integrity at database level
- Validators on ORM models catch errors before persistence

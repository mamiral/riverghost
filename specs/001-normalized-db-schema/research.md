# Research & Technical Decisions: Normalized Relational Database Schema

**Feature**: 001-normalized-db-schema  
**Date**: 2026-03-15  
**Status**: Complete  

## Research Questions & Findings

### 1. SQLAlchemy ORM Patterns for Poker Analysis
**Decision**: Use SQLAlchemy Core with Declarative Base for model definitions  
**Rationale**: Provides strong typing, relationship management, and migration support. Declarative Base offers clean, readable model definitions suitable for complex poker domain relationships.  
**Alternatives Considered**: 
- SQLAlchemy ORM (declarative) - rejected due to performance overhead for bulk operations
- Raw SQL with sqlite3 - rejected due to lack of abstraction and maintainability  
**Sources**: SQLAlchemy documentation, poker analysis project patterns

### 2. SQLite Performance for Simulation Data
**Decision**: Use WAL mode with connection pooling and batch operations  
**Rationale**: WAL mode enables better concurrency for read-heavy analysis workloads. Connection pooling prevents overhead of frequent connections. Batch inserts critical for simulation data loading.  
**Alternatives Considered**:
- PostgreSQL from start - rejected due to added complexity for local tool
- In-memory SQLite - rejected due to persistence requirements  
**Sources**: SQLite documentation, performance benchmarks for analytical workloads

### 3. Schema Design for Extensible Jackpots
**Decision**: Use JSON column for jackpot metadata with type enumeration  
**Rationale**: Allows flexible jackpot definitions while maintaining queryability. Type field enables indexing and filtering, JSON stores variable metadata like card combinations.  
**Alternatives Considered**:
- Separate tables per jackpot type - rejected due to complexity and migration overhead
- Fixed columns - rejected due to unknown future jackpot variations  
**Sources**: Database design patterns, platform-specific poker features

### 4. Foreign Key Strategy for Performance
**Decision**: Enable foreign keys with cascade deletes, use indexes on FK columns  
**Rationale**: Ensures data integrity while maintaining query performance. Cascade deletes simplify cleanup of related simulation data.  
**Alternatives Considered**:
- Disable FKs for performance - rejected due to data corruption risk
- Application-level integrity - rejected due to complexity and error-proneness  
**Sources**: Database performance best practices, ACID requirements

### 5. Data Types for Poker Domain
**Decision**: Use TEXT for card representations, DECIMAL for monetary values, JSON for flexible data  
**Rationale**: TEXT provides human-readable card formats, DECIMAL ensures precise financial calculations, JSON handles variable jackpot metadata.  
**Alternatives Considered**:
- Custom binary formats - rejected due to complexity and debugging difficulty
- String concatenation - rejected due to parsing overhead  
**Sources**: Poker domain data modeling, financial data best practices

## Technical Approach Validation

### Architecture Fit
- **Separation of Concerns**: Models, database management, and queries separated into distinct modules
- **Testability**: Each component can be unit tested independently
- **Maintainability**: Clear module boundaries and SQLAlchemy abstraction
- **Performance**: Optimized for the expected workload (16 concurrent sims, 10k states each)

### Risk Assessment
- **Low Risk**: SQLAlchemy is mature, SQLite is proven for this scale
- **Medium Risk**: Complex queries may need optimization - mitigated by query planning
- **Low Risk**: Schema evolution - handled by SQLAlchemy migrations

## Implementation Guidelines

### SQLAlchemy Configuration
- Use `create_engine` with `poolclass=StaticPool` for single-threaded application
- Enable `echo=True` in development for query logging
- Configure `future=True` for SQLAlchemy 2.0 compatibility

### Database Schema
- Use `declarative_base()` for model inheritance
- Define relationships with `relationship()` and backrefs
- Use `Column` with appropriate types and constraints
- Implement `__repr__` methods for debugging

### Performance Optimizations
- Use `session.bulk_save_objects()` for batch inserts
- Implement connection pooling for concurrent operations
- Add database indexes on frequently queried columns
- Use `session.query().yield_per()` for large result sets

### Testing Strategy
- Use `pytest` with `pytest-mock` for database mocking
- Create in-memory SQLite databases for unit tests
- Use fixtures for common test data (simulations, game states)
- Test foreign key constraints and cascade deletes
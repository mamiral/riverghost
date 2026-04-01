# Research: Fix Database Schema Remediation

**Date**: April 1, 2026
**Feature**: [specs/001-fix-db-schema-remediation/spec.md](specs/001-fix-db-schema-remediation/spec.md)

## Research Tasks

### RT-001: AllInFoldGTOSolver Database Integration
**Question**: How to modify AllInFoldGTOSolver to write complete game states directly to database tables during Monte Carlo simulations?

**Approach**: 
- Analyze current AllInFoldGTOSolver.analyze_hand_strategy() method
- Research SQLAlchemy session management for bulk inserts
- Investigate transaction handling for simulation batches
- Study performance implications of database writes during computation

**Expected Output**: Technical approach for solver database integration with performance benchmarks

---

### RT-002: Database Session Management
**Question**: What are best practices for database session management during long-running Monte Carlo simulations?

**Approach**:
- Research SQLAlchemy session patterns for bulk operations
- Analyze transaction scopes for simulation iterations
- Study connection pooling and timeout handling
- Investigate rollback strategies for failed simulations

**Expected Output**: Session management strategy with error handling patterns

---

### RT-003: Foreign Key Constraint Enforcement
**Question**: How to ensure foreign key constraints are properly enforced during bulk game state insertions?

**Approach**:
- Research SQLite foreign key constraint behavior
- Analyze insertion order requirements for related tables
- Study constraint violation error handling
- Investigate batch insertion vs individual inserts performance

**Expected Output**: Constraint enforcement strategy with validation rules

---

### RT-004: Integration Testing Patterns
**Question**: What are effective integration testing patterns for validating genuine database operations?

**Approach**:
- Research pytest patterns for database integration tests
- Study test database setup and teardown
- Analyze assertion strategies for real vs fake data validation
- Investigate test data generation for simulation scenarios

**Expected Output**: Testing framework and patterns for database remediation validation

---

### RT-005: Performance Optimization
**Question**: How to optimize database write performance for storing thousands of game states per simulation?

**Approach**:
- Research bulk insert optimizations in SQLAlchemy
- Analyze indexing strategies for query performance
- Study memory usage patterns for large simulations
- Investigate database file size management

**Expected Output**: Performance optimization recommendations with benchmarks

## Research Status

- [ ] RT-001: AllInFoldGTOSolver Database Integration
- [ ] RT-002: Database Session Management  
- [ ] RT-003: Foreign Key Constraint Enforcement
- [ ] RT-004: Integration Testing Patterns
- [ ] RT-005: Performance Optimization

## Findings Summary

[To be populated after research completion]</content>
<parameter name="filePath">c:\Users\U446541\sandbox\riverghost\specs\001-fix-db-schema-remediation\research.md
# Test File Contracts

## Modified Test Files

### test_models.py
**Contract**: Database Model Validation
- MUST test actual database table creation behavior
- MUST validate model relationships and constraints
- MUST NOT contain placeholder `pass` statements

### test_aof_gui_precompute_runner_canonical_dedup.py
**Contract**: Deduplication Logic Testing
- MUST test real deduplication implementation
- MUST validate canonical result selection
- MUST NOT use mocks for core deduplication logic

### test_all_in_fold_gto.py
**Contract**: GTO Threshold Calculation
- MUST test actual GTO threshold finding algorithm
- MUST validate threshold equity calculations
- MUST NOT mock internal calculation methods

### test_db_browser_integration.py
**Contract**: Database Browser Integration
- MUST validate actual database query results
- MUST test integration between browser and database layers
- MUST NOT use meaningless `assert True` statements

### test_incremental_aggregation.py
**Contract**: Incremental Aggregation Logic
- MUST validate actual aggregation computations
- MUST test incremental update behavior
- MUST NOT use meaningless assertions

### test_jackpot_metrics.py
**Contract**: Jackpot Probability Calculations
- MUST handle random win determination properly
- MUST validate statistical properties of jackpot calculations
- MUST NOT expect fixed equity values from random behavior

### test_aof_browser_panel_database_integration.py
**Contract**: Browser Panel Data Integration
- MUST validate actual payload content and structure
- MUST test database-to-UI data transformation
- MUST NOT check only object existence

### test_aggregation_engine_comprehensive.py
**Contract**: Aggregation Engine Functionality
- MUST validate actual aggregation results and content
- MUST test comprehensive aggregation scenarios
- MUST NOT use existence-only checks

### test_browser_database_provider_persistence.py
**Contract**: Data Persistence Behavior
- MUST validate complete persistence workflows
- MUST test data integrity across operations
- MUST NOT have incomplete or missing assertions
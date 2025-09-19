# DigiClinic Test Suite

## Test Structure

```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Integration tests with real components  
├── adhoc/          # Manual/exploratory test scripts
├── conftest.py     # Shared fixtures
└── pytest.ini     # pytest configuration
```

## Running Tests

### All Tests
```bash
cd backend
pytest tests/
```

### Unit Tests Only (Fast)
```bash
pytest -m unit
```

### Integration Tests Only
```bash
pytest -m integration
```

### Ad-hoc Tests
```bash
pytest -m adhoc
```

### Specific Test Files
```bash
pytest tests/unit/test_mock_patient_db.py
pytest tests/integration/test_api_endpoints.py
```

## Manual Testing

### Patient Database Testing
```bash
cd backend
python tests/adhoc/test_patient_lookup.py
```

### Server Endpoint Testing
```bash
cd backend
python tests/adhoc/manual_server_test.py
```

## Test Categories

- **Unit Tests**: Mock dependencies, test individual components
- **Integration Tests**: Use real components, test interactions
- **Ad-hoc Tests**: Manual verification, exploratory testing
# Beehive Test Suite

This directory contains comprehensive tests for the Beehive multi-agent conversation system, implemented as part of issue #60.

## Test Coverage Summary

### ✅ Completed Test Modules

| Module | Test File | Coverage | Status |
|--------|-----------|----------|--------|
| ConversationLogger | `test_conversation_logger.py` | 93% | ✅ Complete |
| ConversationManager | `test_conversation_manager.py` | 97% | ✅ Complete |

### 🚧 Pending Test Modules (Requires Implementation)

| Module | Test File | Status |
|--------|-----------|--------|
| ConversationDaemon | `test_conversation_daemon.py` | ⚠️ Needs module implementation |
| Integration Tests | `test_conversation_integration.py` | ⚠️ Depends on daemon |
| Performance Tests | `test_conversation_performance.py` | ⚠️ Depends on daemon |

## Test Structure

### Unit Tests
- **ConversationLogger**: 44 test cases covering logging, statistics, task generation, and error handling
- **ConversationManager**: 33 test cases covering input processing, CLI enforcement, and monitoring

### Test Infrastructure
- **Database Helpers**: Test database setup, schema creation, and data fixtures
- **Mock Helpers**: Comprehensive mocking for subprocess, tmux, filesystem operations
- **Sample Data**: JSON fixtures for various conversation scenarios

### Test Categories
- **Initialization**: Component setup and configuration
- **Core Functionality**: Primary feature testing
- **Error Handling**: Exception scenarios and edge cases
- **Performance**: Scalability and throughput testing
- **Integration**: Component interaction testing

## Running Tests

### Prerequisites
```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest pytest-cov pytest-mock
```

### Available Test Commands

```bash
# Run all implemented tests
PYTHONPATH=. python -m pytest tests/conversation/test_conversation_logger.py tests/conversation/test_conversation_manager.py -v

# Run with coverage
PYTHONPATH=. python -m pytest tests/conversation/test_conversation_logger.py tests/conversation/test_conversation_manager.py --cov=bees.conversation_logger --cov=bees.conversation_manager --cov-report=term-missing

# Run specific test categories
PYTHONPATH=. python -m pytest tests/conversation/ -k "test_init" -v
PYTHONPATH=. python -m pytest tests/conversation/ -k "error_handling" -v
PYTHONPATH=. python -m pytest tests/conversation/ -k "performance" -v
```

### Test Markers
- `@pytest.mark.performance` - Performance and benchmark tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests

## Test Results

### Current Coverage Achieved: 95% Overall

#### ConversationLogger (93% Coverage)
- **Initialization**: ✅ 100% (4/4 tests)
- **Beekeeper Instructions**: ✅ 100% (5/5 tests)  
- **Bee Conversations**: ✅ 100% (4/4 tests)
- **History & Stats**: ✅ 100% (5/5 tests)
- **CLI Enforcement**: ✅ 100% (2/2 tests)
- **Task Generation**: ✅ 100% (23/23 tests - includes parameterized)
- **Error Handling**: ✅ 100% (3/3 tests)

#### ConversationManager (97% Coverage)
- **Initialization**: ✅ 100% (2/2 tests)
- **Beekeeper Input**: ✅ 100% (10/10 tests)
- **Sender CLI**: ✅ 100% (5/5 tests)
- **Violation Handling**: ✅ 100% (3/3 tests)
- **Communication Health**: ✅ 100% (3/3 tests)
- **Summary**: ✅ 100% (3/3 tests)
- **Monitoring**: ✅ 100% (4/4 tests)

### Missing Coverage Areas
- ConversationLogger: Exception handling paths (lines 48-49, 173-174, 205-206, 343-345)
- ConversationManager: Error logging paths (lines 113-115, 294-296)

## Next Steps

To complete the full test coverage plan from issue #60:

1. **Implement ConversationDaemon module** in `bees/conversation_daemon.py`
2. **Enable daemon tests** by running `test_conversation_daemon.py`
3. **Enable integration tests** by running `test_conversation_integration.py`
4. **Enable performance tests** by running `test_conversation_performance.py`
5. **Target 85%+ coverage** across all conversation system components

## Test Quality Features

### Comprehensive Mocking
- Subprocess operations (tmux, CLI commands)
- Database connections and transactions
- Filesystem operations
- Datetime operations for consistent testing

### Data Fixtures
- Sample conversations in multiple languages (Japanese/English)
- Various message types and priorities
- Error scenarios and edge cases
- Performance testing datasets

### Parametrized Testing
- 20+ parameterized test cases for keyword detection
- Multiple priority classification scenarios
- Various input validation cases

### Error Scenarios
- Database connection failures
- Invalid configurations
- Command timeouts
- Permission errors

This test suite provides a solid foundation for ensuring the reliability and quality of the Beehive conversation system components.
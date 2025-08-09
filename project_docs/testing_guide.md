# Testing Guide - Tennis Analysis System

## Table of Contents
1. [Testing Philosophy](#testing-philosophy)
2. [Types of Tests](#types-of-tests)
3. [Testing Structure](#testing-structure)
4. [Implementation Examples](#implementation-examples)
5. [Testing Best Practices](#testing-best-practices)
6. [Running Tests](#running-tests)
7. [Test Data Management](#test-data-management)
8. [Continuous Integration](#continuous-integration)

## Testing Philosophy

### Why Testing is Critical

**Testing is not optional - it's essential for:**
- **Reliability**: Ensure your code works as expected
- **Confidence**: Make changes without breaking existing functionality
- **Documentation**: Tests show how code should be used
- **Refactoring**: Safely improve code structure
- **Debugging**: Quickly identify what's broken

### ✅ **Recent Frontend Testing Improvements**
- **React Testing Library** - Comprehensive VideoPlayer component tests
- **Jest Configuration** - Coverage thresholds (70% minimum)
- **Development Scripts** - Automated testing, linting, and formatting
- **Best Practices** - See `.cursor/rules/react-frontend.mdc` for React testing patterns

### Our Testing Principles

1. **Test the Business Logic**: Focus on what the code does, not how it does it
2. **Isolate Dependencies**: Mock external services (databases, APIs)
3. **Fast and Reliable**: Tests should run quickly and consistently
4. **Comprehensive Coverage**: Test happy path, edge cases, and error conditions
5. **Maintainable**: Tests should be easy to understand and modify

## Types of Tests

### 1. Unit Tests
**Purpose**: Test individual functions in isolation
**Scope**: Single function or class
**Speed**: Fast (< 1 second each)
**Dependencies**: Mocked

**Example**: Testing video service functions
```python
def test_create_video_record():
    # Test business logic without database
    video = create_video_record(mock_db, "test.mp4", "/path", 1000)
    assert video.filename == "test.mp4"
    assert video.status == "uploaded"
```

### 2. Integration Tests
**Purpose**: Test how components work together
**Scope**: Multiple functions or services
**Speed**: Medium (1-10 seconds each)
**Dependencies**: Real database, mocked external services

**Example**: Testing API endpoints with database
```python
def test_upload_video_endpoint():
    # Test full upload flow
    response = client.post("/api/videos/upload", files={"file": test_file})
    assert response.status_code == 200
    assert response.json()["filename"] == "test.mp4"
```

### 3. End-to-End Tests
**Purpose**: Test complete user workflows
**Scope**: Entire application
**Speed**: Slow (10+ seconds each)
**Dependencies**: Real everything

**Example**: Complete video analysis workflow
```python
def test_video_analysis_workflow():
    # Upload video
    # Wait for processing
    # Check analysis results
    # Verify output files
```

## Testing Structure

### Directory Organization
```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared test fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_video_service.py
│   │   ├── test_video_models.py
│   │   └── test_utils.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_video_routes.py
│   │   └── test_database.py
│   └── e2e/
│       ├── __init__.py
│       └── test_video_workflow.py
```

### Test File Naming Convention
- **Unit tests**: `test_<module_name>.py`
- **Integration tests**: `test_<feature>_integration.py`
- **E2E tests**: `test_<workflow>_e2e.py`

## Implementation Examples

### 1. Unit Test Example

**File**: `backend/tests/unit/test_video_service.py`

```python
import pytest
from unittest.mock import Mock, patch
from app.services.video_service import create_video_record, get_video_by_filename
from app.models.video import Video

class TestVideoService:
    """Unit tests for video service functions."""
    
    def test_create_video_record_success(self):
        """Test successful video record creation."""
        # Arrange
        mock_db = Mock()
        mock_video = Video(
            id=1,
            filename="test.mp4",
            file_path="/path/to/test.mp4",
            file_size=1024000,
            status="uploaded"
        )
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Act
        result = create_video_record(
            db=mock_db,
            filename="test.mp4",
            file_path="/path/to/test.mp4",
            file_size=1024000
        )
        
        # Assert
        assert result.filename == "test.mp4"
        assert result.file_size == 1024000
        assert result.status == "uploaded"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_get_video_by_filename_found(self):
        """Test finding video by filename."""
        # Arrange
        mock_db = Mock()
        expected_video = Video(filename="test.mp4", file_size=1024000)
        mock_db.query.return_value.filter.return_value.first.return_value = expected_video
        
        # Act
        result = get_video_by_filename(mock_db, "test.mp4")
        
        # Assert
        assert result == expected_video
        assert result.filename == "test.mp4"
    
    def test_get_video_by_filename_not_found(self):
        """Test when video is not found."""
        # Arrange
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = get_video_by_filename(mock_db, "nonexistent.mp4")
        
        # Assert
        assert result is None
```

### 2. Integration Test Example

**File**: `backend/tests/integration/test_video_routes.py`

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.models.video import Video

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

class TestVideoRoutes:
    """Integration tests for video API endpoints."""
    
    def setup_method(self):
        """Set up test database."""
        Base.metadata.create_all(bind=engine)
    
    def teardown_method(self):
        """Clean up test database."""
        Base.metadata.drop_all(bind=engine)
    
    def test_list_videos_empty(self):
        """Test listing videos when database is empty."""
        response = client.get("/api/videos/")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_upload_video_success(self):
        """Test successful video upload."""
        # Create test file
        test_file_content = b"fake video content"
        files = {"file": ("test.mp4", test_file_content, "video/mp4")}
        
        response = client.post("/api/videos/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.mp4"
        assert data["file_size"] == len(test_file_content)
        assert data["message"] == "Video uploaded successfully"
    
    def test_upload_video_invalid_format(self):
        """Test upload with unsupported file format."""
        test_file_content = b"fake content"
        files = {"file": ("test.txt", test_file_content, "text/plain")}
        
        response = client.post("/api/videos/upload", files=files)
        
        assert response.status_code == 400
        assert "Unsupported format" in response.json()["detail"]
    
    def test_delete_video_success(self):
        """Test successful video deletion."""
        # First upload a video
        test_file_content = b"fake video content"
        files = {"file": ("test.mp4", test_file_content, "video/mp4")}
        upload_response = client.post("/api/videos/upload", files=files)
        filename = upload_response.json()["filename"]
        
        # Then delete it
        response = client.delete(f"/api/videos/{filename}")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
```

### 3. Test Configuration

**File**: `backend/tests/conftest.py`

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.main import app

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_video_file():
    """Create a sample video file for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    temp_file.write(b"fake video content")
    temp_file.close()
    yield temp_file.name
    Path(temp_file.name).unlink(missing_ok=True)
```

## Testing Best Practices

### 1. Test Structure (AAA Pattern)
```python
def test_function():
    # Arrange - Set up test data and conditions
    mock_db = Mock()
    expected_result = "expected"
    
    # Act - Execute the function being tested
    result = function_under_test(mock_db)
    
    # Assert - Verify the results
    assert result == expected_result
```

### 2. Descriptive Test Names
```python
# Good
def test_create_video_record_with_valid_data_returns_video_object():
    pass

def test_upload_video_with_unsupported_format_returns_400_error():
    pass

# Bad
def test_video():
    pass

def test_upload():
    pass
```

### 3. Test Isolation
```python
def setup_method(self):
    """Each test starts with clean state."""
    Base.metadata.create_all(bind=engine)

def teardown_method(self):
    """Each test cleans up after itself."""
    Base.metadata.drop_all(bind=engine)
```

### 4. Mock External Dependencies
```python
@patch('app.services.video_service.cv2.VideoCapture')
def test_extract_video_metadata(mock_cv2):
    """Test metadata extraction with mocked OpenCV."""
    mock_cap = Mock()
    mock_cap.get.side_effect = [30.0, 3000, 1920, 1080]  # fps, frames, width, height
    mock_cv2.return_value = mock_cap
    
    result = extract_video_metadata(Path("fake_video.mp4"))
    
    assert result["fps"] == 30.0
    assert result["width"] == 1920
```

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_video_service.py

# Run specific test function
pytest tests/unit/test_video_service.py::TestVideoService::test_create_video_record_success

# Run with coverage
pytest --cov=app --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

### Test Configuration
**File**: `pyproject.toml` (add to existing file)
```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Test Data Management

### 1. Test Videos
```python
# Create minimal test videos
def create_test_video(duration_seconds: int = 5) -> Path:
    """Create a minimal test video file."""
    # Implementation would create actual video file
    pass
```

### 2. Database Fixtures
```python
@pytest.fixture
def sample_videos(db_session):
    """Create sample videos in database."""
    videos = []
    for i in range(3):
        video = Video(
            filename=f"test_video_{i}.mp4",
            file_path=f"/path/to/test_video_{i}.mp4",
            file_size=1024000,
            status="uploaded"
        )
        db_session.add(video)
        videos.append(video)
    db_session.commit()
    return videos
```

## Continuous Integration

### GitHub Actions Example
**File**: `.github/workflows/test.yml`
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## Testing Checklist

### Before Writing Code
- [ ] Understand what the code should do
- [ ] Identify edge cases and error conditions
- [ ] Plan test scenarios

### While Writing Code
- [ ] Write tests alongside code (TDD)
- [ ] Test happy path scenarios
- [ ] Test error conditions
- [ ] Test edge cases

### After Writing Code
- [ ] Run all tests
- [ ] Check test coverage
- [ ] Refactor tests if needed
- [ ] Update documentation

### Before Committing
- [ ] All tests pass
- [ ] New code has tests
- [ ] Tests are readable and maintainable
- [ ] Coverage meets standards (>80%)

## Conclusion

**Testing is not a burden - it's an investment in code quality and reliability.**

Good tests:
- ✅ **Save time** by catching bugs early
- ✅ **Enable refactoring** with confidence
- ✅ **Document behavior** for future developers
- ✅ **Improve design** by forcing you to think about usage
- ✅ **Reduce stress** by preventing production issues

**Remember**: The time you spend writing tests is time you won't spend debugging production issues! 
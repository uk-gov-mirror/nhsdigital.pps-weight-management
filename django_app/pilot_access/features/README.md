# BDD Tests for First-Time User Journey

This directory contains Behavior-Driven Development (BDD) tests for the pilot access feature using Django and behave.

## Setup

### 1. Install behave and required dependencies

Behave should already be installed if you're using the `requirements.txt`. If not:

```bash
pip install behave==1.2.6
```

### 2. Create Test Settings File

A Django test settings file has been created at `wm_django/settings/test.py` that:
- Uses SQLite in-memory database instead of PostgreSQL (for fast test execution)
- Disables external service dependencies
- Configures appropriate session serializers for testing

### 3. Directory Structure

The BDD tests are located in:
```
pilot_access/
├── features/
│   ├── environment.py                       # Django test environment setup
│   ├── first_time_user_journey.feature      # Feature file with test scenarios
│   ├── README.md                            # This file
│   └── steps/
│       ├── __init__.py
│       └── landing_steps.py                 # Step definitions for the tests
├── models.py
├── views.py
└── ...
```

## Running the Tests

### Run all BDD tests

```bash
cd django_app
python -m behave pilot_access/features/
```

### Run and output results to a html

```bash
python -m behave pilot_access/features/ -f html-pretty -o test-report.html
```

### Run specific feature file

```bash
python -m behave pilot_access/features/first_time_user_journey.feature
```

### Run with different output formats

```bash
# JSON output
python -m behave pilot_access/features/ --format json --outfile test-results.json

# HTML output (requires install formatter first)
python -m behave pilot_access/features/ --format html --outfile test-results.html

# Verbose output
python -m behave pilot_access/features/ -v

# Plain text output (detailed)
python -m behave pilot_access/features/ -f plain
```

### Run specific scenarios

```bash
# Run a specific scenario by line number
python -m behave pilot_access/features/first_time_user_journey.feature:9

# Run scenarios matching a pattern
python -m behave pilot_access/features/ -n "valid campaign"
```

## Test Scenarios

### 1. First-time user visits landing page with valid campaign code
- **Given**: A valid campaign code exists
- **When**: User visits the landing page with the campaign code
- **Then**: User sees the landing page, disclaimer, and campaign description
- **Status**: ✅ PASSING

### 2. First-time user accepts disclaimer and proceeds
- **Given**: A valid campaign code exists
- **When**: User visits landing page and accepts the disclaimer
- **Then**: User is redirected to contact information page with session data preserved
- **Status**: ✅ PASSING

### 3. Invalid campaign code handling
- **When**: User visits landing page with invalid campaign code
- **Then**: User sees error message and no disclaimer form
- **Status**: ✅ PASSING

### 4. Expired campaign code handling
- **Given**: An expired campaign code exists
- **When**: User visits landing page with expired code
- **Then**: User sees error message about invalid campaign code
- **Status**: ✅ PASSING

### 5. Landing page without campaign code
- **When**: User visits landing page without campaign code
- **Then**: User sees magic link login option
- **Status**: ✅ PASSING

### 6. Complete first-time user journey
- Full flow from landing page acceptance through to session state verification
- **Status**: ✅ PASSING

## Test Results Summary

```
✅ 1 feature passed
✅ 6 scenarios passed
✅ 29 steps passed
⏱️  Total runtime: ~0.3 seconds
```

## How the Tests Work

### Environment Setup (`environment.py`)

The test environment is automatically configured:
- **before_all()**: Sets up Django with test settings, uses SQLite database
- **before_scenario()**: Runs migrations, clears cache, initializes test client
- **after_scenario()**: Flushes database to ensure clean state between tests

### Step Definitions (`landing_steps.py`)

Steps are organized by type:

#### Given Steps (Setup)
- `I have a valid campaign code` - Creates a campaign valid for today
- `I have an expired campaign code` - Creates a campaign that expired yesterday

#### When Steps (Actions)
- `I visit the landing page with the campaign code` - GET request with campaign code
- `I visit the landing page with an invalid campaign code` - GET with fake code
- `I visit the landing page without a campaign code` - GET without parameters
- `I accept the disclaimer` - POST request to accept disclaimer form

#### Then Steps (Assertions)
- `I should see the landing page` - Verifies correct template/status code
- `I should see the campaign disclaimer` - Checks for disclaimer content
- `I should see the campaign description` - Verifies campaign comment is visible
- `I should be redirected to the contact information page` - Verifies redirect
- `my campaign code should be saved in the session` - Checks session data
- `I should see an error message about invalid campaign code` - Error verification
- `I should not see the campaign disclaimer` - Verifies absence of form
- `I should see the magic link login option` - Checks for OTP login alternative
- `the session should contain the campaign code` - Session verification
- `the session should have disclaimer accepted flag set` - Flag verification

## Test Database Configuration

Tests use an in-memory SQLite database for:
- ✅ Fast execution (no network/disk I/O)
- ✅ Automatic cleanup between scenarios
- ✅ Complete isolation from production database
- ✅ Easy local development without PostgreSQL

The test database is defined in [wm_django/settings/test.py](../wm_django/settings/test.py).

## Troubleshooting

### Tests fail with "ModuleNotFoundError"
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Tests fail with "ImproperlyConfigured"
Verify that the test settings file is being used by checking the environment.py uses `wm_django.settings.test`.

### Template not found errors
Ensure the Jinja2 templates directory exists at `templates/pilot_access/landing.jinja`.

### Session not persisting
The Django test client automatically maintains session state. This is working correctly in the tests.

## Dependencies

- `behave` - BDD framework for Python
- `django.test.Client` - Django test client
- `django.urls.reverse` - URL reversing for routing
- `pilot_access.models.Campaign` - Campaign model

## Extending the Tests

To add more scenarios:

1. Add a new scenario in `first_time_user_journey.feature`:
```gherkin
Scenario: New user scenario name
  Given/When/Then statements
```

2. Add corresponding step definitions in `landing_steps.py`:
```python
@given('step description')
def step_function(context):
    # Implementation
```

3. Run tests to verify:
```bash
python -m behave pilot_access/features/ -f plain
```

## CI/CD Integration

Add to your CI/CD pipeline (e.g., GitHub Actions):

```yaml
- name: Run BDD Tests
  run: |
    cd django_app
    python -m behave pilot_access/features/ --format json --outfile test-results.json
    
- name: Upload Test Results
  uses: actions/upload-artifact@v2
  with:
    name: bdd-test-results
    path: django_app/test-results.json
```

## Common Commands

```bash
# Run tests with no capture (see print statements)
python -m behave pilot_access/features/ --no-capture

# Run tests in parallel (if supported)
python -m behave pilot_access/features/ --jobs 4

# Run specific scenario by name
python -m behave pilot_access/features/ -n "First-time user accepts"

# Generate HTML report
python -m behave pilot_access/features/ -f html -o report.html

# List all available steps
python -m behave pilot_access/features/ --dry-run --no-capture
```

## Notes

- Tests run against an in-memory database that is fresh for each scenario
- Each step has access to `context` object which persists data across steps
- Campaign codes are auto-generated 6-digit numeric strings
- Session state is properly maintained across test requests
- All tests complete in under 1 second total runtime

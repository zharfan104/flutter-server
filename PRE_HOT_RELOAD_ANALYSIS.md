# Pre-Hot-Reload Analysis and Error Fixing

## Overview

The Flutter Server now includes a pre-hot-reload analysis and error fixing mechanism that runs **before** attempting hot reload. This ensures that only clean, compilable code is hot reloaded, reducing failed reload attempts and improving the development experience.

## How It Works

### Two-Stage Error Handling

1. **Pre-Hot-Reload Stage** (NEW)
   - Runs `dart analyze` with `errors_only=true` (skips warnings/info)
   - Fixes compilation errors before hot reload
   - Quick fixes with max 3 attempts (configurable)
   - Prevents hot reload failures due to syntax/compilation errors

2. **Post-Hot-Reload Stage** (EXISTING)
   - Comprehensive error recovery after hot reload
   - Handles runtime errors and complex issues
   - Full analysis including warnings
   - Up to 16 fix attempts (configurable)

### Pipeline Flow

```
1. Code Modification (AI generates files)
2. Pre-Hot-Reload Analysis ← NEW
3. Pre-Hot-Reload Error Fixing (if needed) ← NEW
4. Hot Reload (with cleaner code)
5. Post-Hot-Reload Analysis
6. Post-Hot-Reload Error Fixing (if needed)
7. Final Hot Reload
```

## Configuration

Configure in `code_modification/build_pipeline.py`:

```python
self.config = {
    # Existing configurations
    "max_fix_attempts": 16,      # Post-hot-reload fixing
    "enable_hot_reload": True,
    "run_final_analysis": True,
    "auto_fix_errors": True,
    
    # Pre-hot-reload configurations (NEW)
    "pre_hot_reload_check": True,    # Enable/disable pre-hot-reload analysis
    "pre_fix_max_attempts": 3,       # Quick fix attempts before hot reload
    "pre_fix_errors_only": True      # Only fix errors, skip warnings/info
}
```

### Configuration Examples

#### Default (both stages enabled):
```python
"pre_hot_reload_check": True,
"auto_fix_errors": True,
```

#### Only pre-hot-reload checking:
```python
"pre_hot_reload_check": True,
"auto_fix_errors": False,
```

#### Only post-hot-reload recovery (legacy behavior):
```python
"pre_hot_reload_check": False,
"auto_fix_errors": True,
```

## Benefits

1. **Reduced Hot Reload Failures**: Compilation errors are caught and fixed before hot reload
2. **Faster Feedback**: Quick pre-checks (3 attempts) catch obvious errors early
3. **Better UX**: Users see working code immediately instead of compilation errors
4. **Two Layers of Protection**: Pre-check for syntax errors, post-check for runtime issues
5. **Configurable**: Can be disabled if not needed

## Implementation Details

### Modified Files

1. **`code_modification/build_pipeline.py`**
   - Added pre-hot-reload analysis step
   - Added `_execute_pre_hot_reload_fixing()` method
   - Updated configuration options

2. **`code_modification/dart_analysis.py`**
   - Added `errors_only` parameter to `run_analysis()`
   - Filters out warnings/info when `errors_only=True`

3. **`code_modification/iterative_fixer.py`**
   - Added `errors_only` parameter to `fix_all_errors()`
   - Passes parameter through to analysis service

### Status Messages

Users will see these new status messages:

- "🔍 Checking for compilation errors before hot reload..."
- "⚠️ Found X compilation errors, fixing before hot reload..."
- "🔧 Fixing compilation errors before hot reload..."
- "✅ Pre-hot-reload errors fixed successfully!"
- "✅ No compilation errors found, proceeding to hot reload"

## Testing

Run the test suite to verify functionality:

```bash
poetry run python test_pre_hot_reload_analysis.py
```

The test suite validates:
- Analysis runs before hot reload when enabled
- Errors are fixed with reduced attempts (3 vs 16)
- Only errors are fixed (warnings/info skipped)
- Feature can be disabled via configuration
- Post-hot-reload recovery still works as fallback

## Example Workflow

1. User requests: "Add a login button"
2. AI generates code with a typo: `onPresed` instead of `onPressed`
3. Pre-hot-reload analysis detects the error
4. Pre-hot-reload fixer corrects to `onPressed`
5. Hot reload succeeds with clean code
6. User sees working button immediately

Without pre-hot-reload analysis, the hot reload would fail, trigger post-hot-reload recovery, and take longer to show working code.
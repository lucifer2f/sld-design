@echo off
REM Cleanup Script for Unused ML Training Artifacts
REM This script removes old fine-tuned models and training data that are no longer used

echo ========================================
echo  SLD Design - ML Artifacts Cleanup
echo ========================================
echo.
echo This will remove the following unused directories:
echo   - models\electrical_finetuned_* (3 directories, ~320MB)
echo   - training_data (2 files)
echo   - checkpoints (3 subdirectories)
echo   - continuous_learning_data
echo.
echo These artifacts are from an earlier ML training implementation
echo and are NOT currently used by the system.
echo.
echo The system now uses:
echo   - LLM APIs (Google Gemini/OpenAI) for AI features
echo   - Base embedding model 'all-MiniLM-L6-v2' for vector search
echo.

set /p CONFIRM="Do you want to proceed? (yes/no): "
if /i not "%CONFIRM%"=="yes" (
    echo Cleanup cancelled.
    exit /b 0
)

echo.
echo Creating backup archive first...
mkdir archive 2>nul

REM Backup before deletion (optional)
set /p BACKUP="Do you want to create a backup before deletion? (yes/no): "
if /i "%BACKUP%"=="yes" (
    echo Backing up to archive directory...
    xcopy /E /I /Y "models\electrical_finetuned_20251107_162346" "archive\models\electrical_finetuned_20251107_162346"
    xcopy /E /I /Y "models\electrical_finetuned_20251107_163310" "archive\models\electrical_finetuned_20251107_163310"
    xcopy /E /I /Y "models\electrical_finetuned_20251107_164343" "archive\models\electrical_finetuned_20251107_164343"
    xcopy /E /I /Y "training_data" "archive\training_data"
    xcopy /E /I /Y "checkpoints" "archive\checkpoints"
    xcopy /E /I /Y "continuous_learning_data" "archive\continuous_learning_data"
    copy "models\training_report.json" "archive\" 2>nul
    copy "models\training_report_readable.txt" "archive\" 2>nul
    echo Backup complete!
    echo.
)

echo Starting cleanup...
echo.

REM Remove fine-tuned model directories
echo Removing fine-tuned models...
rmdir /S /Q "models\electrical_finetuned_20251107_162346" 2>nul
rmdir /S /Q "models\electrical_finetuned_20251107_163310" 2>nul
rmdir /S /Q "models\electrical_finetuned_20251107_164343" 2>nul
del /Q "models\training_report.json" 2>nul
del /Q "models\training_report_readable.txt" 2>nul

REM Remove training data
echo Removing training data...
rmdir /S /Q "training_data" 2>nul

REM Remove checkpoints
echo Removing checkpoints...
rmdir /S /Q "checkpoints" 2>nul

REM Remove continuous learning data
echo Removing continuous learning data...
rmdir /S /Q "continuous_learning_data" 2>nul

REM Remove validation results if related to old training
echo Removing old validation results...
rmdir /S /Q "validation_results" 2>nul

echo.
echo ========================================
echo  Cleanup Complete!
echo ========================================
echo.
echo Removed:
echo   [x] 3 fine-tuned model directories (~320MB)
echo   [x] Training data directory
echo   [x] Checkpoints directory
echo   [x] Continuous learning data
echo   [x] Old validation results
echo.
if /i "%BACKUP%"=="yes" (
    echo Backup saved in: archive\
    echo.
)
echo The system will continue to work normally using:
echo   - LLM APIs for AI-powered extraction
echo   - Base embedding model for vector search
echo.
echo You can now proceed with normal operations.
echo.
pause

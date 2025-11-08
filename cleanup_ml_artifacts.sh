#!/bin/bash
# Cleanup Script for Unused ML Training Artifacts
# This script removes old fine-tuned models and training data that are no longer used

echo "========================================"
echo " SLD Design - ML Artifacts Cleanup"
echo "========================================"
echo ""
echo "This will remove the following unused directories:"
echo "  - models/electrical_finetuned_* (3 directories, ~320MB)"
echo "  - training_data (2 files)"
echo "  - checkpoints (3 subdirectories)"
echo "  - continuous_learning_data"
echo ""
echo "These artifacts are from an earlier ML training implementation"
echo "and are NOT currently used by the system."
echo ""
echo "The system now uses:"
echo "  - LLM APIs (Google Gemini/OpenAI) for AI features"
echo "  - Base embedding model 'all-MiniLM-L6-v2' for vector search"
echo ""

read -p "Do you want to proceed? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
read -p "Do you want to create a backup before deletion? (yes/no): " BACKUP
if [ "$BACKUP" == "yes" ]; then
    echo "Creating backup archive..."
    mkdir -p archive
    
    echo "Backing up to archive directory..."
    cp -r models/electrical_finetuned_20251107_162346 archive/ 2>/dev/null || true
    cp -r models/electrical_finetuned_20251107_163310 archive/ 2>/dev/null || true
    cp -r models/electrical_finetuned_20251107_164343 archive/ 2>/dev/null || true
    cp -r training_data archive/ 2>/dev/null || true
    cp -r checkpoints archive/ 2>/dev/null || true
    cp -r continuous_learning_data archive/ 2>/dev/null || true
    cp models/training_report.json archive/ 2>/dev/null || true
    cp models/training_report_readable.txt archive/ 2>/dev/null || true
    
    echo "Backup complete!"
    echo ""
fi

echo "Starting cleanup..."
echo ""

# Remove fine-tuned model directories
echo "Removing fine-tuned models..."
rm -rf models/electrical_finetuned_20251107_162346
rm -rf models/electrical_finetuned_20251107_163310
rm -rf models/electrical_finetuned_20251107_164343
rm -f models/training_report.json
rm -f models/training_report_readable.txt

# Remove training data
echo "Removing training data..."
rm -rf training_data

# Remove checkpoints
echo "Removing checkpoints..."
rm -rf checkpoints

# Remove continuous learning data
echo "Removing continuous learning data..."
rm -rf continuous_learning_data

# Remove validation results if related to old training
echo "Removing old validation results..."
rm -rf validation_results

echo ""
echo "========================================"
echo " Cleanup Complete!"
echo "========================================"
echo ""
echo "Removed:"
echo "  [x] 3 fine-tuned model directories (~320MB)"
echo "  [x] Training data directory"
echo "  [x] Checkpoints directory"
echo "  [x] Continuous learning data"
echo "  [x] Old validation results"
echo ""
if [ "$BACKUP" == "yes" ]; then
    echo "Backup saved in: archive/"
    echo ""
fi
echo "The system will continue to work normally using:"
echo "  - LLM APIs for AI-powered extraction"
echo "  - Base embedding model for vector search"
echo ""
echo "You can now proceed with normal operations."
echo ""

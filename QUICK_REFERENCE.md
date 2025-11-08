# 🚀 Quick Reference - SLD Design System

## ⚡ Start the Application

```bash
# Windows - Double-click this file:
START_APP.bat

# Or run manually:
streamlit run src/app.py
```

**Access:** http://localhost:8501

---

## 📋 System Status

| Component | Status | Notes |
|-----------|--------|-------|
| LLM Integration | ✅ WORKING | Google Gemini configured |
| Vector Database | ✅ WORKING | ChromaDB with 6 collections |
| AI Excel Extractor | ✅ WORKING | Pattern + LLM powered |
| Calculation Engines | ✅ WORKING | All 4 engines operational |
| Manual Workflows | ✅ WORKING | All forms functional |
| All UI Pages | ✅ WORKING | No features removed |

---

## 🎯 Quick Tasks

### Create New Project
1. Click **🏠 Dashboard**
2. Click "🆕 New Project"
3. Fill project details
4. Start adding equipment

### AI Excel Extraction
1. Go to **🤖 AI Tools**
2. Upload Excel file
3. Click "🚀 Start AI Extraction"
4. Review extracted data
5. Make corrections if needed
6. Integrate with project

### Add Equipment Manually
1. Go to **🔧 Equipment Config**
2. Choose equipment type (Load/Bus/Cable/etc.)
3. Fill in specifications
4. Click "Add to Project"

### Run Calculations
1. Go to **📊 Design & Analysis**
2. Select loads to calculate
3. Click "Run Calculations"
4. View results
5. Generate reports

---

## 🔧 Troubleshooting

### App Won't Start
```bash
# Check Python version (need 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt
```

### LLM Features Not Working
```bash
# Check .env file has API key
# Should have: GOOGLE_API_KEY=your_key_here
```

### Import Errors
```bash
pip install -r requirements.txt --force-reinstall
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `START_APP.bat` | Quick start script |
| `src/app.py` | Main application |
| `.env` | API keys (don't share!) |
| `requirements.txt` | Dependencies |
| `README.md` | Full documentation |

---

## 🎓 Documentation

| Document | When to Use |
|----------|-------------|
| [README.md](README.md) | Getting started |
| [SYSTEM_AUDIT_REPORT.md](SYSTEM_AUDIT_REPORT.md) | Detailed system info |
| [VERIFICATION_COMPLETE.md](VERIFICATION_COMPLETE.md) | Verification status |
| [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) | What was done |

---

## 💡 Tips

- **Save often** - Auto-save is enabled but manual save recommended
- **Export backups** - Use JSON export for backups
- **Check calculations** - Review results before finalizing
- **Use AI extraction** - Saves time on large Excel files

---

## ✅ All Systems Ready

```
✅ Dependencies: Installed
✅ API Keys: Configured  
✅ Vector DB: Operational
✅ Integrations: Working
✅ Features: All Active
```

**👉 Ready to use! Run START_APP.bat**

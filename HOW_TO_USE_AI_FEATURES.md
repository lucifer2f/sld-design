# How to Use AI Features in EDA System

## Quick Start

### Access AI Tools
1. Click **"🤖 AI Tools"** in the left sidebar
2. You'll see 4 tabs: Excel Import, Equipment Suggestions, Design Insights, and Analytics

---

## AI Equipment Suggestions ⚙️

### What It Does
Automatically recommends the best cable sizes, breaker ratings, and starter equipment for each load in your design.

### How to Use

**Step 1: Load a Project**
- Option A: Import Excel data (use the "📥 Excel Import" tab)
- Option B: Create a new project (go to "⚙️ Project Setup")
- Option C: Load the sample project (click "📂 Try Sample Project" on Dashboard)

**Step 2: Add Loads (if needed)**
- Go to "🔧 Equipment Config" section
- Add loads to your project with their power ratings, voltage, and type

**Step 3: View Equipment Suggestions**
- Click the **"⚙️ Equipment Suggestions"** tab
- The system will automatically run calculations
- Expand each load to see recommendations:
  - **Cable Recommendation**: Size (mm²), type, material
  - **Breaker Recommendation**: Rating (A), type, curve
  - **Starter Recommendation**: Starter type (if applicable for motor loads)

### Example Output
```
📌 L1: Main Pump Motor
├── 🔌 Cable Recommendation
│   ├── Size: 35 mm²
│   ├── Type: Multi-Core
│   ├── Material: Copper
│   └── Reason: Ampacity 127A exceeds required 87.5A
├── ⚡ Breaker Recommendation
│   ├── Rating: 100 A
│   ├── Type: MCCB
│   ├── Curve: D
│   └── Reason: Protects load current 87.5A with appropriate margin
└── 🔧 Starter Recommendation
    ├── Type: Soft Starter or VFD
    └── Reason: Motor load 11.0kW requires starting equipment
```

### Tips
- **First load is expanded by default** - see it immediately without clicking
- **Reasoning shown** - understand why each recommendation was made
- **Automatic calculations** - no manual calculation step needed
- **All loads shown** - scroll to see recommendations for all loads

---

## AI Design Insights 💡

### What It Does
Analyzes your entire electrical design and provides:
- Design quality score (0-100)
- Issues and safety concerns
- Recommendations for improvements
- Standards compliance check

### How to Use

**Step 1: Load a Project with Loads**
- Same as Equipment Suggestions - ensure you have a project with loads

**Step 2: View Design Insights**
- Click the **"💡 Design Insights"** tab
- System automatically runs calculations if needed
- View the design analysis dashboard

### Understanding the Results

**Design Score (0-100)**
- 🟢 **80-100**: Excellent - your design is well optimized
- 🟡 **60-79**: Good - some improvements recommended
- 🔴 **0-59**: Poor - significant issues detected

**Issues Found ❌**
- Critical validation problems that must be addressed
- Example: "Cable undersized for load current"

**Safety Concerns ⚠️**
- Safety-critical issues
- Example: "Breaker rating below minimum protection requirement"

**Recommendations ✅**
- Suggestions for improvement
- Example: "Consider load balancing across phases"

**Warnings ℹ️**
- Non-critical alerts
- Example: "Cable utilization is low, consider smaller size"

**Standards Compliance**
- Checks against applicable standards (IEC, NEC, etc.)
- ✅ = Compliant
- ❌ = Non-compliant

### Example Output
```
Design Score: 82/100 🟢

Issues Found (0)
- None found

Safety Concerns (0)
- None found

Recommendations (2)
✅ Consider load balancing across phases for more efficient use
✅ Verify cable routes for mechanical protection

Standards Compliance
┌─────────────────────┬──────────┐
│ Aspect              │ Compliant│
├─────────────────────┼──────────┤
│ Cable Sizing        │    ✅    │
│ Breaker Protection  │    ✅    │
│ Voltage Drop        │    ✅    │
│ Phase Balance       │    ❌    │
└─────────────────────┴──────────┘
```

### Tips
- **Score interpretation**: 80+ is good for most designs
- **Address red items first**: Safety concerns need immediate attention
- **Use recommendations**: Follow suggestions to improve your design
- **Standards compliance**: Ensure all critical aspects are compliant

---

## AI Analytics 📊

### What It Does
Visualizes your system with charts and graphs showing:
- Load power distribution
- Voltage level breakdown
- System statistics

### How to Use

1. Click the **"📊 Analytics"** tab
2. View power distribution bar chart
3. View voltage distribution pie chart
4. Use these to identify system imbalances or issues

---

## AI Excel Import 📥

### What It Does
Extract electrical design data from Excel spreadsheets automatically.

### How to Use

1. Click the **"📥 Excel Import"** tab
2. Click "Choose Excel file" and select your file
3. Enter a project name
4. Click "🚀 Extract with AI"
5. System extracts loads, cables, transformers, buses automatically
6. Navigate to other tabs to see equipment suggestions and design insights

### Excel Format Requirements
- Headers in first row
- Standard electrical engineering terminology
- Valid numerical values
- Unique equipment IDs
- Realistic voltage and power values

### Example Excel Columns
```
Load ID | Load Name      | Power (kW) | Voltage (V) | Current (A) | Type
L1      | Main Pump      | 11         | 380         | 22.4        | Motor
L2      | Lighting Panel | 5          | 230         | 21.7        | Lighting
```

---

## Troubleshooting

### "AI Equipment Suggester not initialized"
- Check that dependencies are installed
- Verify llm_multimodal_processor and vector_database_manager are available
- Restart the application

### No equipment suggestions appearing
- Ensure project has at least one load
- Click on Equipment Suggestions tab to trigger analysis
- Check that load data is complete (power, voltage, type)

### Design Score is very low
- Review "Issues Found" and "Safety Concerns" sections
- Address critical safety issues first
- Check standards compliance indicators
- Review recommendations

### Excel import fails
- Verify file format is .xlsx or .xls
- Check headers are in first row
- Ensure no merged cells
- Verify equipment IDs are unique
- Use standard electrical terminology

---

## Keyboard Shortcuts

- **Sidebar Navigation**: Click menu items on the left
- **Tab Navigation**: Click tabs to switch between sections
- **Expandable Sections**: Click to expand/collapse load details
- **Buttons**: Click to trigger actions (Extract, Analyze, etc.)

---

## Tips & Best Practices

1. **Start with Excel Import** if you have spreadsheets
2. **Review Equipment Suggestions** before finalizing your design
3. **Check Design Insights** to ensure compliance
4. **Fix critical issues** (red ❌) before proceeding
5. **Monitor Design Score** as you make changes
6. **Use Analytics** to visualize system balance
7. **Export Results** when design is complete

---

## FAQ

**Q: Can AI recommendations override my manual selections?**
A: No, these are suggestions. You can always manually edit equipment in the Equipment Config section.

**Q: How often are calculations updated?**
A: Calculations run automatically whenever you visit Equipment Suggestions or Design Insights tabs after making changes.

**Q: Why is my design score low?**
A: Click on "Design Insights" tab to see specific issues and recommendations.

**Q: Can I export the AI analysis?**
A: Yes, go to the "📤 Export" tab in Design & Analysis to export reports including AI analysis.

**Q: What if AI features are unavailable?**
A: The app will show warnings. You can still use manual equipment selection in Equipment Config.

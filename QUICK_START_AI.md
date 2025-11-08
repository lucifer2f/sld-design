# Quick Start: AI Features

## What's New?

The system now has **AI-powered design analysis and equipment recommendations** integrated throughout the Design & Analysis tab.

---

## Using AI Features in the UI

### 1. Design Score & Metrics
When you go to **Design & Analysis → Load Analysis**, you'll see:

```
🟢 Design Score: 85/100
Issues Found: 2
Recommendations: 5
```

- **Green (80-100)**: Good design
- **Yellow (60-79)**: Needs improvements
- **Red (0-59)**: Critical issues

---

### 2. Equipment Recommendations Per Load

Each load shows expandable sections with:

#### 🔌 Cable Recommendation
- **Size**: e.g., "25 mm²"
- **Type**: Multi-Core, Single Core, etc.
- **Material**: Copper or Aluminum
- **Reasoning**: Why this size was chosen

#### ⚡ Breaker Recommendation
- **Rating**: e.g., "100 A"
- **Type**: MCB, MCCB, or ACB
- **Curve**: B, C, D, K, Z (load-dependent)
- **Reasoning**: Why this breaker

#### 🔧 Starter (if needed)
For motors over 3 kW:
- Recommended starter type
- Why it's needed

---

### 3. Design Insights
In **Design & Analysis → Charts & Reports**, you get:

#### 📊 Visualizations
- Power distribution bar chart
- Voltage distribution pie chart
- Hover over for details

#### 🤖 AI Insights
- **Issues Found**: Specific problems with solutions
- **Safety Concerns**: Critical issues
- **Recommendations**: Improvement suggestions
- **Warnings**: Non-critical alerts
- **Standards Compliance**: ✅/❌ for each aspect

---

## How Equipment Sizing Works

### Cable Sizing
1. Load current × 1.25 (safety margin)
2. Ampacity lookup (with derating)
3. Temperature adjustment
4. Next standard size selected

**Example**: 60A load → 75A required → 25mm² selected

### Breaker Selection
1. Load current × 1.25 to 1.5
2. Find nearest standard rating
3. Select type (MCB/MCCB/ACB) by current
4. Choose curve based on load type

**Example**: 60A load → 100A breaker, curve C

### Transformer Sizing
1. Calculate KVA = √(P² + Q²)
2. Apply 20% safety margin
3. Select next standard rating

**Example**: 100kW + 30kVAR → 135kVA → 150kVA transformer

---

## Troubleshooting

### AI Features Not Showing?
✅ **Solution**: Add loads to project first
- Go to 🔧 Equipment Config
- Add at least one load
- Return to 📊 Design & Analysis

### No Recommendations?
✅ **Solution**: LLM might be unavailable
- System falls back to rule-based sizing
- Equipment suggestions still work
- Manual entry still available

### Design Score Too Low?
✅ **Solution**: Check and fix issues
- Review listed issues
- Add breakers to loads
- Configure grounding
- Verify voltage ratings

---

## Common Scenarios

### Scenario 1: New Project
```
1. Upload Excel or add loads manually
2. View Design & Analysis tab
3. Check Design Score
4. Review equipment recommendations
5. Accept or adjust suggestions
6. Run calculations
```

### Scenario 2: Validating Design
```
1. Open existing project
2. Go to Design & Analysis
3. Review Design Score
4. Check Issues and Recommendations
5. Fix any problems
6. Rerun to verify improvements
```

### Scenario 3: Quick Equipment Setup
```
1. Add a load (e.g., 50kW motor)
2. Open Load Analysis
3. Find equipment recommendations
4. Copy-paste values
5. Equipment is configured
```

---

## Tips & Tricks

### Maximize Design Score
1. **Add Breakers**: System scores breaker presence
2. **Use Common Voltages**: 480V, 240V, 208V are standards
3. **Verify Power Factors**: Typical range 0.8-0.95
4. **Check Safety**: Ensure all loads have protection

### Get Better Equipment Suggestions
1. **Set Load Types**: Motor, Lighting, Heating helps selection
2. **Provide Voltage**: Different voltages get different recommendations
3. **Specify Installation**: Conduit, cable tray, underground affect cable sizing
4. **Set Duty Cycle**: Continuous vs intermittent changes breaker type

### Use Insights for Optimization
1. **Review Recommendations**: AI suggests cost/performance improvements
2. **Fix Safety Concerns**: Red items must be addressed
3. **Address Warnings**: Yellow items should be reviewed
4. **Verify Compliance**: Check ✅/❌ standards table

---

## Design Analysis Details

### What Gets Analyzed
- ✅ Load validity (positive values, realistic ranges)
- ✅ Voltage standards (common electrical voltages)
- ✅ Power factor ranges (0.6-1.0)
- ✅ Cable ampacity vs load current
- ✅ Voltage drop (< 3% preferred)
- ✅ Breaker coordination (cascade and selective)
- ✅ Safety standards compliance
- ✅ Design patterns (similar designs)
- ✅ Component specifications (standards DB)

### What Doesn't Get Analyzed
- Cost calculations (see Export for financials)
- Installation logistics (outside scope)
- Grounding design (basic check only)
- Thermal analysis (not available)
- Reliability prediction (future feature)

---

## Equipment Recommendation Confidence

**High Confidence (85-90%)**
- Ampacity-based sizing
- Standard breaker selection
- Basic load calculations

**Medium Confidence (70-75%)**
- LLM-based suggestions
- Pattern matching from similar designs
- Multi-parameter recommendations

**Low Confidence (50-60%)**
- LLM suggestions without data
- Vector DB results when few matches
- Complex interactions

---

## Standards Used

### Cable Sizing (IEC 60364)
- Standard sizes: 1 to 300 mm²
- Ampacity tables: For XLPE insulation
- Derating factors: Installation method & temperature

### Breaker Selection (IEC 60898)
- Standard ratings: 6A to 320A
- Breaker curves: B, C, D, K, Z
- Coordination: Cascade and selective

### Transformers (IEC 60076)
- Standard KVA: 5 to 500 kVA
- Connection types: Delta-Wye, Delta-Delta
- Cooling: Oil-immersed or Dry-type

---

## Performance Notes

### Speed
- **Quick Configuration**: < 1 second
- **Design Analysis**: 2-5 seconds
- **Full UI Load**: 5-10 seconds

### Limitations
- Large projects (>100 loads) take longer
- LLM requests depend on provider
- First query slower than subsequent ones (caching)

### Optimization
- UI shows top 5 loads only
- Equipment suggestions limited to top 3 options
- Design analysis optimized for ≤50 loads

---

## FAQ

**Q: Can I ignore the recommendations?**
A: Yes, all suggestions are optional. Use your engineering judgment.

**Q: Will it damage data if I use wrong equipment?**
A: No, the system stores what you input. Warnings help prevent mistakes.

**Q: What if LLM API is down?**
A: System uses rule-based calculations instead. Core functionality preserved.

**Q: Can I export the AI analysis?**
A: Yes, go to Charts & Reports and use screenshot or export options.

**Q: How accurate are the recommendations?**
A: Based on IEC standards and engineering best practices. Real-world factors may differ.

**Q: Can I adjust cable/breaker sizes manually?**
A: Yes, recommendations are suggestions. Edit the Equipment Config to change values.

**Q: Does it check code compliance?**
A: Checks against IEC standards. Local codes may differ - verify separately.

**Q: What's the design score based on?**
A: Issues (-10 pts), Safety (-15 pts), Warnings (-3 pts), Compliance check (-10 pts each)

---

## Getting Help

### Issues with Equipment Suggestions
1. Check that load values are valid
2. Ensure voltage is a standard value
3. Try setting load type explicitly
4. Contact support with error message

### Issues with Design Score
1. Review specific issues listed
2. Add missing equipment (breakers, protection)
3. Verify load values are realistic
4. Check standards compliance report

### General Issues
1. Refresh page (F5)
2. Clear session state if needed
3. Restart Streamlit app
4. Check Python dependencies

---

## Next Steps

1. **Try it out**: Upload an Excel file and view Design & Analysis
2. **Review suggestions**: Check each load's recommendations
3. **Verify standards**: Review compliance table
4. **Optimize design**: Use recommendations to improve
5. **Export results**: Save your validated design

---

## Summary

The AI features provide:
- ✅ Instant equipment recommendations
- ✅ Design quality scoring
- ✅ Standards compliance checking
- ✅ Safety concern identification
- ✅ Intelligent insights and suggestions

Use them to design better electrical systems faster with expert guidance.

# Google Gemini AI Integration User Guide

## Overview

Your Electrical Design Automation System now includes Google Gemini AI integration for intelligent Excel data extraction and electrical engineering assistance. This guide explains how Gemini is used throughout the application and how to maximize its benefits.

## 🔑 Setup Requirements

### API Key Configuration
1. **.env File**: Your Google API key is stored in the `.env` file:
   ```
   GOOGLE_API_KEY=AIzaSyBOBRk79E-6G4_QHJhsekwMy8x2sKX0ung
   ```

2. **Automatic Loading**: The system automatically loads this key when the application starts using python-dotenv.

## 🎯 Where Gemini AI is Used

### 1. 🤖 AI Excel Extraction (Primary Use)

**Location**: `🤖 AI Tools` → Upload Excel File

**What it does**:
- **Intelligent File Analysis**: Gemini analyzes Excel file structure and content
- **Header Detection**: Automatically identifies column headers using AI pattern recognition
- **Data Extraction**: Extracts electrical parameters with contextual understanding
- **Validation**: Performs electrical engineering rule validation
- **Auto-Correction**: Suggests and applies fixes for common data issues

**How to use**:
1. Navigate to `🤖 AI Tools`
2. Upload your Excel file (supports .xlsx, .xls)
3. Enter a project name
4. Click `🚀 Extract with AI`
5. Gemini processes the file and creates your electrical project

### 2. 📊 Design Analysis & Assistance

**Location**: `📊 Design & Analysis`

**What Gemini provides**:
- **Smart Design Suggestions**: Analyzes your electrical system and provides optimization recommendations
- **Standards Compliance**: Checks against IEC/NEC standards and provides guidance
- **Load Balancing**: Identifies phase imbalances and suggests corrections
- **Cable Optimization**: Recommends cable size optimizations
- **Engineering Insights**: Provides professional electrical engineering advice

### 3. 💡 Smart Defaults & Validation

**Location**: Throughout the application for form assistance

**What Gemini enables**:
- **Smart Parameter Defaults**: Context-aware default values based on load type and voltage
- **Parameter Validation**: Real-time validation with engineering reasoning
- **Design Rule Checking**: Ensures electrical safety and standards compliance

## 🚀 Quick Start Workflow

### Method 1: AI-Powered Excel Import (Recommended)
```
1. Go to 🤖 AI Tools
2. Upload your Excel file
3. Let Gemini extract data automatically
4. Review results in 📊 Design & Analysis
5. Export reports with one click
```

### Method 2: Manual Design with AI Assistance
```
1. Use 🚀 Quick Design for templates
2. Add loads manually with AI smart defaults
3. Get design suggestions in Analysis & Reports
4. Export your complete project
```

## 🔧 AI Features in Detail

### Excel Processing Capabilities

**Input Formats Supported**:
- Load schedules with power, voltage, equipment details
- Cable schedules with specifications and routing
- Bus configurations with ratings and connections
- Transformer schedules with ratings and vector groups

**AI Processing Steps**:
1. **Structure Analysis**: Gemini understands table layout and relationships
2. **Content Understanding**: Recognizes electrical terminology and units
3. **Data Mapping**: Maps columns to electrical parameters intelligently
4. **Validation**: Applies electrical engineering rules
5. **Enhancement**: Auto-corrects common issues

### Design Intelligence Features

**Load Analysis**:
- Identifies load types (motor, lighting, HVAC, etc.)
- Calculates power requirements and power factors
- Suggests protection and cabling requirements

**System Optimization**:
- Recommends cable sizing optimizations
- Identifies potential phase imbalances
- Suggests diversity factor adjustments

**Standards Compliance**:
- IEC 60364 Low Voltage requirements
- NEC conductor ampacity rules
- Equipment grounding requirements
- Protective device coordination

## 📊 Understanding AI Results

### Confidence Scores
- **High Confidence (>0.8)**: Data extracted with high reliability
- **Medium Confidence (0.5-0.8)**: Good extraction, manual review recommended
- **Low Confidence (<0.5)**: Requires manual correction

### Validation Messages
- **✅ Success**: Data meets all electrical engineering standards
- **⚠️ Warnings**: Potential issues that don't prevent operation
- **❌ Errors**: Critical issues requiring correction

## 🔄 AI Learning & Improvement

### Vector Database Integration
Your system includes a **vector database** that learns from:
- Successful extractions and corrections
- Design patterns and best practices
- Standards compliance examples
- Component specifications

### Continuous Learning
- Each successful project improves future AI performance
- Failed extractions are analyzed to prevent similar issues
- Design patterns are stored for reuse

## 🛠️ Troubleshooting

### Common Issues & Solutions

**API Key Problems**:
```
Error: No API key found for Google Gemini
Solution: Ensure .env file exists with valid GOOGLE_API_KEY
```

**Extraction Failures**:
```
Problem: AI cannot extract data from Excel
Solutions:
1. Use clear column headers
2. Include standard electrical terminology
3. Ensure data is in tabular format
4. Try manual workflow as fallback
```

**Validation Errors**:
```
Problem: Extracted data fails validation
Solutions:
1. Review AI suggestions in Manual Review tab
2. Correct obvious errors manually
3. Check electrical parameter ranges
4. Verify units and standards
```

### Manual Workflow Fallback

If AI extraction fails:
1. **Create project manually** using Quick Design templates
2. **Add loads through the standard interface**
3. **Use smart defaults** for parameter assistance
4. **Run calculations normally**

## 📈 Performance & Cost

### API Usage
- **Model**: `gemini-2.0-flash` (fast, cost-effective)
- **Typical Usage**: 1-2 API calls per Excel file extraction
- **Cost**: Minimal (under $0.01 per extraction)
- **Rate Limits**: 60 requests per minute

### Processing Speed
- **Small files (<100 rows)**: 5-10 seconds
- **Large files (>500 rows)**: 20-30 seconds
- **Complex layouts**: May take longer for analysis

## 🎯 Best Practices

### Excel File Preparation
1. **Use clear headers**: "Load Name", "Power (kW)", "Voltage (V)"
2. **Standard terminology**: "Motor Pump", "Lighting Panel", "HVAC Unit"
3. **Consistent formatting**: Same units throughout
4. **Tabular structure**: No merged cells, clear data ranges

### Data Quality Tips
1. **Realistic values**: Power ratings should be physically possible
2. **Complete information**: Include all required electrical parameters
3. **Logical connections**: Equipment connections should make sense
4. **Standards compliance**: Use appropriate voltage levels and phases

### Getting Better Results
1. **Start simple**: Begin with smaller, well-formatted files
2. **Learn patterns**: The AI improves with each successful extraction
3. **Provide feedback**: Use manual corrections to teach the system
4. **Review suggestions**: Always check AI recommendations

## 🔮 Future Enhancements

### Planned AI Features
- **Diagram Analysis**: Upload SLD images for automatic extraction
- **Design Optimization**: AI-powered system optimization
- **Standards Updates**: Automatic compliance checking
- **Component Libraries**: AI-assisted equipment selection

### Advanced Capabilities
- **Multi-language Support**: Process international electrical documents
- **Industry Templates**: Specialized templates for different sectors
- **Collaborative Design**: AI-assisted multi-user design sessions

## 📞 Support & Resources

### Getting Help
- **Check logs**: Terminal output shows AI processing details
- **Manual fallback**: Always available if AI fails
- **Sample files**: Use provided sample Excel files for testing

### Documentation
- **This guide**: Comprehensive AI integration documentation
- **API reference**: Technical details in source code comments
- **Best practices**: Ongoing updates based on user feedback

---

## 🎉 Getting Started

You're now ready to use Gemini AI in your Electrical Design Automation System! The AI integration provides intelligent assistance while maintaining full manual control when needed.

**First Steps**:
1. Try the AI Excel extraction with a sample file
2. Review the AI suggestions and corrections
3. Explore the design analysis recommendations
4. Use the streamlined workflow for faster project completion

The combination of AI intelligence and engineering expertise creates a powerful, user-friendly design tool that learns and improves with each use.
from flask import Flask
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__)

@app.route('/')
def home():
    """Serve the main application page"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Electrical Design Automation System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                text-align: center;
                color: #1f77b4;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .status {
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
            }
            .success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .info {
                background-color: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⚡ Electrical Design Automation System</h1>
            <p>Deployed on Vercel</p>
        </div>

        <div class="card">
            <h2>🚀 Deployment Status</h2>
            <div class="status success">
                ✅ Application successfully deployed to Vercel
            </div>
            <div class="status info">
                ℹ️ This is a simplified web interface. The full Streamlit application requires a persistent server environment.
            </div>
        </div>

        <div class="card">
            <h2>📋 Available Features</h2>
            <ul>
                <li>✅ Project committed and pushed to GitHub</li>
                <li>✅ Vercel deployment configuration created</li>
                <li>✅ Basic web interface deployed</li>
                <li>⚠️ Full Streamlit app requires alternative deployment (Streamlit Cloud, Heroku, etc.)</li>
            </ul>
        </div>

        <div class="card">
            <h2>🔗 Repository</h2>
            <p><a href="https://github.com/vapor7v/sld-design" target="_blank">https://github.com/vapor7v/sld-design</a></p>
        </div>

        <div class="card">
            <h2>💡 Recommendations</h2>
            <p>For the full Streamlit application with interactive features, consider deploying to:</p>
            <ul>
                <li><strong>Streamlit Cloud</strong> - Official platform for Streamlit apps</li>
                <li><strong>Heroku</strong> - Supports Python applications with persistent servers</li>
                <li><strong>AWS/Heroku</strong> - For production deployments</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "ok", "deployment": "vercel"}

# For Vercel, we need to export the app
def handler(request):
    """Vercel handler function"""
    from werkzeug.wrappers import Request
    from werkzeug.serving import make_server

    # This is a simplified handler - in practice, you'd need proper WSGI handling
    return app

# Export the Flask app for Vercel
application = app
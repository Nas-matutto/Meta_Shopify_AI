# META Ads & Sales Data Analyzer

A powerful web application that analyzes META Ads and Sales data using Claude AI to provide intelligent insights and answer questions about your marketing performance and sales data.

## 🚀 Features

- **File Upload**: Support for CSV and Excel files from META Ads and Shopify/Sales platforms
- **AI-Powered Question Engine**: Ask ANY question in natural language and get Claude-powered answers
- **Interactive Chat**: Natural conversation interface with your data
- **Comprehensive Analysis**: Get full performance summaries or ask specific questions
- **Real-time Processing**: Instant file processing and analysis
- **No External Dependencies**: Runs completely locally - only needs your Claude API key
- **Responsive Design**: Works on desktop and mobile devices

## 📋 Prerequisites

- Python 3.8 or higher
- Anthropic Claude API key
- **That's it!** No other external services required

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd meta-sales-analyzer
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

1. Copy the `.env` template:
```bash
cp .env .env.local
```

2. Edit `.env.local` and add your configuration:
```bash
ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here
SECRET_KEY=your-secure-secret-key-for-production
```

### 5. Create Required Directories

```bash
mkdir templates uploads
```

### 6. Move Template File

Move the `index.html` file to the `templates/` directory:
```bash
# Make sure index.html is in templates/index.html
```

## 🏃‍♂️ Running the Application

### Development Mode

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Production Mode

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📁 Project Structure

```
meta-sales-analyzer/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables template
├── .gitignore           # Git ignore rules
├── README.md            # This file
├── templates/
│   └── index.html       # Frontend template
└── uploads/             # File upload directory (created automatically)
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Claude API key | Required |
| `SECRET_KEY` | Flask session secret key | Required |
| `FLASK_ENV` | Environment mode | `development` |
| `MAX_CONTENT_LENGTH` | Max file upload size in bytes | `16777216` (16MB) |

### File Upload Limits

- **Supported formats**: CSV, XLSX, XLS
- **Maximum file size**: 16MB per file
- **Required files**: Both META Ads and Sales data files

## 🌐 Deployment

### GitHub Deployment

1. **Push to GitHub**:
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. **Deploy to your preferred platform**:
   - **Heroku**: Add `Procfile` with `web: gunicorn app:app`
   - **Railway**: Connect your GitHub repo
   - **Render**: Connect your GitHub repo
   - **PythonAnywhere**: Upload files and configure WSGI

### Environment Variables for Production

Set these environment variables in your deployment platform:
- `ANTHROPIC_API_KEY`
- `SECRET_KEY`
- `FLASK_ENV=production`

## 📊 Usage

1. **Upload Files**: 
   - Upload your META Ads data (CSV/Excel)
   - Upload your Sales data (CSV/Excel)

2. **Review Data Summary**: 
   - Check the automatically generated data overview
   - Verify column names and row counts

3. **Ask Questions**: 
   - Use natural language to ask about your data
   - Examples:
     - "What's the ROI of my META ads campaigns?"
     - "Which products had the highest sales?"
     - "Show me the correlation between ad spend and revenue"
     - "What are the top performing campaigns?"

## 🔍 Sample Questions

- **Performance Analysis**: "What's my overall ROAS?"
- **Campaign Insights**: "Which campaigns generated the most revenue?"
- **Trend Analysis**: "How did my sales trend over time?"
- **Optimization**: "Which ad sets should I scale up?"
- **Attribution**: "What's the correlation between impressions and sales?"

## 🛡️ Security Considerations

- **API Keys**: Never commit API keys to version control
- **File Uploads**: Files are processed in memory and not permanently stored
- **Session Management**: Data is cleared when browser session ends
- **Input Validation**: All file uploads are validated for type and size

## 🐛 Troubleshooting

### Common Issues

1. **"Module not found" errors**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Claude API errors**:
   - Verify your API key is correct
   - Check your API usage limits
   - Ensure you have credit in your Anthropic account

3. **File upload errors**:
   - Check file format (CSV, XLSX, XLS only)
   - Verify file size is under 16MB
   - Ensure files have proper headers

4. **Template not found**:
   - Ensure `index.html` is in the `templates/` directory
   - Check file permissions

### Debug Mode

Run with debug information:
```bash
FLASK_DEBUG=True python app.py
```

## 📈 Extending the Application

### Adding New Data Sources

1. Modify the upload route in `app.py`
2. Update the file parsing logic
3. Adjust the Claude API context

### Custom Analysis Features

1. Add new routes for specific analysis types
2. Create specialized prompts for Claude
3. Add frontend components for new features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Anthropic for the Claude API
- Flask community for the web framework
- Pandas for data processing capabilities

## 📞 Support

For support, please:
1. Check the troubleshooting section
2. Review the GitHub issues
3. Create a new issue with detailed information

---

**Built with ❤️ for data-driven marketing insights**
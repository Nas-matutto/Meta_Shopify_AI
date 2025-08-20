from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import pandas as pd
import json
import os
from datetime import datetime
import anthropic
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Anthropic client (you'll need to set your API key)
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY', 'your-api-key-here')
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_uploaded_file(file):
    """Parse uploaded CSV or Excel file into pandas DataFrame"""
    try:
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if file_extension == 'csv':
            # Try different encodings and separators
            content = file.read()
            file.seek(0)  # Reset file pointer
            
            # Try UTF-8 first, then latin-1 if that fails
            try:
                df = pd.read_csv(io.StringIO(content.decode('utf-8')))
            except UnicodeDecodeError:
                df = pd.read_csv(io.StringIO(content.decode('latin-1')))
                
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(file)
        else:
            return None, "Unsupported file format"
            
        return df, None
    except Exception as e:
        return None, f"Error parsing file: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # Check if files are present
        if 'meta_ads_file' not in request.files or 'sales_file' not in request.files:
            return jsonify({'error': 'Both META Ads and Sales files are required'}), 400
        
        meta_file = request.files['meta_ads_file']
        sales_file = request.files['sales_file']
        
        if meta_file.filename == '' or sales_file.filename == '':
            return jsonify({'error': 'Both files must be selected'}), 400
        
        if not (allowed_file(meta_file.filename) and allowed_file(sales_file.filename)):
            return jsonify({'error': 'Only CSV and Excel files are allowed'}), 400
        
        # Parse META Ads file
        meta_df, meta_error = parse_uploaded_file(meta_file)
        if meta_error:
            return jsonify({'error': f'META Ads file error: {meta_error}'}), 400
        
        # Parse Sales file
        sales_df, sales_error = parse_uploaded_file(sales_file)
        if sales_error:
            return jsonify({'error': f'Sales file error: {sales_error}'}), 400
        
        # Store data in session (for MVP - in production, use a database)
        session['meta_data'] = meta_df.to_json(orient='records')
        session['sales_data'] = sales_df.to_json(orient='records')
        session['meta_columns'] = list(meta_df.columns)
        session['sales_columns'] = list(sales_df.columns)
        
        # Generate data summary for initial analysis
        meta_summary = {
            'rows': len(meta_df),
            'columns': len(meta_df.columns),
            'column_names': list(meta_df.columns),
            'sample_data': meta_df.head(3).to_dict('records')
        }
        
        sales_summary = {
            'rows': len(sales_df),
            'columns': len(sales_df.columns),
            'column_names': list(sales_df.columns),
            'sample_data': sales_df.head(3).to_dict('records')
        }
        
        return jsonify({
            'message': 'Files uploaded successfully',
            'meta_summary': meta_summary,
            'sales_summary': sales_summary
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Check if data exists in session
        if 'meta_data' not in session or 'sales_data' not in session:
            return jsonify({'error': 'Please upload files first'}), 400
        
        # Reconstruct DataFrames from session
        meta_df = pd.read_json(session['meta_data'], orient='records')
        sales_df = pd.read_json(session['sales_data'], orient='records')
        
        # Prepare context for Claude
        context = f"""
        I have two datasets to analyze:
        
        1. META Ads Data:
        - {len(meta_df)} rows, {len(meta_df.columns)} columns
        - Columns: {', '.join(meta_df.columns)}
        - Sample data (first 3 rows): {meta_df.head(3).to_json(orient='records')}
        
        2. Sales Data:
        - {len(sales_df)} rows, {len(sales_df.columns)} columns  
        - Columns: {', '.join(sales_df.columns)}
        - Sample data (first 3 rows): {sales_df.head(3).to_json(orient='records')}
        
        Question: {question}
        
        Please analyze this data and provide insights. If you need more specific data points or calculations, let me know what additional information would be helpful.
        """
        
        # Call Claude API with enhanced analysis capabilities
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Updated to latest model
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a data analyst expert specializing in META Ads and Sales performance analysis. 

{context}

Please provide a comprehensive analysis based on the question asked. When analyzing:
1. Look for patterns, correlations, and insights in the data
2. Provide specific numbers and metrics when possible
3. Give actionable recommendations
4. If you need to see more specific data points to answer accurately, let me know what additional information would be helpful
5. Format your response clearly with key insights highlighted

Answer the question thoroughly and provide valuable business insights."""
                }
            ]
        )
        
        response_text = message.content[0].text
        
        return jsonify({
            'answer': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/data-summary', methods=['GET'])
def get_data_summary():
    try:
        if 'meta_data' not in session or 'sales_data' not in session:
            return jsonify({'error': 'No data uploaded'}), 400
        
        # Reconstruct DataFrames
        meta_df = pd.read_json(session['meta_data'], orient='records')
        sales_df = pd.read_json(session['sales_data'], orient='records')
        
        summary = {
            'meta_ads': {
                'rows': len(meta_df),
                'columns': list(meta_df.columns),
                'data_types': meta_df.dtypes.astype(str).to_dict()
            },
            'sales': {
                'rows': len(sales_df),
                'columns': list(sales_df.columns),
                'data_types': sales_df.dtypes.astype(str).to_dict()
            }
        }
        
        return jsonify(summary)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get summary: {str(e)}'}), 500

@app.route('/detailed-analysis', methods=['POST'])
def detailed_analysis():
    """Get detailed analysis of specific data subsets"""
    try:
        data = request.get_json()
        analysis_type = data.get('analysis_type', 'general')
        
        if 'meta_data' not in session or 'sales_data' not in session:
            return jsonify({'error': 'Please upload files first'}), 400
        
        # Reconstruct DataFrames
        meta_df = pd.read_json(session['meta_data'], orient='records')
        sales_df = pd.read_json(session['sales_data'], orient='records')
        
        # Provide more detailed data context for specific analysis types
        if analysis_type == 'performance_summary':
            context = f"""
            Perform a comprehensive performance analysis of this META Ads and Sales data:
            
            META Ads Data Summary:
            - Total rows: {len(meta_df)}
            - Columns: {', '.join(meta_df.columns)}
            - Full dataset: {meta_df.to_json(orient='records')}
            
            Sales Data Summary:
            - Total rows: {len(sales_df)}
            - Columns: {', '.join(sales_df.columns)}
            - Full dataset: {sales_df.to_json(orient='records')}
            
            Please provide:
            1. Overall performance metrics and KPIs
            2. Top performing campaigns/products
            3. Key insights and patterns
            4. Recommendations for optimization
            5. Any concerning trends or opportunities
            """
        else:
            # Standard analysis with sample data
            context = f"""
            Analyze this META Ads and Sales data:
            
            META Ads Data ({len(meta_df)} rows):
            Columns: {', '.join(meta_df.columns)}
            Sample: {meta_df.head(5).to_json(orient='records')}
            
            Sales Data ({len(sales_df)} rows):
            Columns: {', '.join(sales_df.columns)}
            Sample: {sales_df.head(5).to_json(orient='records')}
            
            Provide a general business intelligence analysis with key insights.
            """
        
        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": context
                }
            ]
        )
        
        response_text = message.content[0].text
        
        return jsonify({
            'analysis': response_text,
            'analysis_type': analysis_type,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Detailed analysis failed: {str(e)}'}), 500
def clear_data():
    """Clear uploaded data from session"""
    session.pop('meta_data', None)
    session.pop('sales_data', None)
    session.pop('meta_columns', None)
    session.pop('sales_columns', None)
    return jsonify({'message': 'Data cleared successfully'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
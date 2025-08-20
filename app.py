from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
import anthropic
from werkzeug.utils import secure_filename
import io
from dotenv import load_dotenv
import hashlib
import pickle
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.permanent_session_lifetime = timedelta(hours=2)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
SESSION_DATA_FOLDER = 'session_data'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SESSION_DATA_FOLDER, exist_ok=True)

# Initialize Anthropic client with proper error handling
try:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your-api-key-here':
        print("WARNING: ANTHROPIC_API_KEY not found in environment variables!")
        print("Please set your API key in the .env file")
        client = None
    else:
        # Check if we're in a corporate environment with SSL issues
        import ssl
        import urllib3
        
        # For corporate networks with SSL inspection, we may need to handle certificates differently
        try:
            # Try normal connection first
            client = anthropic.Anthropic(
                api_key=api_key,
                timeout=60.0,
                max_retries=3
            )
            print(f"Anthropic client initialized successfully with key: {api_key[:10]}...")
        except Exception as ssl_error:
            print(f"SSL/Connection issue detected: {ssl_error}")
            print("This appears to be a corporate network with SSL inspection.")
            print("Please try connecting via mobile hotspot or personal VPN.")
            client = None
            
except Exception as e:
    print(f"Error initializing Anthropic client: {e}")
    client = None

def get_session_id():
    """Get or create a session ID"""
    if 'session_id' not in session:
        # Create a unique session ID
        session['session_id'] = hashlib.md5(f"{datetime.now().isoformat()}{os.urandom(16)}".encode()).hexdigest()
        session.permanent = True
    return session['session_id']

def save_session_data(session_id, data):
    """Save data to file instead of session cookie"""
    try:
        filepath = os.path.join(SESSION_DATA_FOLDER, f"{session_id}.pkl")
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        print(f"✅ Data saved to file: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving session data: {e}")
        return False

def load_session_data(session_id):
    """Load data from file"""
    try:
        filepath = os.path.join(SESSION_DATA_FOLDER, f"{session_id}.pkl")
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            print(f"✅ Data loaded from file: {filepath}")
            return data
        else:
            print(f"❌ Session file not found: {filepath}")
            return {}
    except Exception as e:
        print(f"❌ Error loading session data: {e}")
        return {}

def clear_session_data(session_id):
    """Clear session data file"""
    try:
        filepath = os.path.join(SESSION_DATA_FOLDER, f"{session_id}.pkl")
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"✅ Session data file deleted: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error clearing session data: {e}")
        return False

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
        
        # Clean the DataFrame
        # Replace infinite values with NaN, then fill NaN with appropriate values
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Convert numeric columns properly
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to convert to numeric, if fails keep as string
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
        
        return df, None
    except Exception as e:
        return None, f"Error parsing file: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        print("=== UPLOAD ENDPOINT DEBUG (FILE-BASED) ===")
        print(f"Upload endpoint called")
        
        # Check if files are present
        if 'meta_ads_file' not in request.files or 'sales_file' not in request.files:
            print("Missing files in request")
            return jsonify({'error': 'Both META Ads and Sales files are required'}), 400
        
        meta_file = request.files['meta_ads_file']
        sales_file = request.files['sales_file']
        
        print(f"Files received: {meta_file.filename}, {sales_file.filename}")
        
        if meta_file.filename == '' or sales_file.filename == '':
            return jsonify({'error': 'Both files must be selected'}), 400
        
        if not (allowed_file(meta_file.filename) and allowed_file(sales_file.filename)):
            return jsonify({'error': 'Only CSV and Excel files are allowed'}), 400
        
        # Parse META Ads file
        print("Parsing META Ads file...")
        meta_df, meta_error = parse_uploaded_file(meta_file)
        if meta_error:
            print(f"META Ads parsing error: {meta_error}")
            return jsonify({'error': f'META Ads file error: {meta_error}'}), 400
        
        # Parse Sales file
        print("Parsing Sales file...")
        sales_df, sales_error = parse_uploaded_file(sales_file)
        if sales_error:
            print(f"Sales parsing error: {sales_error}")
            return jsonify({'error': f'Sales file error: {sales_error}'}), 400
        
        print(f"Data shapes - META: {meta_df.shape}, Sales: {sales_df.shape}")
        
        # Clean data and handle NaN values before storing
        meta_df_clean = meta_df.fillna('')
        sales_df_clean = sales_df.fillna('')
        
        print("Data cleaned, converting to JSON...")
        
        # Get session ID for file-based storage
        session_id = get_session_id()
        print(f"🆔 Generated Session ID: {session_id}")
        print(f"📁 Session data folder exists: {os.path.exists(SESSION_DATA_FOLDER)}")
        print(f"📁 Session data folder path: {os.path.abspath(SESSION_DATA_FOLDER)}")
        
        # Store data in file instead of session cookie
        session_data = {
            'meta_data': meta_df_clean.to_json(orient='records'),
            'sales_data': sales_df_clean.to_json(orient='records'),
            'meta_columns': list(meta_df.columns),
            'sales_columns': list(sales_df.columns),
            'upload_timestamp': datetime.now().isoformat()
        }
        
        print(f"💾 Attempting to save data for session: {session_id}")
        
        if save_session_data(session_id, session_data):
            print("✅ Data stored in FILE successfully (not session cookie)")
            print(f"📊 META data length: {len(session_data['meta_data'])} chars")
            print(f"💰 Sales data length: {len(session_data['sales_data'])} chars")
            
            # Verify the file was actually created
            filepath = os.path.join(SESSION_DATA_FOLDER, f"{session_id}.pkl")
            print(f"📄 File exists after save: {os.path.exists(filepath)}")
            if os.path.exists(filepath):
                print(f"📏 File size: {os.path.getsize(filepath)} bytes")
        else:
            return jsonify({'error': 'Failed to save session data'}), 500
        
        # Generate data summary for initial analysis
        meta_summary = {
            'rows': len(meta_df),
            'columns': len(meta_df.columns),
            'column_names': list(meta_df.columns),
            'sample_data': meta_df_clean.head(3).to_dict('records')
        }
        
        sales_summary = {
            'rows': len(sales_df),
            'columns': len(sales_df.columns),
            'column_names': list(sales_df.columns),
            'sample_data': sales_df_clean.head(3).to_dict('records')
        }
        
        print("🎉 Returning success response")
        
        return jsonify({
            'message': 'Files uploaded successfully',
            'meta_summary': meta_summary,
            'sales_summary': sales_summary,
            'session_id': session_id  # Include session ID in response for debugging
        })
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    try:
        print("=== ASK ENDPOINT DEBUG (FILE-BASED) ===")
        print(f"🔍 Ask endpoint called")
        
        # Get session ID and load data from file
        if 'session_id' not in session:
            print("❌ No session ID found in session")
            print(f"Session keys: {list(session.keys())}")
            return jsonify({'error': 'No session found. Please upload files first'}), 400
        
        session_id = session['session_id']
        print(f"🆔 Session ID: {session_id}")
        
        # Load session data from file
        print(f"📁 Loading data from file...")
        session_data = load_session_data(session_id)
        if not session_data:
            print("❌ No session data found in file")
            filepath = os.path.join(SESSION_DATA_FOLDER, f"{session_id}.pkl")
            print(f"Expected file path: {filepath}")
            print(f"File exists: {os.path.exists(filepath)}")
            return jsonify({'error': 'Session data not found. Please upload files first'}), 400
        
        print(f"✅ Session data loaded successfully")
        print(f"📊 Session data keys: {list(session_data.keys())}")
        
        # Check if Claude client is available
        if client is None:
            return jsonify({'error': 'Claude API not configured. Please check your ANTHROPIC_API_KEY in .env file'}), 500
        
        data = request.get_json()
        question = data.get('question', '').strip()
        
        print(f"❓ Question received: {question}")
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Check if data exists
        if 'meta_data' not in session_data:
            print("❌ META data not found in session data")
            return jsonify({'error': 'META Ads data not found. Please upload files first'}), 400
            
        if 'sales_data' not in session_data:
            print("❌ Sales data not found in session data")
            return jsonify({'error': 'Sales data not found. Please upload files first'}), 400
        
        print("✅ Both datasets found in session data")
        
        # Reconstruct DataFrames from session data
        print("🔄 Reconstructing DataFrames...")
        try:
            meta_df = pd.read_json(session_data['meta_data'], orient='records')
            sales_df = pd.read_json(session_data['sales_data'], orient='records')
            print(f"✅ Data loaded successfully - META: {len(meta_df)} rows, Sales: {len(sales_df)} rows")
        except Exception as e:
            print(f"❌ Error reconstructing DataFrames: {e}")
            return jsonify({'error': 'Error reading uploaded data. Please re-upload your files.'}), 400
        
        # Prepare context for Claude (limit data size for API)
        meta_sample = meta_df.head(5).to_dict('records') if len(meta_df) > 5 else meta_df.to_dict('records')
        sales_sample = sales_df.head(5).to_dict('records') if len(sales_df) > 5 else sales_df.to_dict('records')
        
        context = f"""You are a data analyst expert specializing in META Ads and Sales performance analysis. 

I have two datasets to analyze:

1. META Ads Data:
- {len(meta_df)} rows, {len(meta_df.columns)} columns
- Columns: {', '.join(meta_df.columns)}
- Sample data (first 5 rows): {json.dumps(meta_sample, default=str)}

2. Sales Data:
- {len(sales_df)} rows, {len(sales_df.columns)} columns  
- Columns: {', '.join(sales_df.columns)}
- Sample data (first 5 rows): {json.dumps(sales_sample, default=str)}

Question: {question}

Please provide a comprehensive analysis based on the question asked. When analyzing:
1. Look for patterns, correlations, and insights in the data
2. Provide specific numbers and metrics when possible
3. Give actionable recommendations
4. If you need to see more specific data points to answer accurately, let me know what additional information would be helpful
5. Format your response clearly with key insights highlighted

Answer the question thoroughly and provide valuable business insights."""
        
        print("🤖 Sending request to Claude API...")
        
        # Call Claude API with enhanced analysis capabilities
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Use the correct model name
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": context
                }
            ]
        )
        
        print("✅ Claude API response received")
        
        response_text = message.content[0].text
        
        return jsonify({
            'answer': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
    except anthropic.APIError as e:
        print(f"Anthropic API Error: {e}")
        return jsonify({'error': f'Claude API Error: {str(e)}'}), 500
    except anthropic.APIConnectionError as e:
        print(f"Anthropic Connection Error: {e}")
        return jsonify({'error': f'Connection to Claude API failed. Please check your internet connection and API key.'}), 500
    except anthropic.RateLimitError as e:
        print(f"Anthropic Rate Limit Error: {e}")
        return jsonify({'error': f'Rate limit exceeded. Please try again in a moment.'}), 429
    except Exception as e:
        print(f"General error in ask_question: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/detailed-analysis', methods=['POST'])
def detailed_analysis():
    """Get detailed analysis of specific data subsets"""
    try:
        data = request.get_json()
        analysis_type = data.get('analysis_type', 'general')
        
        if 'session_id' not in session:
            return jsonify({'error': 'Please upload files first'}), 400
        
        session_id = session['session_id']
        session_data = load_session_data(session_id)
        
        if not session_data or 'meta_data' not in session_data or 'sales_data' not in session_data:
            return jsonify({'error': 'Please upload files first'}), 400
        
        # Reconstruct DataFrames
        meta_df = pd.read_json(session_data['meta_data'], orient='records')
        sales_df = pd.read_json(session_data['sales_data'], orient='records')
        
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

@app.route('/data-summary', methods=['GET'])
def get_data_summary():
    try:
        if 'session_id' not in session:
            return jsonify({'error': 'No data uploaded'}), 400
        
        session_id = session['session_id']
        session_data = load_session_data(session_id)
        
        if not session_data or 'meta_data' not in session_data or 'sales_data' not in session_data:
            return jsonify({'error': 'No data uploaded'}), 400
        
        # Reconstruct DataFrames
        meta_df = pd.read_json(session_data['meta_data'], orient='records')
        sales_df = pd.read_json(session_data['sales_data'], orient='records')
        
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

@app.route('/session-status', methods=['GET'])
def session_status():
    """Check what's in the current session"""
    if 'session_id' not in session:
        return jsonify({
            'has_session': False,
            'message': 'No session found'
        })
    
    session_id = session['session_id']
    session_data = load_session_data(session_id)
    
    return jsonify({
        'has_session': True,
        'session_id': session_id,
        'session_data_keys': list(session_data.keys()),
        'has_meta_data': 'meta_data' in session_data,
        'has_sales_data': 'sales_data' in session_data,
        'meta_data_length': len(session_data.get('meta_data', '')) if 'meta_data' in session_data else 0,
        'sales_data_length': len(session_data.get('sales_data', '')) if 'sales_data' in session_data else 0,
        'upload_timestamp': session_data.get('upload_timestamp', 'Not found')
    })

@app.route('/clear-data', methods=['POST'])
def clear_data():
    """Clear uploaded data from session"""
    try:
        if 'session_id' in session:
            session_id = session['session_id']
            clear_session_data(session_id)
        
        # Clear session
        session.clear()
        return jsonify({'message': 'Data cleared successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to clear data: {str(e)}'}), 500

@app.route('/test-claude', methods=['GET'])
def test_claude():
    """Test endpoint to verify Claude API is working"""
    try:
        if client is None:
            return jsonify({
                'status': 'error',
                'message': 'Claude client not initialized. Check ANTHROPIC_API_KEY in .env file'
            }), 500
        
        # Simple test message
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Please respond with 'API connection successful!' to confirm you're working."
                }
            ]
        )
        
        response_text = message.content[0].text
        
        return jsonify({
            'status': 'success',
            'message': 'Claude API is working!',
            'response': response_text
        })
        
    except anthropic.APIConnectionError as e:
        return jsonify({
            'status': 'error',
            'message': f'Connection error: {str(e)}',
            'suggestion': 'Check your internet connection and firewall settings'
        }), 500
        
    except anthropic.APIError as e:
        return jsonify({
            'status': 'error',
            'message': f'API error: {str(e)}',
            'suggestion': 'Check your API key is valid and has proper permissions'
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/debug-config', methods=['GET'])
def debug_config():
    """Debug endpoint to check configuration"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    return jsonify({
        'env_file_exists': os.path.exists('.env'),
        'api_key_loaded': bool(api_key),
        'api_key_format': api_key[:15] + '...' if api_key and len(api_key) > 15 else 'Not found',
        'api_key_length': len(api_key) if api_key else 0,
        'client_initialized': client is not None,
        'working_directory': os.getcwd(),
        'session_data_folder_exists': os.path.exists(SESSION_DATA_FOLDER),
        'session_data_folder_path': os.path.abspath(SESSION_DATA_FOLDER)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
#!/usr/bin/env python3
"""
Debug script to test Claude API connection
Run this to verify your API key and connection work
"""

import os
from dotenv import load_dotenv
import anthropic

def test_claude_api():
    print("=== Claude API Debug Test ===\n")
    
    # 1. Load environment variables
    print("1. Loading environment variables...")
    load_dotenv()
    
    # 2. Check if .env file exists
    env_file_exists = os.path.exists('.env')
    print(f"   .env file exists: {env_file_exists}")
    
    if env_file_exists:
        with open('.env', 'r') as f:
            env_content = f.read()
            has_api_key = 'ANTHROPIC_API_KEY' in env_content
            print(f"   .env contains ANTHROPIC_API_KEY: {has_api_key}")
    
    # 3. Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    print(f"   API key loaded: {'Yes' if api_key else 'No'}")
    
    if api_key:
        print(f"   API key format: {api_key[:15]}..." if len(api_key) > 15 else api_key)
        print(f"   API key length: {len(api_key)}")
        print(f"   Starts with sk-ant: {'Yes' if api_key.startswith('sk-ant') else 'No'}")
    else:
        print("   ❌ NO API KEY FOUND!")
        print("   Please check your .env file contains:")
        print("   ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here")
        return False
    
    # 4. Test Claude API connection
    print("\n2. Testing Claude API connection...")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("   Client created successfully")
        
        # Test with a simple message
        print("   Sending test message...")
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[
                {
                    "role": "user", 
                    "content": "Hello! Just testing the connection. Please respond with 'Connection successful!'"
                }
            ]
        )
        
        response = message.content[0].text
        print(f"   ✅ SUCCESS! Claude responded: {response}")
        return True
        
    except anthropic.APIConnectionError as e:
        print(f"   ❌ CONNECTION ERROR: {e}")
        print("   This usually means:")
        print("   - Internet connection issue")
        print("   - Firewall blocking the request")
        print("   - Claude API is down")
        return False
        
    except anthropic.APIError as e:
        print(f"   ❌ API ERROR: {e}")
        print("   This usually means:")
        print("   - Invalid API key")
        print("   - API key doesn't have access")
        print("   - Rate limit exceeded")
        return False
        
    except Exception as e:
        print(f"   ❌ UNEXPECTED ERROR: {e}")
        return False

def test_alternative_models():
    """Test with different Claude models in case the current one has issues"""
    print("\n3. Testing alternative models...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("   Skipping - no API key")
        return
    
    models_to_test = [
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022"
    ]
    
    client = anthropic.Anthropic(api_key=api_key)
    
    for model in models_to_test:
        try:
            print(f"   Testing {model}...")
            message = client.messages.create(
                model=model,
                max_tokens=20,
                messages=[{"role": "user", "content": "Test"}]
            )
            print(f"   ✅ {model} works!")
            
        except Exception as e:
            print(f"   ❌ {model} failed: {e}")

if __name__ == "__main__":
    success = test_claude_api()
    
    if success:
        print("\n🎉 API test successful! Your Claude API is working.")
        print("The issue might be in your Flask app configuration.")
    else:
        print("\n❌ API test failed. Please fix the issues above.")
        test_alternative_models()
    
    print("\n=== End Debug Test ===")
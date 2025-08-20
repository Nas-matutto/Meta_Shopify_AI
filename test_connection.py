#!/usr/bin/env python3
"""
Test network connectivity to Anthropic API
"""

import os
import requests
import socket
from dotenv import load_dotenv
import anthropic

def test_basic_connectivity():
    """Test basic internet and DNS connectivity"""
    print("=== Network Connectivity Test ===\n")
    
    # 1. Test basic internet
    print("1. Testing basic internet connectivity...")
    try:
        response = requests.get("https://www.google.com", timeout=10)
        print(f"   ✅ Internet works: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Internet issue: {e}")
        return False
    
    # 2. Test DNS resolution for Anthropic
    print("2. Testing DNS resolution for api.anthropic.com...")
    try:
        ip = socket.gethostbyname("api.anthropic.com")
        print(f"   ✅ DNS works: api.anthropic.com resolves to {ip}")
    except Exception as e:
        print(f"   ❌ DNS issue: {e}")
        return False
    
    # 3. Test HTTPS connection to Anthropic
    print("3. Testing HTTPS connection to Anthropic API...")
    try:
        response = requests.get("https://api.anthropic.com", timeout=30)
        print(f"   ✅ HTTPS works: Status {response.status_code}")
    except requests.exceptions.Timeout:
        print("   ⚠️  Connection timeout - might be firewall/proxy issue")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  Response: {e} (this might be normal)")
    
    return True

def test_with_different_settings():
    """Test Claude API with different timeout and retry settings"""
    print("\n=== Testing Claude API with Different Settings ===\n")
    
    load_dotenv()
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ No API key found")
        return False
    
    # Test with different configurations
    configs = [
        {"timeout": 30.0, "max_retries": 1, "model": "claude-3-5-sonnet-20241210"},
        {"timeout": 60.0, "max_retries": 3, "model": "claude-3-5-sonnet-20241210"},
        {"timeout": 30.0, "max_retries": 1, "model": "claude-3-5-haiku-20241022"},
    ]
    
    for i, config in enumerate(configs, 1):
        print(f"{i}. Testing with timeout={config['timeout']}s, retries={config['max_retries']}, model={config['model']}")
        
        try:
            client = anthropic.Anthropic(
                api_key=api_key,
                timeout=config['timeout'],
                max_retries=config['max_retries']
            )
            
            message = client.messages.create(
                model=config['model'],
                max_tokens=20,
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            print(f"   ✅ SUCCESS with config {i}!")
            print(f"   Response: {message.content[0].text}")
            return True
            
        except anthropic.APIConnectionError as e:
            print(f"   ❌ Connection error: {e}")
        except anthropic.APITimeoutError as e:
            print(f"   ❌ Timeout error: {e}")
        except Exception as e:
            print(f"   ❌ Other error: {e}")
    
    return False

def test_proxy_settings():
    """Check if proxy settings might be interfering"""
    print("\n=== Checking Proxy Settings ===\n")
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    proxy_found = False
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"   Found proxy setting: {var}={value}")
            proxy_found = True
    
    if not proxy_found:
        print("   No proxy environment variables found")
    else:
        print("   ⚠️  Proxy detected - this might interfere with API calls")
        print("   Try temporarily unsetting proxy variables:")
        for var in proxy_vars:
            if os.environ.get(var):
                print(f"   unset {var}")

def main():
    # Test basic connectivity first
    if not test_basic_connectivity():
        print("\n❌ Basic connectivity failed. Check your internet connection.")
        return
    
    # Check proxy settings
    test_proxy_settings()
    
    # Test Claude API with different settings
    if test_with_different_settings():
        print("\n🎉 Found a working configuration!")
    else:
        print("\n❌ All Claude API tests failed.")
        print("\nPossible solutions:")
        print("1. Check if you're behind a corporate firewall")
        print("2. Try using a VPN")
        print("3. Check with your network administrator")
        print("4. Try running from a different network (mobile hotspot)")

if __name__ == "__main__":
    main()
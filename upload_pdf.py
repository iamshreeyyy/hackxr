#!/usr/bin/env python3
"""
PDF Upload Helper Script
Upload PDF files to the LLM Document Processing System
"""

import requests
import os
import sys
from pathlib import Path
import time

# Server configuration
SERVER_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{SERVER_URL}/upload-documents"

def check_server_health():
    """Check if the server is running"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not accessible: {e}")
        return False

def upload_pdf(file_path):
    """Upload a single PDF file"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    if not file_path.lower().endswith('.pdf'):
        print(f"❌ File is not a PDF: {file_path}")
        return False
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 50:
        print(f"❌ File too large ({file_size_mb:.1f}MB): {file_path}")
        print("   Maximum file size is 50MB")
        return False
    
    print(f"📄 Uploading: {os.path.basename(file_path)} ({file_size_mb:.1f}MB)")
    
    try:
        with open(file_path, 'rb') as file:
            files = {'files': (os.path.basename(file_path), file, 'application/pdf')}
            
            start_time = time.time()
            response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=300)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful ({processing_time:.1f}s)")
                print(f"   📊 Documents processed: {result.get('documents_processed', 0)}")
                print(f"   🧩 Chunks created: {result.get('total_chunks', 0)}")
                print(f"   ⚡ Processing time: {result.get('processing_time', 0):.2f}s")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail.get('detail', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ Upload timed out (file too large or server busy)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def upload_directory(directory_path):
    """Upload all PDF files in a directory"""
    if not os.path.exists(directory_path):
        print(f"❌ Directory not found: {directory_path}")
        return
    
    pdf_files = list(Path(directory_path).glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in: {directory_path}")
        return
    
    print(f"📁 Found {len(pdf_files)} PDF files in directory")
    print(f"📂 Directory: {directory_path}")
    print("-" * 50)
    
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        if upload_pdf(str(pdf_file)):
            successful += 1
        else:
            failed += 1
        print()  # Add spacing between files
    
    print("=" * 50)
    print(f"📊 Upload Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📄 Total: {len(pdf_files)}")

def test_query(query_text):
    """Test a query against uploaded documents"""
    print(f"🤔 Testing query: {query_text}")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/query",
            json={"query": query_text},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Query successful!")
            print(f"   🎯 Decision: {result.get('decision', 'unknown')}")
            print(f"   📊 Confidence: {result.get('confidence_score', 0):.2f}")
            print(f"   ⚡ Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"   📄 Source clauses: {len(result.get('source_clauses', []))}")
            
            justification = result.get('justification', '')
            if justification:
                print(f"   💭 Justification: {justification[:200]}...")
        else:
            print(f"❌ Query failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Query error: {e}")

def main():
    print("🚀 PDF Upload Helper for LLM Document Processing System")
    print("=" * 60)
    
    # Check server health
    if not check_server_health():
        print("\n💡 Make sure the server is running with: python main.py")
        sys.exit(1)
    
    print()
    
    if len(sys.argv) < 2:
        print("📖 Usage:")
        print("  Upload single file:    python upload_pdf.py /path/to/file.pdf")
        print("  Upload directory:      python upload_pdf.py /path/to/directory/")
        print("  Upload with test query: python upload_pdf.py /path/to/file.pdf 'your test query'")
        print()
        print("🔍 Examples:")
        print("  python upload_pdf.py ~/Documents/policy.pdf")
        print("  python upload_pdf.py ~/Documents/pdfs/")
        print("  python upload_pdf.py policy.pdf 'What is covered for 30-year-old cardiac surgery?'")
        sys.exit(0)
    
    path = sys.argv[1]
    
    # Upload files
    if os.path.isfile(path):
        upload_pdf(path)
    elif os.path.isdir(path):
        upload_directory(path)
    else:
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    # Test query if provided
    if len(sys.argv) > 2:
        test_query_text = sys.argv[2]
        print("\n" + "=" * 50)
        test_query(test_query_text)

if __name__ == "__main__":
    main()

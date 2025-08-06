#!/usr/bin/env python3
"""
Detailed PDF Upload and Verification Script
Shows exactly what happens when uploading PDFs and how to verify results
"""

import requests
import os
import sys
import time
import json
from pathlib import Path

# Server configuration
SERVER_URL = "http://localhost:8001"

def print_banner(text):
    """Print a banner with the given text"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_section(text):
    """Print a section header"""
    print(f"\n🔹 {text}")
    print("-" * 50)

def check_server_status():
    """Get detailed server status"""
    print_banner("CHECKING SERVER STATUS")
    
    try:
        # Check basic health
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not responding correctly")
            return False
            
        health_data = response.json()
        print("✅ Server is healthy and running")
        
        # Get system info
        sys_response = requests.get(f"{SERVER_URL}/system-info", timeout=5)
        if sys_response.status_code == 200:
            sys_info = sys_response.json()
            
            print_section("Current System Status")
            print(f"📊 Documents processed: {sys_info.get('processing_stats', {}).get('documents_processed', 0)}")
            print(f"🧩 Queries processed: {sys_info.get('processing_stats', {}).get('queries_processed', 0)}")
            
            # Vector store status
            agents = health_data.get('agents_status', {}).get('agents', {})
            retrieval = agents.get('retrieval_agent', {})
            print(f"🔍 Documents in vector store: {retrieval.get('indexed_documents', 0)}")
            print(f"📚 Vector store size: {retrieval.get('vector_store_size', 0)} chunks")
            
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Make sure the server is running with: python main.py")
        return False

def upload_and_track_pdf(file_path):
    """Upload PDF with detailed tracking"""
    print_banner(f"UPLOADING PDF: {os.path.basename(file_path)}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    if not file_path.lower().endswith('.pdf'):
        print(f"❌ File is not a PDF: {file_path}")
        return False
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"📄 File: {os.path.basename(file_path)}")
    print(f"📏 Size: {file_size_mb:.2f} MB")
    
    if file_size_mb > 50:
        print(f"❌ File too large (max 50MB)")
        return False
    
    # Get system status before upload
    print_section("System Status BEFORE Upload")
    pre_response = requests.get(f"{SERVER_URL}/system-info")
    if pre_response.status_code == 200:
        pre_data = pre_response.json()
        pre_docs = pre_data.get('processing_stats', {}).get('documents_processed', 0)
        pre_chunks = pre_data.get('system_status', {}).get('agents', {}).get('retrieval_agent', {}).get('indexed_documents', 0)
        print(f"📊 Documents processed: {pre_docs}")
        print(f"🧩 Vector chunks: {pre_chunks}")
    
    # Upload the file
    print_section("Starting Upload Process")
    print("⏳ Uploading and processing...")
    
    try:
        start_time = time.time()
        
        with open(file_path, 'rb') as file:
            files = {'files': (os.path.basename(file_path), file, 'application/pdf')}
            response = requests.post(f"{SERVER_URL}/upload-documents", files=files, timeout=300)
        
        upload_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload completed successfully!")
            print(f"⏱️  Total time: {upload_time:.2f} seconds")
            
            # Show upload results
            print_section("Upload Results")
            print(f"📄 Files uploaded: {result.get('files_uploaded', 0)}")
            print(f"📊 Documents processed: {result.get('documents_processed', 0)}")
            print(f"🧩 Total chunks created: {result.get('total_chunks', 0)}")
            print(f"⚡ Processing time: {result.get('processing_time', 0):.2f}s")
            
            # Get system status after upload
            print_section("System Status AFTER Upload")
            post_response = requests.get(f"{SERVER_URL}/system-info")
            if post_response.status_code == 200:
                post_data = post_response.json()
                post_docs = post_data.get('processing_stats', {}).get('documents_processed', 0)
                post_chunks = post_data.get('system_status', {}).get('agents', {}).get('retrieval_agent', {}).get('indexed_documents', 0)
                
                print(f"📊 Documents processed: {post_docs} (was {pre_docs})")
                print(f"🧩 Vector chunks: {post_chunks} (was {pre_chunks})")
                
                if post_chunks > pre_chunks:
                    print(f"✅ SUCCESS: Added {post_chunks - pre_chunks} new chunks to vector store!")
                else:
                    print("⚠️  WARNING: No new chunks were added to vector store")
            
            return True
            
        else:
            print(f"❌ Upload failed with status code: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_query_with_results(query_text):
    """Test a query and show detailed results"""
    print_banner(f"TESTING QUERY: {query_text}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{SERVER_URL}/query",
            json={"query": query_text},
            timeout=30
        )
        query_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Query processed successfully!")
            print_section("Query Results")
            print(f"🤔 Query: {result.get('query', query_text)}")
            print(f"🎯 Decision: {result.get('decision', 'unknown')}")
            print(f"💰 Amount: ${result.get('amount', 0) or 'Not specified'}")
            print(f"📊 Confidence: {result.get('confidence_score', 0):.2%}")
            print(f"⏱️  Processing time: {query_time:.2f}s")
            print(f"📄 Source clauses found: {len(result.get('source_clauses', []))}")
            
            # Show justification
            justification = result.get('justification', '')
            if justification:
                print_section("AI Justification")
                print(justification)
            
            # Show source clauses if any
            source_clauses = result.get('source_clauses', [])
            if source_clauses:
                print_section("Source Document Clauses")
                for i, clause in enumerate(source_clauses[:3], 1):  # Show first 3
                    print(f"\n📋 Clause {i}:")
                    print(f"   Content: {clause.get('content', 'N/A')[:200]}...")
                    print(f"   Relevance: {clause.get('relevance_score', 0):.2%}")
            else:
                print("\n⚠️  No relevant clauses found in uploaded documents")
                print("   This might mean:")
                print("   • The PDF content doesn't match your query")
                print("   • The document wasn't processed correctly")
                print("   • Try a more general query about the document content")
            
            return True
            
        else:
            print(f"❌ Query failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Query error: {e}")
        return False

def suggest_queries():
    """Suggest queries based on common document types"""
    print_banner("SUGGESTED QUERIES TO TRY")
    
    print("💡 Try these queries to test your uploaded document:")
    print("\n🏥 Insurance/Healthcare:")
    print("   • 'What are the coverage limits?'")
    print("   • 'Is surgery covered?'")
    print("   • 'What is the deductible amount?'")
    print("   • 'What procedures are excluded?'")
    
    print("\n📄 General Document:")
    print("   • 'What is this document about?'")
    print("   • 'What are the key terms?'")
    print("   • 'What are the main sections?'")
    print("   • 'Summarize the content'")
    
    print("\n🔍 Specific Search:")
    print("   • 'Find information about [specific topic]'")
    print("   • 'What does it say about [specific term]?'")

def main():
    if len(sys.argv) < 2:
        print("📖 Usage:")
        print("  python detailed_upload.py /path/to/file.pdf")
        print("  python detailed_upload.py /path/to/file.pdf 'test query'")
        sys.exit(0)
    
    file_path = sys.argv[1]
    
    # Step 1: Check server
    if not check_server_status():
        sys.exit(1)
    
    # Step 2: Upload file
    if upload_and_track_pdf(file_path):
        print_banner("UPLOAD SUCCESSFUL!")
        
        # Step 3: Test query if provided
        if len(sys.argv) > 2:
            test_query = sys.argv[2]
            test_query_with_results(test_query)
        else:
            # Suggest some queries
            suggest_queries()
            
            # Test with a general query
            print_section("Testing with General Query")
            test_query_with_results("What is this document about?")
            
        print_banner("VERIFICATION COMPLETE")
        print("🎉 Your PDF has been successfully processed!")
        print("🌐 You can also test queries at: http://localhost:8000")
        
    else:
        print_banner("UPLOAD FAILED")
        print("❌ There was an issue uploading your PDF")
        print("💡 Check the error messages above and try again")

if __name__ == "__main__":
    main()

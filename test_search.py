#!/usr/bin/env python3
"""
Vector Search Diagnostic Script
Test if the vector search is working correctly
"""

import requests
import json

def test_direct_search():
    """Test the search functionality directly"""
    
    # Test 1: Very simple query
    print("🔍 Test 1: Simple search")
    response = requests.post(
        "http://localhost:8000/query",
        json={"query": "the"},
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Query successful")
        print(f"📄 Source clauses: {len(result.get('source_clauses', []))}")
        if result.get('source_clauses'):
            print("🎉 FOUND CLAUSES! Vector search is working!")
            clause = result['source_clauses'][0]
            print(f"Sample content: {clause.get('content', '')[:100]}...")
        else:
            print("❌ No clauses found")
    else:
        print(f"❌ Query failed: {response.status_code}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Check system info
    print("🔍 Test 2: System information")
    sys_response = requests.get("http://localhost:8000/system-info")
    if sys_response.status_code == 200:
        sys_info = sys_response.json()
        agents = sys_info.get('system_status', {}).get('agents', {})
        retrieval = agents.get('retrieval_agent', {})
        
        print(f"📊 Indexed documents: {retrieval.get('indexed_documents', 0)}")
        print(f"📚 Vector store size: {retrieval.get('vector_store_size', 0)}")
        
        if retrieval.get('indexed_documents', 0) > 0:
            print("✅ Documents are indexed in vector store")
        else:
            print("❌ No documents in vector store")

if __name__ == "__main__":
    test_direct_search()

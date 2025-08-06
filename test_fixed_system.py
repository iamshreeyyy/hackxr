#!/usr/bin/env python3
"""
Test the fixed system with the corrected similarity threshold
"""

import requests
import time
import json
from pathlib import Path

def test_fixed_system():
    """Test the system after fixing the similarity threshold configuration"""
    
    BASE_URL = "http://localhost:8001"
    
    print("🔧 Testing Fixed System with Similarity Threshold 0.3")
    print("=" * 60)
    
    # Check system health
    print("\n📋 1. Checking System Health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Health Status: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Get current system info
    print("\n📊 2. System Information Before Upload")
    try:
        response = requests.get(f"{BASE_URL}/system-info")
        system_info = response.json()
        print(f"   📄 Indexed documents: {system_info.get('indexed_documents', 0)}")
        print(f"   🔧 Similarity threshold: {system_info.get('similarity_threshold', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Upload the PDF
    pdf_path = Path("/home/shrey/Downloads/my_pdf/CHOTGDP23004V012223.pdf")
    
    print(f"\n📤 3. Uploading PDF: {pdf_path.name}")
    
    if not pdf_path.exists():
        print("   ❌ PDF file not found!")
        return
    
    try:
        with open(pdf_path, "rb") as f:
            files = {"files": (pdf_path.name, f, "application/pdf")}
            response = requests.post(f"{BASE_URL}/upload-documents", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Upload successful!")
            processing_time = result.get('processing_time', 0)
            if isinstance(processing_time, (int, float)):
                print(f"   📊 Processing time: {processing_time:.2f}s")
            else:
                print(f"   📊 Processing time: {processing_time}")
            print(f"   📝 Status: {result.get('status', 'N/A')}")
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return
    
    # Check system info after upload
    print("\n📊 4. System Information After Upload")
    try:
        response = requests.get(f"{BASE_URL}/system-info")
        system_info = response.json()
        print(f"   📄 Indexed documents: {system_info.get('indexed_documents', 0)}")
        print(f"   📚 Vector store size: {system_info.get('vector_store_size', 0)}")
        print(f"   🔧 Similarity threshold: {system_info.get('similarity_threshold', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test queries with the fixed system
    print("\n🔍 5. Testing Query Processing")
    
    test_queries = [
        "insurance coverage",
        "medical treatment",
        "hospital stay benefits",
        "policy benefits",
        "claim procedures"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Query {i}: '{query}'")
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={"query": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                source_clauses = len(result.get('source_clauses', []))
                decision = result.get('decision', {}).get('decision', 'N/A')
                confidence = result.get('decision', {}).get('confidence', 0)
                
                print(f"   📄 Source clauses found: {source_clauses}")
                print(f"   🎯 Decision: {decision} (confidence: {confidence:.2f})")
                
                # Show first source clause if found
                if source_clauses > 0:
                    first_clause = result['source_clauses'][0]
                    clause_text = first_clause.get('clause_text', '')[:200] + "..."
                    relevance = first_clause.get('relevance_score', 0)
                    print(f"   📋 First clause (score: {relevance:.3f}): {clause_text}")
                    print("   🎉 SUCCESS: Documents are being retrieved!")
                else:
                    print("   ⚠️  No source clauses found")
                    
            else:
                print(f"   ❌ Query failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Query error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Test Complete!")

if __name__ == "__main__":
    test_fixed_system()

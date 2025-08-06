#!/usr/bin/env python3
"""
Test script for the LLM Document Processing System
"""

import asyncio
import json
import time
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.agents.orchestrator import AgentOrchestrator

async def test_system():
    """Test the complete system functionality"""
    print("🧪 Testing LLM Document Processing System\n")
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()
    
    print("✅ System initialized\n")
    
    # Test 1: System health check
    print("1️⃣ Testing system health...")
    health = await orchestrator.health_check()
    print(f"   Status: {health['overall_status']}")
    if health['overall_status'] != 'healthy':
        print(f"   Issues: {health.get('error', 'Unknown')}")
    print()
    
    # Test 2: Create a sample document content for testing
    print("2️⃣ Testing document processing...")
    sample_document = """
    INSURANCE POLICY DOCUMENT
    
    Coverage Details:
    - Knee surgery is covered under orthopedic procedures
    - Maximum coverage amount: ₹2,00,000 per claim
    - Waiting period: 90 days from policy start date
    - Age limit: 18-75 years
    - Geographic coverage: Major cities in India including Mumbai, Delhi, Bangalore, Pune, Chennai
    
    Exclusions:
    - Cosmetic surgery is not covered
    - Pre-existing conditions have a 2-year waiting period
    
    Claim Process:
    - Pre-authorization required for surgeries above ₹50,000
    - Claims must be submitted within 30 days
    """
    
    # Create a temporary file for testing
    temp_file = Path("temp_policy.txt")
    temp_file.write_text(sample_document)
    
    try:
        result = await orchestrator.process_document(str(temp_file))
        if result['success']:
            print(f"   ✅ Document processed: {result['chunks']} chunks created")
        else:
            print(f"   ❌ Document processing failed: {result.get('error')}")
    finally:
        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()
    print()
    
    # Test 3: Process sample queries
    print("3️⃣ Testing query processing...")
    test_queries = [
        "46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
        "25-year-old female, cosmetic surgery, Mumbai, 6-month policy",
        "60M, cardiac surgery, Delhi, 2-year policy"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"   Query {i}: {query}")
        start_time = time.time()
        
        try:
            response = await orchestrator.process_query(query)
            processing_time = time.time() - start_time
            
            print(f"   Decision: {response['decision']}")
            print(f"   Confidence: {response['confidence_score']:.2f}")
            if response['amount']:
                print(f"   Amount: ₹{response['amount']:,.2f}")
            print(f"   Processing time: {processing_time:.2f}s")
            print(f"   Source clauses: {len(response['source_clauses'])}")
            
        except Exception as e:
            print(f"   ❌ Query processing failed: {str(e)}")
        
        print()
    
    # Test 4: System statistics
    print("4️⃣ System statistics...")
    stats = await orchestrator.get_system_status()
    print(f"   Queries processed: {stats['processing_stats']['queries_processed']}")
    print(f"   Documents processed: {stats['processing_stats']['documents_processed']}")
    print(f"   Decisions made: {stats['processing_stats']['decisions_made']}")
    print()
    
    print("🎉 All tests completed!")

def main():
    """Main test function"""
    try:
        asyncio.run(test_system())
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

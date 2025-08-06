"""
Agent Orchestrator
Coordinates all agents in the multi-agent RAG system
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
import logging

from src.utils.logger import setup_logger
from src.agents.document_parser import DocumentParserAgent
from src.agents.semantic_chunker import SemanticChunkerAgent
from src.agents.retrieval_agent import RetrievalAgent, RetrievalConfig
from src.agents.validation_agent import ValidationAgent
from src.agents.decision_agent import DecisionAgent
from src.agents.mapping_agent import MappingAgent
from src.config import get_settings

logger = setup_logger(__name__)
settings = get_settings()

class AgentOrchestrator:
    """
    Central orchestrator for the multi-agent system
    Coordinates workflow between all specialized agents
    """
    
    def __init__(self):
        # Initialize all agents
        self.document_parser = DocumentParserAgent()
        self.semantic_chunker = SemanticChunkerAgent()
        
        # Create retrieval config from settings
        retrieval_config = RetrievalConfig(
            dense_weight=settings.dense_weight,
            sparse_weight=settings.sparse_weight,
            max_results=settings.max_results,
            similarity_threshold=settings.similarity_threshold,
            rerank_results=True
        )
        self.retrieval_agent = RetrievalAgent(retrieval_config)
        
        self.validation_agent = ValidationAgent()
        self.decision_agent = DecisionAgent()
        self.mapping_agent = MappingAgent()
        
        # System state
        self.initialized = False
        self.processing_stats = {
            'documents_processed': 0,
            'queries_processed': 0,
            'decisions_made': 0,
            'total_processing_time': 0.0
        }
        
        logger.info("Agent Orchestrator initialized with all agents")
    
    async def initialize(self):
        """Initialize the orchestrator and all agents"""
        try:
            logger.info("Initializing multi-agent system...")
            
            # Any additional initialization logic for agents
            # Most agents initialize themselves in their constructors
            
            self.initialized = True
            logger.info("Multi-agent system initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing system: {str(e)}")
            raise
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            Processing result with statistics
        """
        if not self.initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Step 1: Parse document
            parsed_result = await self.document_parser.parse_document(file_path)
            if not parsed_result.get('success', False):
                logger.error(f"Document parsing failed for {file_path}")
                return {'success': False, 'error': 'Document parsing failed'}
            
            # Step 2: Create semantic chunks
            chunks = await self.semantic_chunker.create_chunks(
                parsed_result['content'], 
                file_path
            )
            
            if not chunks:
                logger.error(f"Semantic chunking failed for {file_path}")
                return {'success': False, 'error': 'Semantic chunking failed'}
            
            # Step 3: Add chunks to retrieval system
            success = await self.retrieval_agent.add_documents(chunks)
            if not success:
                logger.warning(f"Some chunks failed to be added to retrieval system")
            
            # Update statistics
            processing_time = time.time() - start_time
            self.processing_stats['documents_processed'] += 1
            self.processing_stats['total_processing_time'] += processing_time
            
            logger.info(f"Document processing completed in {processing_time:.2f}s")
            
            return {
                'success': True,
                'chunks': len(chunks),
                'processing_time': processing_time,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a query through the complete multi-agent pipeline
        
        Args:
            query: Natural language query
            
        Returns:
            Complete response with decision and traceability
        """
        if not self.initialized:
            await self.initialize()
        
        start_time = time.time()
        decision_path = []
        
        try:
            logger.info(f"Processing query: {query}")
            
            # Step 1: Parse query and extract entities
            decision_path.append({
                'step': 'query_parsing',
                'timestamp': time.time(),
                'status': 'started'
            })
            
            parsed_query = await self.retrieval_agent.query_parser.parse_query(query)
            entities = parsed_query.get('entities', {})
            
            decision_path[-1].update({
                'status': 'completed',
                'entities_extracted': len(entities)
            })
            
            logger.info(f"Extracted entities: {entities}")
            
            # Step 2: Retrieve relevant documents
            decision_path.append({
                'step': 'document_retrieval',
                'timestamp': time.time(),
                'status': 'started'
            })
            
            source_clauses = await self.retrieval_agent.retrieve_relevant_documents(query)
            
            decision_path[-1].update({
                'status': 'completed',
                'clauses_retrieved': len(source_clauses)
            })
            
            logger.info(f"Retrieved {len(source_clauses)} relevant clauses")
            
            # Step 3: Validate against policy rules
            decision_path.append({
                'step': 'policy_validation',
                'timestamp': time.time(),
                'status': 'started'
            })
            
            validation_result = await self.validation_agent.validate_claim(entities, source_clauses)
            
            decision_path[-1].update({
                'status': 'completed',
                'rules_satisfied': len(validation_result.satisfied_rules),
                'rules_violated': len(validation_result.violated_rules)
            })
            
            logger.info(f"Validation completed - Valid: {validation_result.is_valid}")
            
            # Step 4: Make decision
            decision_path.append({
                'step': 'decision_making',
                'timestamp': time.time(),
                'status': 'started'
            })
            
            decision_result = await self.decision_agent.make_decision(
                entities, source_clauses, validation_result, parsed_query.get('context', {}).get('question_type', 'general')
            )
            
            decision_path[-1].update({
                'status': 'completed',
                'decision': decision_result.decision,
                'confidence': decision_result.confidence_score
            })
            
            logger.info(f"Decision made: {decision_result.decision} (confidence: {decision_result.confidence_score:.2f})")
            
            # Step 5: Create traceability mapping
            decision_path.append({
                'step': 'traceability_mapping',
                'timestamp': time.time(),
                'status': 'started'
            })
            
            trace_id = await self.mapping_agent.create_decision_trace(
                query, entities, decision_result, source_clauses, decision_path
            )
            
            decision_path[-1].update({
                'status': 'completed',
                'trace_id': trace_id
            })
            
            # Calculate total processing time
            processing_time = time.time() - start_time
            
            # Update statistics
            self.processing_stats['queries_processed'] += 1
            self.processing_stats['decisions_made'] += 1
            self.processing_stats['total_processing_time'] += processing_time
            
            # Compile final response
            response = {
                'decision': decision_result.decision,
                'amount': decision_result.amount,
                'justification': decision_result.justification,
                'confidence_score': decision_result.confidence_score,
                'source_clauses': [
                    {
                        'document_name': clause.document_name,
                        'clause_id': clause.clause_id,
                        'clause_text': clause.clause_text,
                        'relevance_score': clause.relevance_score,
                        'page_number': clause.page_number
                    } for clause in source_clauses
                ],
                'processing_time': processing_time,
                'trace_id': trace_id,
                'entities': entities,
                'validation_summary': {
                    'is_valid': validation_result.is_valid,
                    'satisfied_rules': validation_result.satisfied_rules,
                    'violated_rules': validation_result.violated_rules,
                    'warnings': validation_result.warnings
                }
            }
            
            logger.info(f"Query processing completed in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            processing_time = time.time() - start_time
            
            return {
                'decision': 'error',
                'amount': None,
                'justification': f'Error processing query: {str(e)}',
                'confidence_score': 0.0,
                'source_clauses': [],
                'processing_time': processing_time,
                'trace_id': None,
                'entities': {},
                'validation_summary': {
                    'is_valid': False,
                    'satisfied_rules': [],
                    'violated_rules': ['system_error'],
                    'warnings': [str(e)]
                }
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get status of all agents in the system"""
        try:
            # Get individual agent statistics
            retrieval_stats = await self.retrieval_agent.get_statistics()
            validation_stats = self.validation_agent.get_rule_statistics()
            decision_stats = self.decision_agent.get_decision_statistics()
            mapping_stats = self.mapping_agent.get_mapping_statistics()
            
            return {
                'system_initialized': self.initialized,
                'agents': {
                    'document_parser': {'status': 'active'},
                    'semantic_chunker': {'status': 'active'},
                    'retrieval_agent': {
                        'status': 'active',
                        'indexed_documents': retrieval_stats.get('total_documents', 0),
                        'vector_store_size': retrieval_stats.get('vector_store_size', 0)
                    },
                    'validation_agent': {
                        'status': 'active',
                        'total_rules': validation_stats.get('total_rules', 0),
                        'rule_types': list(validation_stats.get('rule_types', {}).keys())
                    },
                    'decision_agent': {
                        'status': 'active',
                        'total_decisions': decision_stats.get('total_decisions', 0),
                        'average_confidence': decision_stats.get('average_confidence', 0)
                    },
                    'mapping_agent': {
                        'status': 'active',
                        'total_traces': mapping_stats.get('total_traces', 0),
                        'total_links': mapping_stats.get('total_links', 0)
                    }
                },
                'processing_stats': self.processing_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {'error': str(e)}
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""
        try:
            system_status = await self.get_system_status()
            
            # Add additional system info
            system_info = {
                'system_version': '1.0.0',
                'system_status': system_status,
                'capabilities': [
                    'multi_format_document_parsing',
                    'semantic_aware_chunking',
                    'hybrid_vector_search',
                    'dynamic_rule_validation',
                    'explainable_decisions',
                    'bidirectional_traceability'
                ],
                'supported_file_types': ['.pdf', '.docx', '.doc', '.txt'],
                'supported_query_types': [
                    'eligibility_check',
                    'coverage_inquiry',
                    'claim_validation',
                    'policy_interpretation'
                ]
            }
            
            return system_info
            
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {'error': str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health_status = {
            'overall_status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            # Check initialization
            health_status['checks']['initialization'] = {
                'status': 'pass' if self.initialized else 'fail',
                'message': 'System initialized' if self.initialized else 'System not initialized'
            }
            
            # Check agent availability
            agents = [
                ('document_parser', self.document_parser),
                ('semantic_chunker', self.semantic_chunker),
                ('retrieval_agent', self.retrieval_agent),
                ('validation_agent', self.validation_agent),
                ('decision_agent', self.decision_agent),
                ('mapping_agent', self.mapping_agent)
            ]
            
            for agent_name, agent in agents:
                try:
                    # Simple check - agent should have required methods
                    health_status['checks'][agent_name] = {
                        'status': 'pass',
                        'message': f'{agent_name} is available'
                    }
                except Exception as e:
                    health_status['checks'][agent_name] = {
                        'status': 'fail',
                        'message': f'{agent_name} error: {str(e)}'
                    }
                    health_status['overall_status'] = 'degraded'
            
            # Check processing statistics
            if self.processing_stats['queries_processed'] == 0:
                health_status['checks']['processing'] = {
                    'status': 'warning',
                    'message': 'No queries processed yet'
                }
            else:
                avg_processing_time = (self.processing_stats['total_processing_time'] / 
                                     self.processing_stats['queries_processed'])
                health_status['checks']['processing'] = {
                    'status': 'pass',
                    'message': f'Average processing time: {avg_processing_time:.2f}s'
                }
            
        except Exception as e:
            health_status['overall_status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
    
    async def reset_system(self):
        """Reset the system state (for testing/development)"""
        logger.warning("Resetting system state...")
        
        # Reset statistics
        self.processing_stats = {
            'documents_processed': 0,
            'queries_processed': 0,
            'decisions_made': 0,
            'total_processing_time': 0.0
        }
        
        # Reinitialize agents if needed
        self.initialized = False
        await self.initialize()
        
        logger.info("System reset completed")
    
    async def shutdown(self):
        """Graceful system shutdown"""
        logger.info("Shutting down multi-agent system...")
        
        try:
            # Save any pending data or cleanup
            # Individual agents may have cleanup methods
            
            self.initialized = False
            logger.info("System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            raise

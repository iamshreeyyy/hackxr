"""
Mapping Agent
Maintains bidirectional traceability between decisions and source documents
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from src.utils.logger import setup_logger
from src.models.schemas import SourceClause
from src.agents.decision_agent import DecisionResult

logger = setup_logger(__name__)

@dataclass
class TraceabilityLink:
    """Represents a link between decision and source"""
    link_id: str
    decision_id: str
    source_clause_id: str
    relationship_type: str  # 'supports', 'contradicts', 'references', 'validates'
    strength: float  # 0.0 to 1.0
    explanation: str
    timestamp: datetime

@dataclass
class DecisionTrace:
    """Complete trace of a decision"""
    trace_id: str
    query: str
    decision: str
    entities: Dict[str, Any]
    confidence_score: float
    source_links: List[TraceabilityLink]
    decision_path: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime

class DocumentIndex:
    """Index for fast document and clause retrieval"""
    
    def __init__(self):
        self.clause_index: Dict[str, Dict[str, Any]] = {}
        self.document_index: Dict[str, List[str]] = {}  # document -> clause_ids
        self.decision_index: Dict[str, List[str]] = {}  # decision_id -> clause_ids
        
    def add_clause(self, clause: SourceClause):
        """Add clause to index"""
        self.clause_index[clause.clause_id] = {
            'document_name': clause.document_name,
            'clause_text': clause.clause_text,
            'relevance_score': clause.relevance_score,
            'page_number': clause.page_number,
            'metadata': {
                'indexed_at': datetime.now().isoformat(),
                'word_count': len(clause.clause_text.split()),
                'char_count': len(clause.clause_text)
            }
        }
        
        # Update document index
        if clause.document_name not in self.document_index:
            self.document_index[clause.document_name] = []
        if clause.clause_id not in self.document_index[clause.document_name]:
            self.document_index[clause.document_name].append(clause.clause_id)
    
    def get_clause(self, clause_id: str) -> Optional[Dict[str, Any]]:
        """Get clause by ID"""
        return self.clause_index.get(clause_id)
    
    def get_clauses_by_document(self, document_name: str) -> List[str]:
        """Get all clause IDs for a document"""
        return self.document_index.get(document_name, [])
    
    def get_clauses_by_decision(self, decision_id: str) -> List[str]:
        """Get all clause IDs linked to a decision"""
        return self.decision_index.get(decision_id, [])
    
    def link_decision_to_clauses(self, decision_id: str, clause_ids: List[str]):
        """Link decision to clauses"""
        self.decision_index[decision_id] = clause_ids

class MappingAgent:
    """
    Mapping Agent
    Maintains bidirectional traceability between decisions and source documents
    """
    
    def __init__(self):
        self.document_index = DocumentIndex()
        self.decision_traces: Dict[str, DecisionTrace] = {}
        self.traceability_links: Dict[str, TraceabilityLink] = {}
        self.audit_log: List[Dict[str, Any]] = []
        logger.info("Mapping Agent initialized")
    
    async def create_decision_trace(self, query: str, entities: Dict[str, Any], 
                                   decision_result: DecisionResult, 
                                   source_clauses: List[SourceClause],
                                   decision_path: List[Dict[str, Any]]) -> str:
        """
        Create a complete trace for a decision
        
        Args:
            query: Original query
            entities: Extracted entities
            decision_result: Decision result
            source_clauses: Source clauses used
            decision_path: Path of decision making process
            
        Returns:
            Trace ID for the created trace
        """
        try:
            trace_id = str(uuid.uuid4())
            decision_id = str(uuid.uuid4())
            
            # Index all source clauses
            for clause in source_clauses:
                self.document_index.add_clause(clause)
            
            # Create traceability links
            source_links = []
            clause_ids = []
            
            for clause in source_clauses:
                link = await self._create_traceability_link(
                    decision_id, clause, decision_result
                )
                source_links.append(link)
                self.traceability_links[link.link_id] = link
                clause_ids.append(clause.clause_id)
            
            # Link decision to clauses in index
            self.document_index.link_decision_to_clauses(decision_id, clause_ids)
            
            # Create decision trace
            decision_trace = DecisionTrace(
                trace_id=trace_id,
                query=query,
                decision=decision_result.decision,
                entities=entities,
                confidence_score=decision_result.confidence_score,
                source_links=source_links,
                decision_path=decision_path,
                metadata={
                    'decision_id': decision_id,
                    'amount': decision_result.amount,
                    'risk_assessment': decision_result.risk_assessment,
                    'processing_timestamp': datetime.now().isoformat()
                },
                timestamp=datetime.now()
            )
            
            # Store trace
            self.decision_traces[trace_id] = decision_trace
            
            # Log audit event
            await self._log_audit_event('decision_trace_created', {
                'trace_id': trace_id,
                'decision_id': decision_id,
                'decision': decision_result.decision,
                'source_clauses_count': len(source_clauses)
            })
            
            logger.info(f"Created decision trace {trace_id} for decision {decision_result.decision}")
            return trace_id
            
        except Exception as e:
            logger.error(f"Error creating decision trace: {str(e)}")
            return ""
    
    async def _create_traceability_link(self, decision_id: str, clause: SourceClause, 
                                       decision_result: DecisionResult) -> TraceabilityLink:
        """Create a traceability link between decision and clause"""
        link_id = str(uuid.uuid4())
        
        # Determine relationship type and strength
        relationship_type, strength, explanation = await self._analyze_clause_relationship(
            clause, decision_result
        )
        
        return TraceabilityLink(
            link_id=link_id,
            decision_id=decision_id,
            source_clause_id=clause.clause_id,
            relationship_type=relationship_type,
            strength=strength,
            explanation=explanation,
            timestamp=datetime.now()
        )
    
    async def _analyze_clause_relationship(self, clause: SourceClause, 
                                         decision: DecisionResult) -> Tuple[str, float, str]:
        """Analyze relationship between clause and decision"""
        clause_text = clause.clause_text.lower()
        decision_outcome = decision.decision.lower()
        
        # Analyze clause content for relationship indicators
        supports_keywords = ['covered', 'eligible', 'benefits', 'approved', 'included']
        contradicts_keywords = ['excluded', 'not covered', 'denied', 'prohibited', 'limitation']
        validates_keywords = ['must', 'required', 'shall', 'conditions', 'criteria']
        
        supports_count = sum(1 for keyword in supports_keywords if keyword in clause_text)
        contradicts_count = sum(1 for keyword in contradicts_keywords if keyword in clause_text)
        validates_count = sum(1 for keyword in validates_keywords if keyword in clause_text)
        
        # Determine relationship type
        if decision_outcome == 'approved':
            if supports_count > contradicts_count:
                relationship_type = 'supports'
                strength = min(1.0, clause.relevance_score + 0.2)
                explanation = f"Clause contains {supports_count} supportive terms for approved decision"
            elif contradicts_count > supports_count:
                relationship_type = 'contradicts'
                strength = clause.relevance_score
                explanation = f"Clause contains {contradicts_count} contradictory terms despite approval"
            else:
                relationship_type = 'validates'
                strength = clause.relevance_score
                explanation = "Clause provides validation criteria for decision"
        
        elif decision_outcome == 'rejected':
            if contradicts_count > supports_count:
                relationship_type = 'supports'
                strength = min(1.0, clause.relevance_score + 0.2)
                explanation = f"Clause contains {contradicts_count} exclusionary terms supporting rejection"
            elif supports_count > contradicts_count:
                relationship_type = 'contradicts'
                strength = clause.relevance_score
                explanation = f"Clause contains {supports_count} supportive terms despite rejection"
            else:
                relationship_type = 'validates'
                strength = clause.relevance_score
                explanation = "Clause provides validation criteria for decision"
        
        else:  # pending, requires_review
            if validates_count > 0:
                relationship_type = 'validates'
                strength = clause.relevance_score
                explanation = f"Clause contains {validates_count} validation requirements"
            else:
                relationship_type = 'references'
                strength = clause.relevance_score * 0.8
                explanation = "Clause provides reference information for decision"
        
        return relationship_type, strength, explanation
    
    async def get_decision_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """Get decision trace by ID"""
        return self.decision_traces.get(trace_id)
    
    async def get_source_clauses_for_decision(self, decision_id: str) -> List[Dict[str, Any]]:
        """Get all source clauses that influenced a decision"""
        clause_ids = self.document_index.get_clauses_by_decision(decision_id)
        clauses = []
        
        for clause_id in clause_ids:
            clause_data = self.document_index.get_clause(clause_id)
            if clause_data:
                # Add traceability information
                links = [link for link in self.traceability_links.values() 
                        if link.source_clause_id == clause_id and link.decision_id == decision_id]
                
                clause_data['traceability_links'] = [
                    {
                        'relationship_type': link.relationship_type,
                        'strength': link.strength,
                        'explanation': link.explanation
                    } for link in links
                ]
                clauses.append(clause_data)
        
        return clauses
    
    async def get_decisions_using_clause(self, clause_id: str) -> List[Dict[str, Any]]:
        """Get all decisions that used a specific clause"""
        related_links = [link for link in self.traceability_links.values() 
                        if link.source_clause_id == clause_id]
        
        decisions = []
        for link in related_links:
            # Find the trace containing this decision
            trace = next((trace for trace in self.decision_traces.values() 
                         if trace.metadata.get('decision_id') == link.decision_id), None)
            
            if trace:
                decisions.append({
                    'trace_id': trace.trace_id,
                    'decision': trace.decision,
                    'query': trace.query,
                    'confidence_score': trace.confidence_score,
                    'relationship_type': link.relationship_type,
                    'relationship_strength': link.strength,
                    'timestamp': trace.timestamp.isoformat()
                })
        
        return decisions
    
    async def generate_audit_report(self, start_date: Optional[datetime] = None, 
                                   end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate audit report for traceability"""
        if start_date is None:
            start_date = datetime.min
        if end_date is None:
            end_date = datetime.max
        
        # Filter traces by date range
        filtered_traces = [
            trace for trace in self.decision_traces.values()
            if start_date <= trace.timestamp <= end_date
        ]
        
        # Calculate statistics
        decision_stats = {}
        for trace in filtered_traces:
            decision = trace.decision
            decision_stats[decision] = decision_stats.get(decision, 0) + 1
        
        # Analyze traceability strength
        link_strengths = [link.strength for link in self.traceability_links.values()]
        avg_link_strength = sum(link_strengths) / len(link_strengths) if link_strengths else 0
        
        # Find most referenced documents
        document_usage = {}
        for clause_id, clause_data in self.document_index.clause_index.items():
            doc_name = clause_data['document_name']
            document_usage[doc_name] = document_usage.get(doc_name, 0) + 1
        
        return {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_decisions': len(filtered_traces),
                'total_clauses_indexed': len(self.document_index.clause_index),
                'total_documents': len(self.document_index.document_index),
                'total_traceability_links': len(self.traceability_links),
                'average_link_strength': avg_link_strength
            },
            'decision_statistics': decision_stats,
            'document_usage': sorted(document_usage.items(), key=lambda x: x[1], reverse=True),
            'traceability_coverage': self._calculate_traceability_coverage(),
            'audit_events': len(self.audit_log)
        }
    
    def _calculate_traceability_coverage(self) -> Dict[str, float]:
        """Calculate traceability coverage metrics"""
        total_decisions = len(self.decision_traces)
        decisions_with_traces = sum(1 for trace in self.decision_traces.values() 
                                  if len(trace.source_links) > 0)
        
        total_clauses = len(self.document_index.clause_index)
        clauses_with_decisions = len(set(link.source_clause_id 
                                        for link in self.traceability_links.values()))
        
        return {
            'decision_coverage': decisions_with_traces / total_decisions if total_decisions > 0 else 0,
            'clause_coverage': clauses_with_decisions / total_clauses if total_clauses > 0 else 0
        }
    
    async def _log_audit_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log audit event"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'event_data': event_data,
            'agent': 'mapping_agent'
        }
        
        self.audit_log.append(audit_entry)
        
        # Keep only last 10000 audit events
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
    
    async def export_trace_data(self, trace_id: str) -> Dict[str, Any]:
        """Export complete trace data for external analysis"""
        trace = self.decision_traces.get(trace_id)
        if not trace:
            return {}
        
        # Get linked clauses with full details
        linked_clauses = []
        for link in trace.source_links:
            clause_data = self.document_index.get_clause(link.source_clause_id)
            if clause_data:
                linked_clauses.append({
                    **clause_data,
                    'link_details': {
                        'relationship_type': link.relationship_type,
                        'strength': link.strength,
                        'explanation': link.explanation
                    }
                })
        
        return {
            'trace': asdict(trace),
            'linked_clauses': linked_clauses,
            'export_timestamp': datetime.now().isoformat()
        }
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get mapping agent statistics"""
        return {
            'total_traces': len(self.decision_traces),
            'total_links': len(self.traceability_links),
            'indexed_clauses': len(self.document_index.clause_index),
            'indexed_documents': len(self.document_index.document_index),
            'audit_events': len(self.audit_log),
            'link_type_distribution': self._get_link_type_distribution()
        }
    
    def _get_link_type_distribution(self) -> Dict[str, int]:
        """Get distribution of link types"""
        distribution = {}
        for link in self.traceability_links.values():
            link_type = link.relationship_type
            distribution[link_type] = distribution.get(link_type, 0) + 1
        return distribution

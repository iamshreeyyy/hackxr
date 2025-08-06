"""
Decision Agent
Generates explainable decisions with clause-level justification
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

from src.utils.logger import setup_logger
from src.models.schemas import SourceClause
from src.agents.validation_agent import ValidationResult

logger = setup_logger(__name__)

@dataclass
class DecisionContext:
    """Context for decision making"""
    entities: Dict[str, Any]
    source_clauses: List[SourceClause]
    validation_result: ValidationResult
    query_type: str
    urgency_level: str = "normal"

@dataclass
class DecisionResult:
    """Result of decision making process"""
    decision: str
    confidence_score: float
    amount: Optional[float]
    justification: str
    decision_factors: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]

class DecisionRules:
    """Decision making rules and logic"""
    
    @staticmethod
    def evaluate_coverage_decision(context: DecisionContext) -> DecisionResult:
        """Evaluate coverage decision based on validation and clauses"""
        decision_factors = []
        confidence_components = []
        risk_factors = []
        
        # Factor 1: Validation results
        validation_factor = DecisionRules._evaluate_validation_factor(context.validation_result)
        decision_factors.append(validation_factor)
        confidence_components.append(validation_factor['confidence_impact'])
        
        # Factor 2: Source clause support
        clause_factor = DecisionRules._evaluate_clause_support(context.source_clauses, context.entities)
        decision_factors.append(clause_factor)
        confidence_components.append(clause_factor['confidence_impact'])
        
        # Factor 3: Entity completeness
        entity_factor = DecisionRules._evaluate_entity_completeness(context.entities)
        decision_factors.append(entity_factor)
        confidence_components.append(entity_factor['confidence_impact'])
        
        # Factor 4: Risk assessment
        risk_assessment = DecisionRules._assess_risk(context)
        risk_factors = risk_assessment['factors']
        
        # Make final decision
        overall_confidence = sum(confidence_components) / len(confidence_components)
        
        # Decision logic
        if context.validation_result.is_valid and clause_factor['supports_coverage']:
            decision = "approved"
            confidence_modifier = 0.1
        elif not context.validation_result.is_valid and len(context.validation_result.violated_rules) > 2:
            decision = "rejected"
            confidence_modifier = 0.1
        elif len(context.validation_result.warnings) > 0:
            decision = "requires_review"
            confidence_modifier = -0.2
        else:
            decision = "pending"
            confidence_modifier = -0.15
        
        final_confidence = max(0.0, min(1.0, overall_confidence + confidence_modifier))
        
        # Calculate amount if applicable
        amount = DecisionRules._calculate_coverage_amount(context) if decision == "approved" else None
        
        # Generate justification
        justification = DecisionRules._generate_justification(
            decision, decision_factors, context.validation_result, context.source_clauses
        )
        
        return DecisionResult(
            decision=decision,
            confidence_score=final_confidence,
            amount=amount,
            justification=justification,
            decision_factors=decision_factors,
            risk_assessment=risk_assessment
        )
    
    @staticmethod
    def _evaluate_validation_factor(validation_result: ValidationResult) -> Dict[str, Any]:
        """Evaluate the impact of validation results on decision"""
        if validation_result.is_valid:
            return {
                'factor_name': 'validation_compliance',
                'status': 'positive',
                'confidence_impact': 0.8,
                'description': 'All validation rules satisfied',
                'details': {
                    'satisfied_rules': len(validation_result.satisfied_rules),
                    'violated_rules': len(validation_result.violated_rules)
                }
            }
        else:
            critical_violations = [rule for rule in validation_result.violated_rules 
                                 if 'age' in rule.lower() or 'excluded' in rule.lower()]
            
            if critical_violations:
                confidence_impact = 0.2
                status = 'negative'
            else:
                confidence_impact = 0.5
                status = 'cautionary'
            
            return {
                'factor_name': 'validation_compliance',
                'status': status,
                'confidence_impact': confidence_impact,
                'description': f'{len(validation_result.violated_rules)} validation rules violated',
                'details': {
                    'violated_rules': validation_result.violated_rules,
                    'critical_violations': critical_violations
                }
            }
    
    @staticmethod
    def _evaluate_clause_support(clauses: List[SourceClause], entities: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate how well source clauses support the claim"""
        if not clauses:
            return {
                'factor_name': 'clause_support',
                'status': 'negative',
                'confidence_impact': 0.3,
                'supports_coverage': False,
                'description': 'No relevant policy clauses found'
            }
        
        # Analyze clauses for coverage support
        positive_clauses = []
        negative_clauses = []
        neutral_clauses = []
        
        for clause in clauses:
            clause_analysis = DecisionRules._analyze_clause_sentiment(clause, entities)
            
            if clause_analysis['sentiment'] == 'positive':
                positive_clauses.append(clause_analysis)
            elif clause_analysis['sentiment'] == 'negative':
                negative_clauses.append(clause_analysis)
            else:
                neutral_clauses.append(clause_analysis)
        
        # Determine overall support
        if len(positive_clauses) > len(negative_clauses):
            supports_coverage = True
            confidence_impact = 0.7 + (len(positive_clauses) * 0.1)
            status = 'positive'
            description = f'{len(positive_clauses)} clauses support coverage'
        elif len(negative_clauses) > len(positive_clauses):
            supports_coverage = False
            confidence_impact = 0.3
            status = 'negative'
            description = f'{len(negative_clauses)} clauses indicate exclusion'
        else:
            supports_coverage = False
            confidence_impact = 0.5
            status = 'neutral'
            description = 'Mixed or unclear clause support'
        
        return {
            'factor_name': 'clause_support',
            'status': status,
            'confidence_impact': min(1.0, confidence_impact),
            'supports_coverage': supports_coverage,
            'description': description,
            'details': {
                'positive_clauses': len(positive_clauses),
                'negative_clauses': len(negative_clauses),
                'neutral_clauses': len(neutral_clauses),
                'highest_relevance': max([c.relevance_score for c in clauses])
            }
        }
    
    @staticmethod
    def _analyze_clause_sentiment(clause: SourceClause, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze if a clause is positive, negative, or neutral for coverage"""
        text = clause.clause_text.lower()
        
        # Positive indicators
        positive_terms = ['covered', 'eligible', 'benefits', 'included', 'reimburse', 'approved']
        negative_terms = ['excluded', 'not covered', 'limitation', 'restricted', 'denied']
        
        positive_score = sum(1 for term in positive_terms if term in text)
        negative_score = sum(1 for term in negative_terms if term in text)
        
        # Check if specific entities are mentioned
        entity_mentioned = any(str(value).lower() in text for value in entities.values() if isinstance(value, str))
        
        if entity_mentioned:
            if positive_score > negative_score:
                sentiment = 'positive'
            elif negative_score > positive_score:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
        else:
            sentiment = 'neutral'
        
        return {
            'clause_id': clause.clause_id,
            'sentiment': sentiment,
            'positive_score': positive_score,
            'negative_score': negative_score,
            'entity_mentioned': entity_mentioned,
            'relevance_score': clause.relevance_score
        }
    
    @staticmethod
    def _evaluate_entity_completeness(entities: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate completeness of extracted entities"""
        required_entities = ['age', 'procedure']
        optional_entities = ['gender', 'location', 'policy_duration']
        
        present_required = sum(1 for entity in required_entities if entity in entities and entities[entity])
        present_optional = sum(1 for entity in optional_entities if entity in entities and entities[entity])
        
        completeness_score = (present_required / len(required_entities)) * 0.8 + \
                           (present_optional / len(optional_entities)) * 0.2
        
        if completeness_score >= 0.8:
            status = 'complete'
            confidence_impact = 0.9
        elif completeness_score >= 0.6:
            status = 'adequate'
            confidence_impact = 0.7
        else:
            status = 'incomplete'
            confidence_impact = 0.4
        
        return {
            'factor_name': 'entity_completeness',
            'status': status,
            'confidence_impact': confidence_impact,
            'description': f'Entity completeness: {completeness_score:.1%}',
            'details': {
                'required_entities_present': present_required,
                'optional_entities_present': present_optional,
                'missing_required': [e for e in required_entities if e not in entities or not entities[e]],
                'completeness_score': completeness_score
            }
        }
    
    @staticmethod
    def _assess_risk(context: DecisionContext) -> Dict[str, Any]:
        """Assess risk factors in the decision"""
        risk_factors = []
        overall_risk = "low"
        
        # Age-based risk
        if 'age' in context.entities:
            age = int(str(context.entities['age']).split()[0]) if context.entities['age'] else 0
            if age > 70:
                risk_factors.append({
                    'type': 'age_risk',
                    'level': 'high',
                    'description': 'Advanced age increases claim probability'
                })
                overall_risk = "high"
            elif age < 25:
                risk_factors.append({
                    'type': 'age_risk',
                    'level': 'low',
                    'description': 'Young age reduces claim probability'
                })
        
        # Procedure-based risk
        if 'procedure' in context.entities:
            procedure = str(context.entities['procedure']).lower()
            high_risk_procedures = ['surgery', 'cardiac', 'brain', 'cancer', 'transplant']
            
            if any(proc in procedure for proc in high_risk_procedures):
                risk_factors.append({
                    'type': 'procedure_risk',
                    'level': 'high',
                    'description': 'High-risk medical procedure'
                })
                overall_risk = "high"
        
        # Policy duration risk
        if 'policy_duration' in context.entities:
            duration_str = str(context.entities['policy_duration']).lower()
            if 'month' in duration_str:
                months = int(''.join(filter(str.isdigit, duration_str)) or '0')
                if months < 6:
                    risk_factors.append({
                        'type': 'policy_duration_risk',
                        'level': 'medium',
                        'description': 'New policy with limited duration'
                    })
                    if overall_risk == "low":
                        overall_risk = "medium"
        
        return {
            'overall_risk': overall_risk,
            'factors': risk_factors,
            'risk_score': len([f for f in risk_factors if f['level'] == 'high']) * 0.3 + \
                         len([f for f in risk_factors if f['level'] == 'medium']) * 0.2
        }
    
    @staticmethod
    def _calculate_coverage_amount(context: DecisionContext) -> Optional[float]:
        """Calculate coverage amount based on procedure and policy"""
        if 'procedure' not in context.entities:
            return None
        
        procedure = str(context.entities['procedure']).lower()
        
        # Base amounts by procedure type (simplified)
        procedure_amounts = {
            'knee': 150000,
            'hip': 200000,
            'cardiac': 500000,
            'surgery': 100000,
            'dental': 25000,
            'eye': 50000
        }
        
        base_amount = 75000  # Default amount
        for proc_type, amount in procedure_amounts.items():
            if proc_type in procedure:
                base_amount = amount
                break
        
        # Apply age factor
        if 'age' in context.entities:
            age = int(str(context.entities['age']).split()[0]) if context.entities['age'] else 40
            if age > 60:
                base_amount *= 1.2  # Higher coverage for older patients
            elif age < 30:
                base_amount *= 0.9  # Lower coverage for younger patients
        
        return round(base_amount, 2)
    
    @staticmethod
    def _generate_justification(decision: str, factors: List[Dict[str, Any]], 
                               validation: ValidationResult, clauses: List[SourceClause]) -> str:
        """Generate detailed justification for the decision"""
        justification_parts = []
        
        # Decision summary
        decision_summary = {
            'approved': 'The claim has been APPROVED based on policy analysis.',
            'rejected': 'The claim has been REJECTED due to policy violations.',
            'requires_review': 'The claim REQUIRES MANUAL REVIEW due to policy ambiguities.',
            'pending': 'The claim is PENDING additional information or clarification.'
        }
        
        justification_parts.append(decision_summary.get(decision, 'Decision status unclear.'))
        
        # Add key factors
        justification_parts.append("\nKey Decision Factors:")
        for factor in factors:
            if factor['status'] == 'positive':
                justification_parts.append(f"✓ {factor['description']}")
            elif factor['status'] == 'negative':
                justification_parts.append(f"✗ {factor['description']}")
            else:
                justification_parts.append(f"• {factor['description']}")
        
        # Add validation details
        if validation.violated_rules:
            justification_parts.append(f"\nPolicy Violations: {', '.join(validation.violated_rules)}")
        
        if validation.satisfied_rules:
            justification_parts.append(f"Satisfied Requirements: {', '.join(validation.satisfied_rules[:3])}")
        
        # Add supporting clauses
        if clauses:
            relevant_clauses = sorted(clauses, key=lambda x: x.relevance_score, reverse=True)[:2]
            justification_parts.append(f"\nSupporting Policy Clauses:")
            for i, clause in enumerate(relevant_clauses, 1):
                justification_parts.append(
                    f"{i}. {clause.document_name} (Relevance: {clause.relevance_score:.2f}): "
                    f"{clause.clause_text[:100]}..."
                )
        
        # Add warnings if any
        if validation.warnings:
            justification_parts.append(f"\nWarnings: {', '.join(validation.warnings)}")
        
        return '\n'.join(justification_parts)

class DecisionAgent:
    """
    Decision Agent
    Generates explainable decisions with clause-level justification
    """
    
    def __init__(self):
        self.decision_history: List[Dict[str, Any]] = []
        logger.info("Decision Agent initialized")
    
    async def make_decision(self, entities: Dict[str, Any], source_clauses: List[SourceClause], 
                          validation_result: ValidationResult, query_type: str = "coverage") -> DecisionResult:
        """
        Make a decision based on all available information
        
        Args:
            entities: Extracted entities from query
            source_clauses: Relevant policy clauses
            validation_result: Result from validation agent
            query_type: Type of query (coverage, financial, etc.)
            
        Returns:
            DecisionResult with detailed justification
        """
        try:
            # Create decision context
            context = DecisionContext(
                entities=entities,
                source_clauses=source_clauses,
                validation_result=validation_result,
                query_type=query_type
            )
            
            # Make decision using rules engine
            decision_result = DecisionRules.evaluate_coverage_decision(context)
            
            # Record decision in history
            self._record_decision(entities, decision_result, query_type)
            
            logger.info(f"Decision made: {decision_result.decision} (confidence: {decision_result.confidence_score:.2f})")
            return decision_result
            
        except Exception as e:
            logger.error(f"Error making decision: {str(e)}")
            # Return default rejection decision
            return DecisionResult(
                decision="rejected",
                confidence_score=0.0,
                amount=None,
                justification=f"Error in decision processing: {str(e)}",
                decision_factors=[],
                risk_assessment={'overall_risk': 'unknown', 'factors': []}
            )
    
    def _record_decision(self, entities: Dict[str, Any], decision: DecisionResult, query_type: str):
        """Record decision for audit trail"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'entities': entities,
            'decision': decision.decision,
            'confidence': decision.confidence_score,
            'query_type': query_type,
            'amount': decision.amount
        }
        
        self.decision_history.append(record)
        
        # Keep only last 1000 decisions
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
    
    async def explain_decision(self, decision_result: DecisionResult) -> Dict[str, Any]:
        """
        Provide detailed explanation of decision
        
        Args:
            decision_result: Decision result to explain
            
        Returns:
            Detailed explanation with breakdown
        """
        explanation = {
            'decision_summary': {
                'outcome': decision_result.decision,
                'confidence': decision_result.confidence_score,
                'amount': decision_result.amount
            },
            'decision_factors': decision_result.decision_factors,
            'risk_assessment': decision_result.risk_assessment,
            'justification': decision_result.justification,
            'confidence_breakdown': self._analyze_confidence_factors(decision_result)
        }
        
        return explanation
    
    def _analyze_confidence_factors(self, decision: DecisionResult) -> Dict[str, Any]:
        """Analyze what contributed to the confidence score"""
        factors = decision.decision_factors
        
        confidence_contributors = []
        confidence_detractors = []
        
        for factor in factors:
            if factor['confidence_impact'] > 0.6:
                confidence_contributors.append({
                    'factor': factor['factor_name'],
                    'impact': factor['confidence_impact'],
                    'description': factor['description']
                })
            elif factor['confidence_impact'] < 0.5:
                confidence_detractors.append({
                    'factor': factor['factor_name'],
                    'impact': factor['confidence_impact'],
                    'description': factor['description']
                })
        
        return {
            'contributors': confidence_contributors,
            'detractors': confidence_detractors,
            'overall_assessment': 'high' if decision.confidence_score > 0.7 else 
                                'medium' if decision.confidence_score > 0.5 else 'low'
        }
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about decisions made"""
        if not self.decision_history:
            return {'total_decisions': 0}
        
        decisions = [d['decision'] for d in self.decision_history]
        confidences = [d['confidence'] for d in self.decision_history]
        
        return {
            'total_decisions': len(self.decision_history),
            'decision_distribution': {
                'approved': decisions.count('approved'),
                'rejected': decisions.count('rejected'),
                'pending': decisions.count('pending'),
                'requires_review': decisions.count('requires_review')
            },
            'average_confidence': sum(confidences) / len(confidences),
            'high_confidence_decisions': len([c for c in confidences if c > 0.7])
        }

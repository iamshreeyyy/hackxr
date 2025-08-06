"""
Validation Agent
Dynamically applies policy rules and compliance checks
"""

import asyncio
import re
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.utils.logger import setup_logger
from src.models.schemas import ValidationRule, SourceClause

logger = setup_logger(__name__)

@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    violated_rules: List[str]
    satisfied_rules: List[str]
    warnings: List[str]
    validation_details: Dict[str, Any]

class PolicyRule:
    """Represents a policy rule with conditions and actions"""
    
    def __init__(self, rule_id: str, name: str, conditions: Dict[str, Any], action: str, priority: int = 1):
        self.rule_id = rule_id
        self.name = name
        self.conditions = conditions
        self.action = action
        self.priority = priority
    
    def evaluate(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate if rule conditions are met
        
        Args:
            context: Context containing entities and values to check
            
        Returns:
            Tuple of (condition_met, explanation)
        """
        try:
            for condition_type, condition_value in self.conditions.items():
                if not self._check_condition(condition_type, condition_value, context):
                    return False, f"Rule {self.name}: {condition_type} condition not met"
            
            return True, f"Rule {self.name}: all conditions satisfied"
            
        except Exception as e:
            logger.error(f"Error evaluating rule {self.rule_id}: {str(e)}")
            return False, f"Rule evaluation error: {str(e)}"
    
    def _check_condition(self, condition_type: str, condition_value: Any, context: Dict[str, Any]) -> bool:
        """Check individual condition"""
        if condition_type == "min_age":
            age = self._extract_numeric_value(context.get('age', '0'))
            return age >= condition_value
        
        elif condition_type == "max_age":
            age = self._extract_numeric_value(context.get('age', '0'))
            return age <= condition_value
        
        elif condition_type == "gender":
            gender = context.get('gender', '').lower()
            return gender in [g.lower() for g in condition_value] if isinstance(condition_value, list) else gender == condition_value.lower()
        
        elif condition_type == "waiting_period_days":
            policy_duration = self._extract_policy_duration(context.get('policy_duration', '0'))
            return policy_duration >= condition_value
        
        elif condition_type == "covered_procedures":
            procedure = context.get('procedure', '')
            if isinstance(procedure, list):
                procedure = ' '.join(procedure).lower()
            else:
                procedure = str(procedure).lower()
            return any(proc.lower() in procedure for proc in condition_value)
        
        elif condition_type == "excluded_procedures":
            procedure = context.get('procedure', '')
            if isinstance(procedure, list):
                procedure = ' '.join(procedure).lower()
            else:
                procedure = str(procedure).lower()
            return not any(proc.lower() in procedure for proc in condition_value)
        
        elif condition_type == "covered_locations":
            location = context.get('location', '')
            if isinstance(location, list):
                location = ' '.join(location).lower()
            else:
                location = str(location).lower()
            return any(loc.lower() in location for loc in condition_value)
        
        elif condition_type == "max_claim_amount":
            amount = self._extract_numeric_value(context.get('amount', '0'))
            return amount <= condition_value
        
        elif condition_type == "requires_pre_authorization":
            procedure = context.get('procedure', '')
            if isinstance(procedure, list):
                procedure = ' '.join(procedure).lower()
            else:
                procedure = str(procedure).lower()
            high_risk_procedures = ['surgery', 'operation', 'transplant', 'cardiac']
            return not any(proc in procedure for proc in high_risk_procedures)
        
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return True  # Default to True for unknown conditions
    
    def _extract_numeric_value(self, value_str: str) -> float:
        """Extract numeric value from string"""
        if isinstance(value_str, (int, float)):
            return float(value_str)
        
        # Remove non-numeric characters except decimal point
        numeric_str = re.sub(r'[^\d.]', '', str(value_str))
        try:
            return float(numeric_str) if numeric_str else 0.0
        except ValueError:
            return 0.0
    
    def _extract_policy_duration(self, duration_str: str) -> int:
        """Extract policy duration in days"""
        if isinstance(duration_str, (int, float)):
            return int(duration_str)
        
        duration_str = str(duration_str).lower()
        
        # Extract number
        numbers = re.findall(r'\d+', duration_str)
        if not numbers:
            return 0
        
        value = int(numbers[0])
        
        # Determine time unit
        if 'year' in duration_str or 'yr' in duration_str:
            return value * 365
        elif 'month' in duration_str:
            return value * 30
        elif 'week' in duration_str:
            return value * 7
        else:  # Assume days
            return value

class ValidationAgent:
    """
    Validation Agent
    Dynamically applies policy rules and compliance checks
    """
    
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self._initialize_default_rules()
        logger.info("Validation Agent initialized")
    
    def _initialize_default_rules(self):
        """Initialize default policy rules"""
        default_rules = [
            PolicyRule(
                rule_id="age_limit",
                name="Age Eligibility",
                conditions={"min_age": 18, "max_age": 80},
                action="check_age_eligibility",
                priority=1
            ),
            PolicyRule(
                rule_id="waiting_period",
                name="Waiting Period Check",
                conditions={"waiting_period_days": 90},  # 3 months
                action="check_waiting_period",
                priority=2
            ),
            PolicyRule(
                rule_id="covered_procedures",
                name="Procedure Coverage",
                conditions={"covered_procedures": [
                    "knee surgery", "hip surgery", "cardiac surgery", "dental", 
                    "eye surgery", "general surgery", "orthopedic", "treatment"
                ]},
                action="check_procedure_coverage",
                priority=3
            ),
            PolicyRule(
                rule_id="excluded_procedures",
                name="Excluded Procedures",
                conditions={"excluded_procedures": [
                    "cosmetic", "plastic surgery", "experimental", "elective"
                ]},
                action="reject_excluded_procedure",
                priority=1
            ),
            PolicyRule(
                rule_id="geographic_coverage",
                name="Geographic Coverage",
                conditions={"covered_locations": [
                    "pune", "mumbai", "delhi", "bangalore", "chennai", 
                    "hyderabad", "kolkata", "ahmedabad", "india"
                ]},
                action="check_geographic_coverage",
                priority=2
            ),
            PolicyRule(
                rule_id="claim_amount_limit",
                name="Maximum Claim Amount",
                conditions={"max_claim_amount": 500000},  # 5 lakhs
                action="check_claim_limit",
                priority=2
            ),
            PolicyRule(
                rule_id="pre_authorization",
                name="Pre-authorization Required",
                conditions={"requires_pre_authorization": True},
                action="require_pre_auth",
                priority=3
            )
        ]
        
        self.rules.extend(default_rules)
        logger.info(f"Initialized {len(default_rules)} default rules")
    
    async def validate_claim(self, entities: Dict[str, Any], source_clauses: List[SourceClause]) -> ValidationResult:
        """
        Validate a claim against policy rules
        
        Args:
            entities: Extracted entities from query
            source_clauses: Relevant policy clauses
            
        Returns:
            ValidationResult with detailed validation information
        """
        try:
            violated_rules = []
            satisfied_rules = []
            warnings = []
            validation_details = {}
            
            # Sort rules by priority
            sorted_rules = sorted(self.rules, key=lambda r: r.priority)
            
            # Validate against each rule
            for rule in sorted_rules:
                if not isinstance(rule, PolicyRule):
                    logger.error(f"Invalid rule type found: {type(rule)} - {rule}")
                    continue
                    
                is_satisfied, explanation = rule.evaluate(entities)
                
                if is_satisfied:
                    satisfied_rules.append(rule.name)
                    validation_details[rule.rule_id] = {
                        "status": "satisfied",
                        "explanation": explanation
                    }
                else:
                    violated_rules.append(rule.name)
                    validation_details[rule.rule_id] = {
                        "status": "violated",
                        "explanation": explanation
                    }
                    
                    # Add specific warnings based on rule type
                    if rule.rule_id == "waiting_period":
                        warnings.append("Policy may not have met minimum waiting period")
                    elif rule.rule_id == "excluded_procedures":
                        warnings.append("Procedure may be excluded from coverage")
            
            # Check source clauses for additional validation
            clause_validation = await self._validate_against_clauses(entities, source_clauses)
            validation_details.update(clause_validation)
            
            # Determine overall validity
            critical_violations = []
            for rule_name in violated_rules:
                # Find the actual rule object
                rule_obj = next((r for r in self.rules if r.name == rule_name), None)
                if rule_obj and rule_obj.rule_id in ['excluded_procedures', 'age_limit']:
                    critical_violations.append(rule_name)
            
            is_valid = len(critical_violations) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                violated_rules=violated_rules,
                satisfied_rules=satisfied_rules,
                warnings=warnings,
                validation_details=validation_details
            )
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return ValidationResult(
                is_valid=False,
                violated_rules=["validation_error"],
                satisfied_rules=[],
                warnings=[f"Validation error: {str(e)}"],
                validation_details={}
            )
    
    async def _validate_against_clauses(self, entities: Dict[str, Any], clauses: List[SourceClause]) -> Dict[str, Any]:
        """Validate entities against specific policy clauses"""
        clause_validation = {}
        
        for clause in clauses:
            clause_text = clause.clause_text.lower()
            clause_id = clause.clause_id
            
            # Check for coverage statements
            if self._contains_coverage_language(clause_text):
                if self._check_entity_in_clause(entities, clause_text):
                    clause_validation[f"clause_{clause_id}"] = {
                        "status": "supports_coverage",
                        "explanation": "Clause supports coverage for this case"
                    }
                else:
                    clause_validation[f"clause_{clause_id}"] = {
                        "status": "neutral",
                        "explanation": "Clause is relevant but not specifically supportive"
                    }
            
            # Check for exclusion statements
            elif self._contains_exclusion_language(clause_text):
                if self._check_entity_in_clause(entities, clause_text):
                    clause_validation[f"clause_{clause_id}"] = {
                        "status": "exclusion_risk",
                        "explanation": "Clause may exclude coverage for this case"
                    }
            
            # Check for waiting period mentions
            elif 'waiting' in clause_text or 'period' in clause_text:
                clause_validation[f"clause_{clause_id}"] = {
                    "status": "waiting_period_relevant",
                    "explanation": "Clause mentions waiting period requirements"
                }
        
        return clause_validation
    
    def _contains_coverage_language(self, text: str) -> bool:
        """Check if text contains coverage-positive language"""
        coverage_terms = [
            'covered', 'eligible', 'included', 'benefits', 'reimbursement',
            'payment', 'approved', 'qualified'
        ]
        return any(term in text for term in coverage_terms)
    
    def _contains_exclusion_language(self, text: str) -> bool:
        """Check if text contains exclusion language"""
        exclusion_terms = [
            'excluded', 'not covered', 'limitation', 'restriction', 
            'prohibited', 'denied', 'rejected'
        ]
        return any(term in text for term in exclusion_terms)
    
    def _check_entity_in_clause(self, entities: Dict[str, Any], clause_text: str) -> bool:
        """Check if any entities are mentioned in the clause"""
        for entity_type, entity_value in entities.items():
            if isinstance(entity_value, str) and entity_value.lower() in clause_text:
                return True
        return False
    
    async def add_custom_rule(self, rule: ValidationRule) -> bool:
        """Add a custom validation rule"""
        try:
            # Convert ValidationRule to PolicyRule
            policy_rule = PolicyRule(
                rule_id=rule.rule_id,
                name=rule.rule_name,
                conditions=json.loads(rule.condition),
                action=rule.action,
                priority=rule.priority
            )
            
            self.rules.append(policy_rule)
            logger.info(f"Added custom rule: {rule.rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding custom rule: {str(e)}")
            return False
    
    async def get_applicable_rules(self, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get rules that are applicable to the given entities"""
        applicable_rules = []
        
        for rule in self.rules:
            # Simple applicability check based on entity types
            rule_conditions = rule.conditions.keys()
            entity_types = set(entities.keys())
            
            # Check if rule conditions overlap with available entities
            if any(condition.replace('min_', '').replace('max_', '') in entity_types 
                  for condition in rule_conditions):
                applicable_rules.append({
                    'rule_id': rule.rule_id,
                    'name': rule.name,
                    'conditions': rule.conditions,
                    'priority': rule.priority
                })
        
        return applicable_rules
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        rule_types = {}
        for rule in self.rules:
            for condition_type in rule.conditions.keys():
                rule_types[condition_type] = rule_types.get(condition_type, 0) + 1
        
        return {
            'total_rules': len(self.rules),
            'rule_types': rule_types,
            'average_priority': sum(rule.priority for rule in self.rules) / len(self.rules) if self.rules else 0
        }

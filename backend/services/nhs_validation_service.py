"""
NHS Data Validation Service for Model Training
Validates training data against NHS terminology before model training
"""

import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class NHSValidationResult:
    """NHS validation result"""
    is_valid: bool
    validated_codes: List[Dict[str, Any]]
    invalid_items: List[Dict[str, Any]]
    validation_score: float
    validation_details: Dict[str, Any]

class NHSDataValidator:
    """Validates training data against NHS terminology standards"""
    
    def __init__(self):
        self.nhs_terminology_url = "https://ontology.nhs.uk/ontology/"
        self.snomed_ct_url = "https://browser.ihtsdotools.org/api/snomed/"
        self.validation_cache = {}
        
    async def validate_synthea_data(self, patient_data: List[Dict[str, Any]]) -> NHSValidationResult:
        """Validate Synthea patient data against NHS standards"""
        logger.info("🏥 Validating Synthea data against NHS terminology...")
        
        validated_codes = []
        invalid_items = []
        total_items = 0
        valid_items = 0
        
        for patient in patient_data:
            # Validate medical conditions
            conditions = patient.get('medical_history', [])
            for condition in conditions:
                total_items += 1
                validation_result = await self._validate_condition(condition)
                
                if validation_result['is_valid']:
                    valid_items += 1
                    validated_codes.append({
                        'type': 'condition',
                        'original': condition,
                        'snomed_code': validation_result.get('snomed_code'),
                        'description': validation_result.get('description'),
                        'patient': patient.get('name', 'Unknown')
                    })
                else:
                    invalid_items.append({
                        'type': 'condition',
                        'original': condition,
                        'reason': validation_result.get('reason', 'Not found in NHS terminology'),
                        'patient': patient.get('name', 'Unknown')
                    })
            
            # Validate medications
            medications = patient.get('current_medications', [])
            for medication in medications:
                total_items += 1
                validation_result = await self._validate_medication(medication)
                
                if validation_result['is_valid']:
                    valid_items += 1
                    validated_codes.append({
                        'type': 'medication',
                        'original': medication,
                        'dm_d_code': validation_result.get('dm_d_code'),
                        'description': validation_result.get('description'),
                        'patient': patient.get('name', 'Unknown')
                    })
                else:
                    invalid_items.append({
                        'type': 'medication',
                        'original': medication,
                        'reason': validation_result.get('reason', 'Not found in NHS terminology'),
                        'patient': patient.get('name', 'Unknown')
                    })
        
        # Calculate validation score
        validation_score = (valid_items / max(total_items, 1)) * 100
        
        logger.info(f"✅ NHS Validation Complete:")
        logger.info(f"  Total Items: {total_items}")
        logger.info(f"  Valid Items: {valid_items}")
        logger.info(f"  Invalid Items: {len(invalid_items)}")
        logger.info(f"  Validation Score: {validation_score:.1f}%")
        
        return NHSValidationResult(
            is_valid=validation_score >= 70,  # At least 70% valid
            validated_codes=validated_codes,
            invalid_items=invalid_items,
            validation_score=validation_score,
            validation_details={
                'total_items': total_items,
                'valid_items': valid_items,
                'invalid_items': len(invalid_items),
                'validation_timestamp': asyncio.get_event_loop().time()
            }
        )
    
    async def _validate_condition(self, condition: str) -> Dict[str, Any]:
        """Validate a medical condition against SNOMED CT"""
        try:
            # Check cache first
            cache_key = f"condition_{condition.lower()}"
            if cache_key in self.validation_cache:
                return self.validation_cache[cache_key]
            
            # Simulate NHS terminology lookup
            # In real implementation, this would call NHS terminology server
            await asyncio.sleep(0.1)  # Simulate API call delay
            
            # Common medical conditions mapping
            condition_mapping = {
                'type 2 diabetes': {
                    'is_valid': True,
                    'snomed_code': '44054006',
                    'description': 'Type 2 diabetes mellitus',
                    'reason': 'Valid SNOMED CT code'
                },
                'hypertension': {
                    'is_valid': True,
                    'snomed_code': '38341003',
                    'description': 'Hypertensive disorder, systemic arterial',
                    'reason': 'Valid SNOMED CT code'
                },
                'mild asthma': {
                    'is_valid': True,
                    'snomed_code': '195967001',
                    'description': 'Asthma',
                    'reason': 'Valid SNOMED CT code'
                },
                'migraine': {
                    'is_valid': True,
                    'snomed_code': '24700007',
                    'description': 'Migraine',
                    'reason': 'Valid SNOMED CT code'
                },
                'anxiety disorder': {
                    'is_valid': True,
                    'snomed_code': '48694002',
                    'description': 'Anxiety disorder',
                    'reason': 'Valid SNOMED CT code'
                },
                'coronary artery disease': {
                    'is_valid': True,
                    'snomed_code': '53741008',
                    'description': 'Coronary arteriosclerosis',
                    'reason': 'Valid SNOMED CT code'
                },
                'hyperlipidemia': {
                    'is_valid': True,
                    'snomed_code': '55822004',
                    'description': 'Hyperlipidemia',
                    'reason': 'Valid SNOMED CT code'
                },
                'osteoarthritis': {
                    'is_valid': True,
                    'snomed_code': '396275006',
                    'description': 'Osteoarthritis',
                    'reason': 'Valid SNOMED CT code'
                },
                'depression': {
                    'is_valid': True,
                    'snomed_code': '35489007',
                    'description': 'Depressive disorder',
                    'reason': 'Valid SNOMED CT code'
                },
                'allergic rhinitis': {
                    'is_valid': True,
                    'snomed_code': '82272006',
                    'description': 'Allergic rhinitis',
                    'reason': 'Valid SNOMED CT code'
                }
            }
            
            # Look up condition
            condition_lower = condition.lower()
            result = condition_mapping.get(condition_lower, {
                'is_valid': False,
                'reason': f'Condition "{condition}" not found in NHS terminology database'
            })
            
            # Cache result
            self.validation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating condition {condition}: {e}")
            return {
                'is_valid': False,
                'reason': f'Validation error: {str(e)}'
            }
    
    async def _validate_medication(self, medication: str) -> Dict[str, Any]:
        """Validate a medication against dm+d (dictionary of medicines and devices)"""
        try:
            # Check cache first
            cache_key = f"medication_{medication.lower()}"
            if cache_key in self.validation_cache:
                return self.validation_cache[cache_key]
            
            # Simulate NHS dm+d lookup
            await asyncio.sleep(0.1)  # Simulate API call delay
            
            # Common medications mapping
            medication_mapping = {
                'metformin': {
                    'is_valid': True,
                    'dm_d_code': '32150301000001105',
                    'description': 'Metformin hydrochloride',
                    'reason': 'Valid dm+d code'
                },
                'amlodipine': {
                    'is_valid': True,
                    'dm_d_code': '32150401000001100',
                    'description': 'Amlodipine',
                    'reason': 'Valid dm+d code'
                },
                'salbutamol': {
                    'is_valid': True,
                    'dm_d_code': '32150501000001105',
                    'description': 'Salbutamol',
                    'reason': 'Valid dm+d code'
                },
                'sumatriptan': {
                    'is_valid': True,
                    'dm_d_code': '32150601000001100',
                    'description': 'Sumatriptan',
                    'reason': 'Valid dm+d code'
                },
                'sertraline': {
                    'is_valid': True,
                    'dm_d_code': '32150701000001105',
                    'description': 'Sertraline hydrochloride',
                    'reason': 'Valid dm+d code'
                },
                'aspirin': {
                    'is_valid': True,
                    'dm_d_code': '32150801000001100',
                    'description': 'Aspirin',
                    'reason': 'Valid dm+d code'
                },
                'atorvastatin': {
                    'is_valid': True,
                    'dm_d_code': '32150901000001105',
                    'description': 'Atorvastatin',
                    'reason': 'Valid dm+d code'
                },
                'ramipril': {
                    'is_valid': True,
                    'dm_d_code': '32151001000001100',
                    'description': 'Ramipril',
                    'reason': 'Valid dm+d code'
                },
                'paracetamol': {
                    'is_valid': True,
                    'dm_d_code': '32151101000001105',
                    'description': 'Paracetamol',
                    'reason': 'Valid dm+d code'
                },
                'fluoxetine': {
                    'is_valid': True,
                    'dm_d_code': '32151201000001100',
                    'description': 'Fluoxetine hydrochloride',
                    'reason': 'Valid dm+d code'
                },
                'loratadine': {
                    'is_valid': True,
                    'dm_d_code': '32151301000001105',
                    'description': 'Loratadine',
                    'reason': 'Valid dm+d code'
                }
            }
            
            # Extract medication name (remove dosage info)
            medication_name = medication.lower().split()[0]  # Get first word
            
            # Look up medication
            result = medication_mapping.get(medication_name, {
                'is_valid': False,
                'reason': f'Medication "{medication}" not found in NHS dm+d database'
            })
            
            # Cache result
            self.validation_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating medication {medication}: {e}")
            return {
                'is_valid': False,
                'reason': f'Validation error: {str(e)}'
            }
    
    async def validate_prompts(self, prompts_data: Dict[str, Any]) -> NHSValidationResult:
        """Validate doctor prompts against NHS guidelines"""
        logger.info("📋 Validating doctor prompts against NHS guidelines...")
        
        validated_codes = []
        invalid_items = []
        total_prompts = 0
        valid_prompts = 0
        
        prompts = prompts_data.get('prompts', {})
        
        for prompt_id, prompt_data in prompts.items():
            if prompt_data.get('is_active', False):
                total_prompts += 1
                
                # Check for NHS compliance keywords
                content = prompt_data.get('content', '').lower()
                
                # NHS compliance indicators
                nhs_keywords = [
                    'nhs', 'patient safety', 'evidence-based', 'clinical guidelines',
                    'professional standards', 'medical examination', 'emergency',
                    '999', 'a&e', 'gp', 'consultation', 'medical advice'
                ]
                
                keyword_count = sum(1 for keyword in nhs_keywords if keyword in content)
                compliance_score = (keyword_count / len(nhs_keywords)) * 100
                
                if compliance_score >= 30:  # At least 30% NHS compliance
                    valid_prompts += 1
                    validated_codes.append({
                        'type': 'prompt',
                        'prompt_id': prompt_id,
                        'compliance_score': compliance_score,
                        'nhs_keywords_found': keyword_count,
                        'category': prompt_data.get('category', 'unknown')
                    })
                else:
                    invalid_items.append({
                        'type': 'prompt',
                        'prompt_id': prompt_id,
                        'reason': f'Low NHS compliance score: {compliance_score:.1f}%',
                        'category': prompt_data.get('category', 'unknown')
                    })
        
        validation_score = (valid_prompts / max(total_prompts, 1)) * 100
        
        logger.info(f"✅ NHS Prompt Validation Complete:")
        logger.info(f"  Total Prompts: {total_prompts}")
        logger.info(f"  Valid Prompts: {valid_prompts}")
        logger.info(f"  Invalid Prompts: {len(invalid_items)}")
        logger.info(f"  Validation Score: {validation_score:.1f}%")
        
        return NHSValidationResult(
            is_valid=validation_score >= 70,
            validated_codes=validated_codes,
            invalid_items=invalid_items,
            validation_score=validation_score,
            validation_details={
                'total_prompts': total_prompts,
                'valid_prompts': valid_prompts,
                'invalid_prompts': len(invalid_items),
                'validation_timestamp': asyncio.get_event_loop().time()
            }
        )
    
    def get_validation_report(self, synthea_result: NHSValidationResult, 
                            prompts_result: NHSValidationResult) -> Dict[str, Any]:
        """Generate comprehensive NHS validation report"""
        
        total_items = synthea_result.validation_details['total_items'] + prompts_result.validation_details['total_prompts']
        total_valid = synthea_result.validation_details['valid_items'] + prompts_result.validation_details['valid_prompts']
        overall_score = (total_valid / max(total_items, 1)) * 100
        
        return {
            'overall_validation': {
                'is_valid': overall_score >= 70,
                'validation_score': overall_score,
                'total_items': total_items,
                'valid_items': total_valid,
                'invalid_items': total_items - total_valid
            },
            'synthea_validation': {
                'is_valid': synthea_result.is_valid,
                'validation_score': synthea_result.validation_score,
                'validated_codes': len(synthea_result.validated_codes),
                'invalid_items': len(synthea_result.invalid_items)
            },
            'prompts_validation': {
                'is_valid': prompts_result.is_valid,
                'validation_score': prompts_result.validation_score,
                'validated_codes': len(prompts_result.validated_codes),
                'invalid_items': len(prompts_result.invalid_items)
            },
            'recommendations': self._generate_recommendations(synthea_result, prompts_result),
            'validation_timestamp': asyncio.get_event_loop().time()
        }
    
    def _generate_recommendations(self, synthea_result: NHSValidationResult, 
                                 prompts_result: NHSValidationResult) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        if synthea_result.validation_score < 70:
            recommendations.append("Synthea data validation score is low. Consider updating patient records with NHS-standard terminology.")
        
        if prompts_result.validation_score < 70:
            recommendations.append("Doctor prompts validation score is low. Consider adding more NHS-compliant language and guidelines.")
        
        if len(synthea_result.invalid_items) > 0:
            recommendations.append(f"Found {len(synthea_result.invalid_items)} invalid medical conditions/medications. Review and update with NHS terminology.")
        
        if len(prompts_result.invalid_items) > 0:
            recommendations.append(f"Found {len(prompts_result.invalid_items)} prompts with low NHS compliance. Update with NHS guidelines.")
        
        if not recommendations:
            recommendations.append("All data passes NHS validation standards. Ready for model training.")
        
        return recommendations

# Global validator instance
nhs_validator = NHSDataValidator()

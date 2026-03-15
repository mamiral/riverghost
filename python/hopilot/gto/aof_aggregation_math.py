from __future__ import annotations

import math
from typing import Any, Dict, List


def weighted_average(values: List[float], weights: List[int]) -> float:
    """Compute weighted average of values using sample counts as weights."""
    if not values or not weights or len(values) != len(weights):
        raise ValueError("Values and weights must be non-empty and same length")
    
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("Total weight cannot be zero")
    
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def calculate_confidence_score(total_samples: int) -> float:
    """Calculate confidence score from total sample count.
    
    Returns a value between 0 and 1, where higher is more confident.
    Uses sqrt(total_samples) normalized to reach ~1.0 at 1000 samples.
    """
    if total_samples <= 0:
        return 0.0
    
    # Normalize so that 1000 samples gives ~1.0 confidence
    normalized = min(1.0, math.sqrt(total_samples) / math.sqrt(1000))
    return normalized


def aggregate_run_data(run_payloads: List[Dict[str, Any]], run_weights: List[int] | None = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Aggregate multiple run payloads into statistics.
    
    Args:
        run_payloads: List of run data dicts, each containing hand -> metric -> value
        run_weights: Optional list of weights for each run (defaults to equal weighting)
        
    Returns:
        Dict[hand, Dict[metric, Dict with aggregated_value, total_samples, confidence]]
    """
    if run_weights is None:
        run_weights = [1] * len(run_payloads)
    
    if len(run_payloads) != len(run_weights):
        raise ValueError("run_payloads and run_weights must have same length")
    
    # Collect all data points per hand/metric with proper weighting
    data_points: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    
    for payload, weight in zip(run_payloads, run_weights):
        for hand, metrics in payload.items():
            if hand not in data_points:
                data_points[hand] = {}
            
            for metric, value in metrics.items():
                if metric not in data_points[hand]:
                    data_points[hand][metric] = []
                
                data_points[hand][metric].append({
                    'value': value,
                    'weight': weight
                })
    
    # Compute aggregates efficiently
    result = {}
    for hand, metrics in data_points.items():
        result[hand] = {}
        for metric, points in metrics.items():
            if not points:
                continue
                
            values = [p['value'] for p in points]
            weights = [p['weight'] for p in points]
            
            aggregated_value = weighted_average(values, weights)
            total_samples = sum(weights)
            confidence = calculate_confidence_score(total_samples)
            
            result[hand][metric] = {
                'aggregated_value': aggregated_value,
                'total_samples': total_samples,
                'confidence_score': confidence
            }
    
    return result


def merge_degraded_statuses(statuses: List[str]) -> str:
    """Merge multiple degraded statuses into a single status.
    
    Prioritizes available data over degraded.
    """
    if not statuses:
        return "no_contest"
    
    # Priority order: available > timeout > error > missing > no_contest
    priority = {
        "available": 5,
        "timeout": 4,
        "error": 3,
        "missing": 2,
        "no_contest": 1
    }
    
    best_status = max(statuses, key=lambda s: priority.get(s, 0))
    return best_status
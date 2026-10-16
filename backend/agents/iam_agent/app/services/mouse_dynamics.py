"""
Mouse Dynamics Service
Implements behavioral biometric authentication using mouse movement patterns
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import statistics
import math

logger = logging.getLogger(__name__)


class MouseDynamicsService:
    """Service for mouse dynamics authentication."""
    
    def __init__(self):
        self.enrollment_samples_required = 15  # More samples needed for mouse dynamics
        self.threshold_factor = 2.0
    
    def enroll_user(
        self,
        user_id: str,
        mouse_data: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enroll a user for mouse dynamics authentication.
        
        Args:
            user_id: User ID
            mouse_data: List of mouse movement data samples
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Enrollment result with profile
        """
        if len(mouse_data) < self.enrollment_samples_required:
            return {
                "user_id": user_id,
                "status": "insufficient_samples",
                "message": f"Need at least {self.enrollment_samples_required} samples, got {len(mouse_data)}",
                "samples_provided": len(mouse_data),
                "samples_required": self.enrollment_samples_required
            }
        
        # Extract features from mouse data
        features = self._extract_features(mouse_data)
        
        # Calculate user profile
        profile = self._calculate_profile(features)
        
        enrollment = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "profile": profile,
            "samples_used": len(mouse_data),
            "enrolled_at": datetime.utcnow().isoformat(),
            "status": "enrolled"
        }
        
        # TODO: Store in database
        
        return enrollment
    
    def verify_mouse_pattern(
        self,
        user_id: str,
        mouse_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify mouse movement pattern against enrolled profile."""
        enrollment = self._get_enrollment(user_id, tenant_id)
        if not enrollment:
            return {
                "user_id": user_id,
                "verified": False,
                "score": 0.0,
                "reason": "user_not_enrolled"
            }
        
        profile = enrollment["profile"]
        
        # Extract features from verification sample
        verification_features = self._extract_single_sample_features(mouse_data)
        
        # Calculate similarity score
        score = self._calculate_similarity_score(verification_features, profile)
        
        # Make decision
        threshold = self._calculate_threshold(profile)
        verified = score >= threshold
        
        return {
            "user_id": user_id,
            "verified": verified,
            "score": round(score, 4),
            "threshold": round(threshold, 4),
            "confidence": self._calculate_confidence(score, threshold),
            "verified_at": datetime.utcnow().isoformat()
        }
    
    def _extract_features(
        self,
        mouse_data: List[Dict[str, Any]]
    ) -> Dict[str, List[float]]:
        """
        Extract features from mouse movement data.
        
        Features:
        - Movement speed (velocity)
        - Acceleration
        - Jerk (rate of change of acceleration)
        - Curvature (path curvature)
        - Direction changes
        - Click patterns (time between clicks)
        - Movement angles
        """
        features = {
            "velocities": [],
            "accelerations": [],
            "jerks": [],
            "curvatures": [],
            "direction_changes": [],
            "click_intervals": [],
            "angles": []
        }
        
        for sample in mouse_data:
            movements = sample.get("movements", [])
            clicks = sample.get("clicks", [])
            
            # Process movements
            prev_x, prev_y, prev_time = None, None, None
            prev_velocity = None
            
            for i, movement in enumerate(movements):
                x = movement.get("x")
                y = movement.get("y")
                timestamp = movement.get("timestamp")
                
                if prev_x is not None and prev_y is not None and prev_time is not None:
                    # Calculate distance
                    dx = x - prev_x
                    dy = y - prev_y
                    distance = math.sqrt(dx * dx + dy * dy)
                    dt = (timestamp - prev_time) / 1000.0  # Convert to seconds
                    
                    if dt > 0:
                        # Velocity
                        velocity = distance / dt
                        features["velocities"].append(velocity)
                        
                        # Acceleration
                        if prev_velocity is not None:
                            acceleration = (velocity - prev_velocity) / dt
                            features["accelerations"].append(acceleration)
                        
                        prev_velocity = velocity
                        
                        # Angle
                        angle = math.atan2(dy, dx)
                        features["angles"].append(angle)
                        
                        # Direction change
                        if i > 1:
                            prev_angle = features["angles"][-2] if len(features["angles"]) >= 2 else angle
                            angle_diff = abs(angle - prev_angle)
                            # Normalize to 0-π range
                            if angle_diff > math.pi:
                                angle_diff = 2 * math.pi - angle_diff
                            features["direction_changes"].append(angle_diff)
                        
                        # Curvature (simplified - rate of angle change)
                        if i > 1 and dt > 0:
                            curvature = abs(features["direction_changes"][-1] if features["direction_changes"] else 0) / dt
                            features["curvatures"].append(curvature)
                
                prev_x, prev_y, prev_time = x, y, timestamp
            
            # Process clicks
            for i in range(1, len(clicks)):
                prev_click = clicks[i - 1]
                curr_click = clicks[i]
                interval = curr_click.get("timestamp") - prev_click.get("timestamp")
                features["click_intervals"].append(interval)
        
        return features
    
    def _extract_single_sample_features(
        self,
        mouse_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract features from a single mouse movement sample."""
        samples = [mouse_data]
        features = self._extract_features(samples)
        
        # Calculate mean values
        return {
            "mean_velocity": statistics.mean(features["velocities"]) if features["velocities"] else 0.0,
            "mean_acceleration": statistics.mean(features["accelerations"]) if features["accelerations"] else 0.0,
            "mean_curvature": statistics.mean(features["curvatures"]) if features["curvatures"] else 0.0,
            "mean_direction_change": statistics.mean(features["direction_changes"]) if features["direction_changes"] else 0.0,
            "mean_click_interval": statistics.mean(features["click_intervals"]) if features["click_intervals"] else 0.0
        }
    
    def _calculate_profile(
        self,
        features: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Calculate user profile from features."""
        profile = {
            "velocity": {
                "mean": statistics.mean(features["velocities"]) if features["velocities"] else 0.0,
                "std": statistics.stdev(features["velocities"]) if len(features["velocities"]) > 1 else 0.0
            },
            "acceleration": {
                "mean": statistics.mean(features["accelerations"]) if features["accelerations"] else 0.0,
                "std": statistics.stdev(features["accelerations"]) if len(features["accelerations"]) > 1 else 0.0
            },
            "curvature": {
                "mean": statistics.mean(features["curvatures"]) if features["curvatures"] else 0.0,
                "std": statistics.stdev(features["curvatures"]) if len(features["curvatures"]) > 1 else 0.0
            },
            "direction_change": {
                "mean": statistics.mean(features["direction_changes"]) if features["direction_changes"] else 0.0,
                "std": statistics.stdev(features["direction_changes"]) if len(features["direction_changes"]) > 1 else 0.0
            },
            "click_interval": {
                "mean": statistics.mean(features["click_intervals"]) if features["click_intervals"] else 0.0,
                "std": statistics.stdev(features["click_intervals"]) if len(features["click_intervals"]) > 1 else 0.0
            }
        }
        
        return profile
    
    def _calculate_similarity_score(
        self,
        verification_features: Dict[str, float],
        profile: Dict[str, Any]
    ) -> float:
        """Calculate similarity score."""
        scores = []
        
        # Compare each feature
        for feature_name in ["velocity", "acceleration", "curvature", "direction_change", "click_interval"]:
            if f"mean_{feature_name}" in verification_features:
                feature_mean = verification_features[f"mean_{feature_name}"]
                profile_feature = profile[feature_name]
                
                diff = abs(feature_mean - profile_feature["mean"])
                std = profile_feature["std"] or 1.0
                feature_score = max(0, 1 - (diff / (self.threshold_factor * std)))
                scores.append(feature_score)
        
        return statistics.mean(scores) if scores else 0.0
    
    def _calculate_threshold(self, profile: Dict[str, Any]) -> float:
        """Calculate acceptance threshold."""
        base_threshold = 0.65
        
        # Adjust based on consistency
        avg_std = (
            (profile["velocity"]["std"] or 0) +
            (profile["acceleration"]["std"] or 0) +
            (profile["curvature"]["std"] or 0)
        ) / 3
        
        if avg_std < 100:
            threshold_adjustment = 0.1
        elif avg_std < 200:
            threshold_adjustment = 0.0
        else:
            threshold_adjustment = -0.1
        
        return max(0.5, min(0.85, base_threshold + threshold_adjustment))
    
    def _calculate_confidence(
        self,
        score: float,
        threshold: float
    ) -> str:
        """Calculate confidence level."""
        margin = score - threshold
        
        if margin > 0.2:
            return "high"
        elif margin > 0.1:
            return "medium"
        elif margin > 0:
            return "low"
        else:
            return "rejected"
    
    def _get_enrollment(
        self,
        user_id: str,
        tenant_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get user enrollment (would fetch from database)."""
        # TODO: Fetch from database
        return None


"""
Keystroke Dynamics Service
Implements behavioral biometric authentication using keystroke patterns
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import statistics
import json

logger = logging.getLogger(__name__)


class KeystrokeDynamicsService:
    """Service for keystroke dynamics authentication."""
    
    def __init__(self):
        self.enrollment_samples_required = 10  # Number of samples needed for enrollment
        self.threshold_factor = 2.0  # Standard deviations for acceptance threshold
    
    def enroll_user(
        self,
        user_id: str,
        keystroke_data: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enroll a user for keystroke dynamics authentication.
        
        Args:
            user_id: User ID
            keystroke_data: List of keystroke timing data samples
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Enrollment result with profile statistics
        """
        if len(keystroke_data) < self.enrollment_samples_required:
            return {
                "user_id": user_id,
                "status": "insufficient_samples",
                "message": f"Need at least {self.enrollment_samples_required} samples, got {len(keystroke_data)}",
                "samples_provided": len(keystroke_data),
                "samples_required": self.enrollment_samples_required
            }
        
        # Extract features from keystroke data
        features = self._extract_features(keystroke_data)
        
        # Calculate user profile (mean and standard deviation for each feature)
        profile = self._calculate_profile(features)
        
        # Store enrollment (would persist to database)
        enrollment = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "profile": profile,
            "samples_used": len(keystroke_data),
            "enrolled_at": datetime.utcnow().isoformat(),
            "status": "enrolled"
        }
        
        # TODO: Store in database
        # self._save_enrollment(enrollment)
        
        return enrollment
    
    def verify_keystroke_pattern(
        self,
        user_id: str,
        keystroke_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify keystroke pattern against enrolled profile.
        
        Args:
            user_id: User ID
            keystroke_data: Single keystroke timing data sample
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Verification result with score and decision
        """
        # Get user profile (would fetch from database)
        enrollment = self._get_enrollment(user_id, tenant_id)
        if not enrollment:
            return {
                "user_id": user_id,
                "verified": False,
                "score": 0.0,
                "reason": "user_not_enrolled",
                "threshold": None
            }
        
        profile = enrollment["profile"]
        
        # Extract features from verification sample
        verification_features = self._extract_single_sample_features(keystroke_data)
        
        # Calculate distance/similarity score
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
    
    def update_enrollment(
        self,
        user_id: str,
        additional_samples: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user enrollment with additional samples (adaptive learning).
        """
        enrollment = self._get_enrollment(user_id, tenant_id)
        if not enrollment:
            return {
                "user_id": user_id,
                "status": "error",
                "message": "User not enrolled"
            }
        
        # Combine old and new samples (would fetch old samples from DB)
        # For now, calculate new profile from additional samples
        new_features = self._extract_features(additional_samples)
        new_profile = self._calculate_profile(new_features)
        
        # Update profile (adaptive update - weighted average)
        updated_profile = self._adaptive_update(enrollment["profile"], new_profile)
        
        enrollment["profile"] = updated_profile
        enrollment["samples_used"] += len(additional_samples)
        enrollment["updated_at"] = datetime.utcnow().isoformat()
        
        # TODO: Update in database
        
        return enrollment
    
    def _extract_features(
        self,
        keystroke_data: List[Dict[str, Any]]
    ) -> Dict[str, List[float]]:
        """
        Extract features from keystroke data samples.
        
        Features extracted:
        - Dwell time (time key is held down)
        - Flight time (time between key presses)
        - Key-pair digraphs (timing for specific key pairs)
        - Typing rhythm (overall timing pattern)
        """
        features = {
            "dwell_times": [],
            "flight_times": [],
            "digraphs": {}
        }
        
        for sample in keystroke_data:
            events = sample.get("events", [])
            
            for i, event in enumerate(events):
                event_type = event.get("type")
                timestamp = event.get("timestamp")
                key = event.get("key")
                
                if event_type == "keydown":
                    # Find corresponding keyup
                    for j in range(i + 1, len(events)):
                        next_event = events[j]
                        if next_event.get("type") == "keyup" and next_event.get("key") == key:
                            keyup_time = next_event.get("timestamp")
                            dwell_time = keyup_time - timestamp
                            features["dwell_times"].append(dwell_time)
                            break
                    
                    # Calculate flight time to next keydown
                    if i < len(events) - 1:
                        next_keydown = events[i + 1]
                        if next_keydown.get("type") == "keydown":
                            flight_time = next_keydown.get("timestamp") - timestamp
                            features["flight_times"].append(flight_time)
                            
                            # Store digraph (key pair timing)
                            digraph = f"{key}-{next_keydown.get('key')}"
                            if digraph not in features["digraphs"]:
                                features["digraphs"][digraph] = []
                            features["digraphs"][digraph].append(flight_time)
        
        return features
    
    def _extract_single_sample_features(
        self,
        keystroke_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract features from a single keystroke sample."""
        samples = [keystroke_data]  # Convert to list format
        features = self._extract_features(samples)
        
        # Calculate mean values for comparison
        return {
            "mean_dwell_time": statistics.mean(features["dwell_times"]) if features["dwell_times"] else 0.0,
            "mean_flight_time": statistics.mean(features["flight_times"]) if features["flight_times"] else 0.0,
            "digraph_means": {
                k: statistics.mean(v) if v else 0.0
                for k, v in features["digraphs"].items()
            }
        }
    
    def _calculate_profile(
        self,
        features: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Calculate user profile (statistics) from features."""
        profile = {
            "dwell_time": {
                "mean": statistics.mean(features["dwell_times"]) if features["dwell_times"] else 0.0,
                "std": statistics.stdev(features["dwell_times"]) if len(features["dwell_times"]) > 1 else 0.0
            },
            "flight_time": {
                "mean": statistics.mean(features["flight_times"]) if features["flight_times"] else 0.0,
                "std": statistics.stdev(features["flight_times"]) if len(features["flight_times"]) > 1 else 0.0
            },
            "digraphs": {}
        }
        
        # Calculate statistics for each digraph
        for digraph, times in features["digraphs"].items():
            if len(times) > 0:
                profile["digraphs"][digraph] = {
                    "mean": statistics.mean(times),
                    "std": statistics.stdev(times) if len(times) > 1 else 0.0,
                    "count": len(times)
                }
        
        return profile
    
    def _calculate_similarity_score(
        self,
        verification_features: Dict[str, float],
        profile: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity score between verification sample and profile.
        
        Higher score = more similar (closer match)
        Score is normalized to 0-1 range
        """
        scores = []
        
        # Compare dwell time
        if "mean_dwell_time" in verification_features:
            dwell_diff = abs(
                verification_features["mean_dwell_time"] - profile["dwell_time"]["mean"]
            )
            dwell_std = profile["dwell_time"]["std"] or 1.0
            dwell_score = max(0, 1 - (dwell_diff / (self.threshold_factor * dwell_std)))
            scores.append(dwell_score)
        
        # Compare flight time
        if "mean_flight_time" in verification_features:
            flight_diff = abs(
                verification_features["mean_flight_time"] - profile["flight_time"]["mean"]
            )
            flight_std = profile["flight_time"]["std"] or 1.0
            flight_score = max(0, 1 - (flight_diff / (self.threshold_factor * flight_std)))
            scores.append(flight_score)
        
        # Compare digraphs
        digraph_scores = []
        for digraph, mean_time in verification_features.get("digraph_means", {}).items():
            if digraph in profile["digraphs"]:
                digraph_profile = profile["digraphs"][digraph]
                digraph_diff = abs(mean_time - digraph_profile["mean"])
                digraph_std = digraph_profile["std"] or 1.0
                digraph_score = max(0, 1 - (digraph_diff / (self.threshold_factor * digraph_std)))
                digraph_scores.append(digraph_score)
        
        if digraph_scores:
            scores.extend(digraph_scores)
        
        # Average all scores
        overall_score = statistics.mean(scores) if scores else 0.0
        
        return overall_score
    
    def _calculate_threshold(self, profile: Dict[str, Any]) -> float:
        """
        Calculate acceptance threshold based on profile statistics.
        
        Threshold is typically set to allow for natural variation.
        """
        # Use a base threshold and adjust based on profile consistency
        base_threshold = 0.6
        
        # Adjust based on standard deviation (more consistent = higher threshold)
        avg_std = (
            (profile["dwell_time"]["std"] or 0) +
            (profile["flight_time"]["std"] or 0)
        ) / 2
        
        # Lower variation allows higher threshold
        if avg_std < 20:
            threshold_adjustment = 0.1
        elif avg_std < 50:
            threshold_adjustment = 0.0
        else:
            threshold_adjustment = -0.1
        
        return max(0.4, min(0.9, base_threshold + threshold_adjustment))
    
    def _calculate_confidence(
        self,
        score: float,
        threshold: float
    ) -> str:
        """Calculate confidence level."""
        margin = score - threshold
        
        if margin > 0.3:
            return "high"
        elif margin > 0.1:
            return "medium"
        elif margin > 0:
            return "low"
        else:
            return "rejected"
    
    def _adaptive_update(
        self,
        old_profile: Dict[str, Any],
        new_profile: Dict[str, Any],
        learning_rate: float = 0.1
    ) -> Dict[str, Any]:
        """
        Adaptively update profile with new samples.
        
        Uses weighted average to gradually adapt to user's changing patterns.
        """
        updated_profile = {
            "dwell_time": {
                "mean": (1 - learning_rate) * old_profile["dwell_time"]["mean"] +
                        learning_rate * new_profile["dwell_time"]["mean"],
                "std": (1 - learning_rate) * old_profile["dwell_time"]["std"] +
                       learning_rate * new_profile["dwell_time"]["std"]
            },
            "flight_time": {
                "mean": (1 - learning_rate) * old_profile["flight_time"]["mean"] +
                        learning_rate * new_profile["flight_time"]["mean"],
                "std": (1 - learning_rate) * old_profile["flight_time"]["std"] +
                       learning_rate * new_profile["flight_time"]["std"]
            },
            "digraphs": {}
        }
        
        # Update digraphs
        all_digraphs = set(old_profile["digraphs"].keys()) | set(new_profile["digraphs"].keys())
        for digraph in all_digraphs:
            if digraph in old_profile["digraphs"] and digraph in new_profile["digraphs"]:
                old_digraph = old_profile["digraphs"][digraph]
                new_digraph = new_profile["digraphs"][digraph]
                updated_profile["digraphs"][digraph] = {
                    "mean": (1 - learning_rate) * old_digraph["mean"] +
                            learning_rate * new_digraph["mean"],
                    "std": (1 - learning_rate) * old_digraph["std"] +
                           learning_rate * new_digraph["std"],
                    "count": old_digraph.get("count", 0) + new_digraph.get("count", 0)
                }
            elif digraph in old_profile["digraphs"]:
                updated_profile["digraphs"][digraph] = old_profile["digraphs"][digraph]
            else:
                updated_profile["digraphs"][digraph] = new_profile["digraphs"][digraph]
        
        return updated_profile
    
    def _get_enrollment(
        self,
        user_id: str,
        tenant_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get user enrollment (would fetch from database)."""
        # TODO: Fetch from database
        return None


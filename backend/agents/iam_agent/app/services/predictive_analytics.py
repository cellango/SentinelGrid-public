"""
Predictive Analytics Service
Provides forecasting and prediction capabilities for IAM
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from app.services.model_provider import get_model_provider

logger = logging.getLogger(__name__)


class PredictiveAnalyticsService:
    """Service for predictive analytics and forecasting."""
    
    def __init__(self):
        self.model_provider = get_model_provider()
    
    def predict_access_patterns(
        self,
        user_id: str,
        access_history: List[Dict[str, Any]],
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """
        Predict future access patterns for a user.
        
        Predictions:
        - Expected access frequency
        - Likely resources to be accessed
        - Typical access times
        - Access volume trends
        """
        if not access_history or len(access_history) < 10:
            return {
                "user_id": user_id,
                "prediction": "insufficient_data",
                "message": "Need at least 10 historical access records for prediction"
            }
        
        # Extract time series data
        daily_counts = self._extract_daily_counts(access_history)
        hourly_distribution = self._extract_hourly_distribution(access_history)
        resource_frequency = self._extract_resource_frequency(access_history)
        
        # Predict future daily access
        predicted_daily = self._predict_time_series(
            list(daily_counts.values()),
            forecast_days
        )
        
        # Predict likely resources
        top_resources = sorted(
            resource_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Calculate trends
        recent_avg = statistics.mean(list(daily_counts.values())[-7:])
        historical_avg = statistics.mean(list(daily_counts.values())[:-7]) if len(daily_counts) > 7 else recent_avg
        trend = "increasing" if recent_avg > historical_avg else "decreasing" if recent_avg < historical_avg else "stable"
        
        return {
            "user_id": user_id,
            "forecast_days": forecast_days,
            "predictions": {
                "daily_access_forecast": predicted_daily,
                "expected_daily_avg": round(recent_avg, 2),
                "trend": trend,
                "trend_percentage": round(((recent_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0, 2),
                "likely_resources": [r[0] for r in top_resources],
                "typical_hours": self._get_typical_hours(hourly_distribution)
            },
            "confidence": self._calculate_confidence(access_history),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def forecast_risk_trends(
        self,
        risk_history: List[Dict[str, Any]],
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """
        Forecast risk trends over time.
        
        Args:
            risk_history: List of historical risk scores with timestamps
            forecast_days: Number of days to forecast
            
        Returns:
            Forecast with trend analysis
        """
        if not risk_history or len(risk_history) < 7:
            return {
                "prediction": "insufficient_data",
                "message": "Need at least 7 days of risk history"
            }
        
        # Extract risk scores over time
        risk_scores = [r.get("risk_score", 0) for r in risk_history]
        dates = [r.get("date") or r.get("timestamp") for r in risk_history]
        
        # Calculate trend
        recent_avg = statistics.mean(risk_scores[-7:])
        historical_avg = statistics.mean(risk_scores[:-7]) if len(risk_scores) > 7 else recent_avg
        
        trend_direction = "increasing" if recent_avg > historical_avg else "decreasing" if recent_avg < historical_avg else "stable"
        
        # Simple linear forecast (can be enhanced with ML models)
        forecast_scores = self._predict_time_series(risk_scores, forecast_days)
        
        # Identify risk thresholds
        high_risk_threshold = 70
        medium_risk_threshold = 50
        
        forecast_high_risk_days = sum(1 for score in forecast_scores if score >= high_risk_threshold)
        forecast_medium_risk_days = sum(1 for score in forecast_scores if high_risk_threshold > score >= medium_risk_threshold)
        
        return {
            "current_risk": risk_scores[-1] if risk_scores else 0,
            "average_risk": round(recent_avg, 2),
            "trend": trend_direction,
            "trend_percentage": round(((recent_avg - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0, 2),
            "forecast": {
                "forecast_days": forecast_days,
                "predicted_scores": forecast_scores,
                "expected_avg": round(statistics.mean(forecast_scores), 2),
                "high_risk_days": forecast_high_risk_days,
                "medium_risk_days": forecast_medium_risk_days
            },
            "recommendations": self._generate_risk_forecast_recommendations(
                trend_direction,
                recent_avg,
                forecast_scores
            ),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def predict_access_requests(
        self,
        request_history: List[Dict[str, Any]],
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """
        Predict future access request patterns.
        """
        if not request_history:
            return {
                "prediction": "no_data",
                "message": "No historical request data available"
            }
        
        # Extract daily request counts
        daily_counts = defaultdict(int)
        for request in request_history:
            timestamp = request.get("created_at") or request.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    day_key = dt.date().isoformat()
                    daily_counts[day_key] += 1
                except:
                    continue
        
        counts = list(daily_counts.values())
        
        if not counts:
            return {"prediction": "insufficient_data"}
        
        # Predict future requests
        predicted_counts = self._predict_time_series(counts, forecast_days)
        
        # Analyze patterns
        recent_avg = statistics.mean(counts[-7:]) if len(counts) >= 7 else statistics.mean(counts)
        forecast_avg = statistics.mean(predicted_counts)
        
        return {
            "forecast_days": forecast_days,
            "current_daily_avg": round(recent_avg, 2),
            "predicted_daily_avg": round(forecast_avg, 2),
            "predicted_total": round(sum(predicted_counts)),
            "predicted_daily_counts": predicted_counts,
            "trend": "increasing" if forecast_avg > recent_avg else "decreasing" if forecast_avg < recent_avg else "stable",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def predict_user_churn_risk(
        self,
        user_id: str,
        user_data: Dict[str, Any],
        access_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Predict if a user is at risk of churn (inactivity leading to account closure).
        """
        if not access_history:
            return {
                "user_id": user_id,
                "churn_risk": "high",
                "reason": "No access history"
            }
        
        # Get last access
        latest_access = max(
            (a.get("timestamp") for a in access_history if a.get("timestamp")),
            default=None
        )
        
        if not latest_access:
            return {
                "user_id": user_id,
                "churn_risk": "high",
                "reason": "No recent access"
            }
        
        try:
            if isinstance(latest_access, str):
                latest_dt = datetime.fromisoformat(latest_access.replace('Z', '+00:00'))
            else:
                latest_dt = latest_access
            
            days_since = (datetime.utcnow() - latest_dt.replace(tzinfo=None)).days
            
            # Calculate access frequency trend
            recent_count = sum(1 for a in access_history if self._is_recent(a, days=30))
            historical_count = sum(1 for a in access_history if not self._is_recent(a, days=30))
            
            frequency_trend = "decreasing" if recent_count < (historical_count / 2) else "stable"
            
            # Determine churn risk
            if days_since > 90:
                churn_risk = "critical"
            elif days_since > 60:
                churn_risk = "high"
            elif days_since > 30 and frequency_trend == "decreasing":
                churn_risk = "medium"
            else:
                churn_risk = "low"
            
            return {
                "user_id": user_id,
                "churn_risk": churn_risk,
                "days_since_last_access": days_since,
                "access_frequency_trend": frequency_trend,
                "recommendations": self._generate_churn_prevention_recommendations(churn_risk, days_since),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error predicting churn risk: {e}")
            return {
                "user_id": user_id,
                "churn_risk": "unknown",
                "error": str(e)
            }
    
    def _extract_daily_counts(self, access_history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract daily access counts from history."""
        daily_counts = defaultdict(int)
        
        for access in access_history:
            timestamp = access.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    day_key = dt.date().isoformat()
                    daily_counts[day_key] += 1
                except:
                    continue
        
        return dict(sorted(daily_counts.items()))
    
    def _extract_hourly_distribution(self, access_history: List[Dict[str, Any]]) -> Dict[int, int]:
        """Extract hourly access distribution."""
        hourly = defaultdict(int)
        
        for access in access_history:
            timestamp = access.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    hour = dt.hour
                    hourly[hour] += 1
                except:
                    continue
        
        return dict(hourly)
    
    def _extract_resource_frequency(self, access_history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Extract resource access frequency."""
        resources = defaultdict(int)
        
        for access in access_history:
            resource = access.get("resource") or access.get("resource_id") or access.get("resource_type")
            if resource:
                resources[resource] += 1
        
        return dict(resources)
    
    def _predict_time_series(self, values: List[float], forecast_periods: int) -> List[float]:
        """Simple time series prediction using moving average with trend."""
        if not values:
            return [0.0] * forecast_periods
        
        if len(values) < 3:
            # Just repeat last value
            return [values[-1]] * forecast_periods
        
        # Calculate trend
        recent_avg = statistics.mean(values[-7:]) if len(values) >= 7 else statistics.mean(values)
        historical_avg = statistics.mean(values[:-7]) if len(values) > 7 else recent_avg
        
        trend = (recent_avg - historical_avg) / max(len(values) - 7, 1)
        
        # Forecast
        forecast = []
        last_value = values[-1]
        
        for i in range(forecast_periods):
            predicted = last_value + (trend * (i + 1))
            forecast.append(max(0, predicted))  # Ensure non-negative
        
        return forecast
    
    def _get_typical_hours(self, hourly_dist: Dict[int, int]) -> List[int]:
        """Get typical access hours (top 3 hours)."""
        if not hourly_dist:
            return []
        
        sorted_hours = sorted(hourly_dist.items(), key=lambda x: x[1], reverse=True)
        return [h[0] for h in sorted_hours[:3]]
    
    def _calculate_confidence(self, access_history: List[Dict[str, Any]]) -> float:
        """Calculate prediction confidence based on data quality."""
        if len(access_history) < 10:
            return 0.3
        elif len(access_history) < 30:
            return 0.6
        elif len(access_history) < 90:
            return 0.8
        else:
            return 0.95
    
    def _generate_risk_forecast_recommendations(
        self,
        trend: str,
        current_avg: float,
        forecast_scores: List[float]
    ) -> List[str]:
        """Generate recommendations based on risk forecast."""
        recommendations = []
        
        if trend == "increasing":
            recommendations.append("Risk trend is increasing - review access policies and user privileges")
        
        if statistics.mean(forecast_scores) > 70:
            recommendations.append("High risk forecast - implement proactive security measures")
        
        if any(score > 80 for score in forecast_scores):
            recommendations.append("Critical risk predicted - prepare incident response procedures")
        
        if not recommendations:
            recommendations.append("Risk levels are within acceptable range - continue monitoring")
        
        return recommendations
    
    def _generate_churn_prevention_recommendations(
        self,
        churn_risk: str,
        days_since: int
    ) -> List[str]:
        """Generate recommendations to prevent user churn."""
        recommendations = []
        
        if churn_risk in ["critical", "high"]:
            recommendations.append(f"User inactive for {days_since} days - consider outreach or account review")
        
        if churn_risk == "critical":
            recommendations.append("Consider disabling or archiving account if inactive")
        
        return recommendations
    
    def _is_recent(self, item: Dict[str, Any], days: int = 30) -> bool:
        """Check if item is recent."""
        timestamp = item.get("timestamp") or item.get("created_at")
        if not timestamp:
            return False
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            return dt.replace(tzinfo=None) >= cutoff
        except:
            return False


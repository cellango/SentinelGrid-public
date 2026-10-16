"""Analyzer registry - maps observable types to analyzers."""

from typing import List, Dict, Type, Optional
from .base_analyzer import BaseAnalyzer
import logging

logger = logging.getLogger(__name__)


class AnalyzerRegistry:
    """
    Central registry of all available analyzers.
    
    Maps observable types to analyzers and provides filtering capabilities.
    
    Usage:
        # Register an analyzer
        registry.register(ProwlerAnalyzer)
        
        # Get analyzers for an observable type
        analyzers = registry.get_analyzers_for_observable("web_application")
        
        # Filter by tags
        critical_analyzers = registry.get_analyzers_for_observable(
            "web_application",
            tags=["critical"]
        )
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._analyzers: Dict[str, Type[BaseAnalyzer]] = {}
        self._observable_mappings: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
    
    def register(self, analyzer_class: Type[BaseAnalyzer]) -> None:
        """
        Register an analyzer.
        
        Args:
            analyzer_class: Analyzer class (not instance)
        
        Raises:
            ValueError: If analyzer is invalid or already registered
        """
        # Validate analyzer
        if not issubclass(analyzer_class, BaseAnalyzer):
            raise ValueError(f"{analyzer_class} must inherit from BaseAnalyzer")
        
        analyzer_name = analyzer_class.name
        if not analyzer_name:
            raise ValueError(f"{analyzer_class.__name__} must define 'name'")
        
        if analyzer_name in self._analyzers:
            logger.warning(f"Analyzer {analyzer_name} already registered, replacing")
        
        # Register analyzer
        self._analyzers[analyzer_name] = analyzer_class
        
        # Build observable type mappings
        for obs_type in analyzer_class.supported_observable_types:
            if obs_type not in self._observable_mappings:
                self._observable_mappings[obs_type] = []
            if analyzer_name not in self._observable_mappings[obs_type]:
                self._observable_mappings[obs_type].append(analyzer_name)
        
        # Build tag index
        for tag in analyzer_class.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if analyzer_name not in self._tag_index[tag]:
                self._tag_index[tag].append(analyzer_name)
        
        logger.info(
            f"Registered analyzer: {analyzer_name} "
            f"(types: {analyzer_class.supported_observable_types}, "
            f"tags: {analyzer_class.tags})"
        )
    
    def unregister(self, analyzer_name: str) -> None:
        """
        Unregister an analyzer.
        
        Args:
            analyzer_name: Name of analyzer to unregister
        """
        if analyzer_name not in self._analyzers:
            return
        
        analyzer_class = self._analyzers[analyzer_name]
        
        # Remove from observable mappings
        for obs_type in analyzer_class.supported_observable_types:
            if obs_type in self._observable_mappings:
                if analyzer_name in self._observable_mappings[obs_type]:
                    self._observable_mappings[obs_type].remove(analyzer_name)
                if not self._observable_mappings[obs_type]:
                    del self._observable_mappings[obs_type]
        
        # Remove from tag index
        for tag in analyzer_class.tags:
            if tag in self._tag_index:
                if analyzer_name in self._tag_index[tag]:
                    self._tag_index[tag].remove(analyzer_name)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
        
        # Remove analyzer
        del self._analyzers[analyzer_name]
        logger.info(f"Unregistered analyzer: {analyzer_name}")
    
    def get_analyzer(self, analyzer_name: str) -> Optional[Type[BaseAnalyzer]]:
        """
        Get analyzer class by name.
        
        Args:
            analyzer_name: Name of analyzer
        
        Returns:
            Analyzer class or None if not found
        """
        return self._analyzers.get(analyzer_name)
    
    def get_analyzers_for_observable(
        self,
        observable_type: str,
        tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None
    ) -> List[Type[BaseAnalyzer]]:
        """
        Get all applicable analyzers for an observable type.
        
        Args:
            observable_type: Type of observable (e.g., "web_application")
            tags: Optional list of tags to filter by (ANY match)
            exclude_tags: Optional list of tags to exclude (ANY match)
        
        Returns:
            List of analyzer classes
        """
        # Get analyzers that support this observable type
        analyzer_names = self._observable_mappings.get(observable_type, [])
        analyzers = [self._analyzers[name] for name in analyzer_names]
        
        # Filter by tags (include)
        if tags:
            analyzers = [
                a for a in analyzers
                if any(tag in a.tags for tag in tags)
            ]
        
        # Filter by tags (exclude)
        if exclude_tags:
            analyzers = [
                a for a in analyzers
                if not any(tag in a.tags for tag in exclude_tags)
            ]
        
        return analyzers
    
    def get_analyzers_by_tag(self, tag: str) -> List[Type[BaseAnalyzer]]:
        """
        Get all analyzers with a specific tag.
        
        Args:
            tag: Tag to search for
        
        Returns:
            List of analyzer classes
        """
        analyzer_names = self._tag_index.get(tag, [])
        return [self._analyzers[name] for name in analyzer_names]
    
    def list_analyzers(self) -> List[Dict]:
        """
        List all registered analyzers.
        
        Returns:
            List of analyzer info dictionaries
        """
        return [
            {
                "name": a.name,
                "description": a.description,
                "version": a.version,
                "supported_types": a.supported_observable_types,
                "tags": a.tags,
                "timeout": a.timeout_seconds,
                "requires_credentials": a.requires_credentials,
            }
            for a in self._analyzers.values()
        ]
    
    def list_observable_types(self) -> List[str]:
        """
        List all supported observable types.
        
        Returns:
            List of observable type strings
        """
        return list(self._observable_mappings.keys())
    
    def list_tags(self) -> List[str]:
        """
        List all analyzer tags.
        
        Returns:
            List of tag strings
        """
        return list(self._tag_index.keys())
    
    def get_stats(self) -> Dict:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_analyzers": len(self._analyzers),
            "observable_types": len(self._observable_mappings),
            "tags": len(self._tag_index),
            "analyzers_by_type": {
                obs_type: len(analyzers)
                for obs_type, analyzers in self._observable_mappings.items()
            }
        }
    
    def __len__(self) -> int:
        """Return number of registered analyzers."""
        return len(self._analyzers)
    
    def __repr__(self) -> str:
        return f"<AnalyzerRegistry(analyzers={len(self._analyzers)})>"


# Global registry instance
registry = AnalyzerRegistry()


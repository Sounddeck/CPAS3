"""
Event Bus for CPAS
Provides a communication channel between modules
"""
import logging
from typing import Dict, List, Callable, Any

logger = logging.getLogger(__name__)

class EventBus:
    """
    Event bus that allows modules to subscribe to and publish events.
    Provides a decoupled communication mechanism between components.
    """
    
    def __init__(self):
        """Initialize the event bus"""
        self.subscribers: Dict[str, List[Callable]] = {}
        logger.info("Event bus initialized")
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type
        
        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to event: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe from an event type
        
        Args:
            event_type: The type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from event: {event_type}")
    
    def publish(self, event_type: str, **kwargs) -> None:
        """
        Publish an event of the specified type
        
        Args:
            event_type: The type of event to publish
            **kwargs: Data to pass to subscribers
        """
        if event_type not in self.subscribers:
            return
        
        # Add event type to kwargs for context
        kwargs['event_type'] = event_type
        
        # Notify all subscribers
        logger.debug(f"Publishing event: {event_type} with data: {kwargs}")
        for callback in self.subscribers[event_type]:
            try:
                callback(**kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def clear_subscribers(self, event_type: str = None) -> None:
        """
        Clear all subscribers for an event type, or all subscribers if no type specified
        
        Args:
            event_type: The event type to clear, or None to clear all
        """
        if event_type:
            if event_type in self.subscribers:
                self.subscribers[event_type] = []
                logger.debug(f"Cleared subscribers for event: {event_type}")
        else:
            self.subscribers.clear()
            logger.debug("Cleared all event subscribers")

# Create singleton instance
event_bus = EventBus()

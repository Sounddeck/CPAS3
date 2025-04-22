"""
Performance analytics for agents
Tracks and visualizes agent performance metrics
"""

import time
import threading
import logging
from typing import Dict, List, Any
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Tracks and analyzes agent performance metrics"""
    
    def __init__(self, max_history: int = 100):
        """Initialize the performance tracker"""
        self.max_history = max_history
        self.metrics = {}  # agent_id -> metric_type -> list of (timestamp, value) tuples
        self.lock = threading.Lock()
        logger.info("Performance tracker initialized")
    
    def add_metric(self, agent_id: str, metric_type: str, value: float) -> None:
        """Add a performance metric data point"""
        with self.lock:
            if agent_id not in self.metrics:
                self.metrics[agent_id] = {}
                
            if metric_type not in self.metrics[agent_id]:
                self.metrics[agent_id][metric_type] = []
                
            # Add the data point
            data_point = (time.time(), value)
            self.metrics[agent_id][metric_type].append(data_point)
            
            # Trim if needed
            if len(self.metrics[agent_id][metric_type]) > self.max_history:
                self.metrics[agent_id][metric_type] = self.metrics[agent_id][metric_type][-self.max_history:]
    
    def get_metrics(self, agent_id: str, metric_type: str = None, 
                   start_time: float = None, end_time: float = None) -> Dict[str, List[tuple]]:
        """Get metrics for an agent"""
        with self.lock:
            if agent_id not in self.metrics:
                return {}
                
            result = {}
            
            # If metric type is specified, return just that type
            if metric_type:
                if metric_type in self.metrics[agent_id]:
                    metrics = self.metrics[agent_id][metric_type]
                    # Filter by time range if specified
                    if start_time or end_time:
                        filtered_metrics = []
                        for ts, val in metrics:
                            if (start_time is None or ts >= start_time) and \
                               (end_time is None or ts <= end_time):
                                filtered_metrics.append((ts, val))
                        result[metric_type] = filtered_metrics
                    else:
                        result[metric_type] = metrics.copy()
            else:
                # Return all metric types for the agent
                for m_type, metrics in self.metrics[agent_id].items():
                    # Filter by time range if specified
                    if start_time or end_time:
                        filtered_metrics = []
                        for ts, val in metrics:
                            if (start_time is None or ts >= start_time) and \
                               (end_time is None or ts <= end_time):
                                filtered_metrics.append((ts, val))
                        result[m_type] = filtered_metrics
                    else:
                        result[m_type] = metrics.copy()
                        
            return result
    
    def generate_chart(self, agent_id: str, metric_type: str, 
                      width: int = 800, height: int = 400,
                      hours: float = 1.0) -> str:
        """Generate a chart for a specific metric and return as base64 PNG"""
        try:
            end_time = time.time()
            start_time = end_time - (hours * 3600)  # Convert hours to seconds
            
            metrics = self.get_metrics(
                agent_id, 
                metric_type, 
                start_time=start_time,
                end_time=end_time
            )
            
            if not metrics or metric_type not in metrics or not metrics[metric_type]:
                logger.warning(f"No metrics found for agent {agent_id}, type {metric_type}")
                return ""
                
            # Create the plot
            fig = Figure(figsize=(width / 100, height / 100), dpi=100)
            ax = fig.add_subplot(111)
            
            # Extract timestamps and values
            timestamps = [ts for ts, _ in metrics[metric_type]]
            values = [val for _, val in metrics[metric_type]]
            
            # Convert timestamps to relative time (minutes ago)
            relative_times = [(end_time - ts) / 60 for ts in timestamps]
            relative_times.reverse()  # Reverse so time flows left to right
            values.reverse()  # Keep values aligned with times
            
            # Plot the data
            ax.plot(relative_times, values, 'b-')
            
            # Add labels and title
            ax.set_xlabel('Minutes Ago')
            ax.set_ylabel(metric_type)
            ax.set_title(f'{metric_type} for {agent_id}')
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            fig.tight_layout()
            
            # Save to BytesIO buffer
            buf = BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            
            # Convert to base64
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            return ""

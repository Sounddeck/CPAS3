import logging
import time
import uuid
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage # Import SystemMessage

from .base_agent import Agent, AgentStatus
from ..task_queue import Task
from ..monitoring.performance_tracker import PerformanceTracker
from ..memory.agent_memory import AgentMemory

# Import default prompt - adjust path if necessary
from ..prompts.react_prompt import REACT_PROMPT_TEMPLATE_STR

if TYPE_CHECKING:
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.tools import BaseTool
    from ..agent_manager import AgentManager

logger = logging.getLogger(__name__)

class TaskAgent(Agent):
    """
    An agent designed to execute specific tasks using a ReAct (Reasoning and Acting)
    framework or other structured execution methods.
    """
    type: str = "Task" # Class attribute for type identification

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: Optional[str] = None,
        llm: Optional['BaseLanguageModel'] = None,
        tools: Optional[List['BaseTool']] = None,
        agent_manager: Optional['AgentManager'] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
        initial_status: AgentStatus = AgentStatus.INITIALIZING,
        state: Optional[Dict[str, Any]] = None,
        prompt_template_str: Optional[str] = None,
        max_iterations: int = 10, # Limit ReAct loop iterations
        memory: Optional[AgentMemory] = None,
        **kwargs # Allow for additional state parameters
    ):
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            llm=llm,
            agent_manager=agent_manager,
            performance_tracker=performance_tracker,
            initial_status=initial_status,
            state=state
        )

        self.tools = tools if tools is not None else []
        self.max_iterations = max_iterations
        self.memory = memory if memory is not None else AgentMemory(agent_id=self.id) # Use AgentMemory

        # --- Agent Executor Setup ---
        # Use provided prompt template or default ReAct prompt
        prompt_str = prompt_template_str or REACT_PROMPT_TEMPLATE_STR
        try:
            self.prompt = PromptTemplate.from_template(prompt_str)

            if not self.llm:
                logger.warning(f"TaskAgent '{self.name}' initialized without an LLM. Execution will fail.")
                self.agent_executor = None
                self.set_status(AgentStatus.ERROR, "Missing LLM configuration")
                return # Stop initialization if LLM is missing

            # Ensure tools are correctly passed to create_react_agent
            if not self.tools:
                 logger.warning(f"TaskAgent '{self.name}' initialized without tools. Functionality may be limited.")

            # Create the ReAct agent runnable
            react_agent_runnable = create_react_agent(self.llm, self.tools or [], self.prompt)

            # Create the AgentExecutor
            self.agent_executor = AgentExecutor(
                agent=react_agent_runnable,
                tools=self.tools or [],
                verbose=True,  # Enable verbose logging for debugging ReAct steps
                max_iterations=self.max_iterations,
                handle_parsing_errors=True, # Attempt to handle LLM output parsing errors
                memory=self.memory, # Pass the memory object here
            )
            logger.info(f"TaskAgent '{self.name}' initialized with ReAct executor.")
            logger.debug(f"TaskAgent '{self.name}' available tools: {[tool.name for tool in self.tools]}")

        except Exception as e:
            logger.error(f"Failed to initialize ReAct executor for agent '{self.name}': {e}", exc_info=True)
            self.agent_executor = None
            self.set_status(AgentStatus.ERROR, f"Executor init failed: {e}")

        # Restore memory if state contains it
        if state and 'memory' in state:
             try:
                  self.memory.load_from_state(state['memory'])
                  logger.info(f"Restored memory for agent {self.name}")
             except Exception as e:
                  logger.error(f"Failed to restore memory for agent {self.name}: {e}", exc_info=True)


        logger.info(f"TaskAgent '{self.name}' ({self.id}) initialized.")


    def get_serializable_state(self) -> Dict[str, Any]:
        """Return the agent's current state for persistence."""
        state = super().get_serializable_state()
        state.update({
            "type": self.type,
            "max_iterations": self.max_iterations,
            "prompt_template_str": self.prompt.template if self.prompt else None,
            "memory": self.memory.get_serializable_state() if self.memory else None,
            # Tools and LLM are generally not serialized directly, they are dependencies.
            # The AgentManager should handle re-injecting them on load.
        })
        return state

    def _run(self):
        """
        Continuously process tasks from the queue assigned to this agent.
        This overrides the base agent's _run method.
        """
        if not self.agent_executor:
            logger.error(f"Agent {self.name} cannot run: AgentExecutor not initialized.")
            self.set_status(AgentStatus.ERROR, "AgentExecutor not initialized.")
            return

        logger.info(f"TaskAgent {self.name} starting run loop.")
        while self.status == AgentStatus.RUNNING:
            task = None
            try:
                # Fetch a task specifically for this agent
                if self.agent_manager and self.agent_manager.task_queue:
                    task = self.agent_manager.task_queue.get_task(self.id)

                if task:
                    logger.info(f"Agent {self.name} processing task: {task.task_id} - {task.description[:50]}...")
                    self._process_task(task)
                else:
                    # No task found for this agent, wait a bit
                    self.set_status(AgentStatus.IDLE) # Go idle if queue is empty
                    logger.debug(f"Agent {self.name} found no tasks, going idle.")
                    # Optional: sleep for a short duration before checking again
                    # time.sleep(1) # Avoid busy-waiting if status immediately set back to RUNNING
                    # If status remains IDLE, the loop will exit in the next check.
                    # If status becomes RUNNING again (e.g., new task added and agent started),
                    # the loop continues.

            except Exception as e:
                logger.error(f"Error in TaskAgent {self.name} run loop: {e}", exc_info=True)
                self.set_status(AgentStatus.ERROR, f"Run loop error: {e}")
                if task:
                    # Optionally mark the task as failed
                    if self.agent_manager and self.agent_manager.task_queue:
                        self.agent_manager.task_queue.update_task_status(task.task_id, "failed", {"error": str(e)})
                # Consider whether to break the loop or attempt recovery
                time.sleep(5) # Wait before potentially retrying

        logger.info(f"TaskAgent {self.name} run loop finished with status {self.status}.")


    def _process_task(self, task: Task):
        """Executes a single task using the ReAct agent executor."""
        if not self.agent_executor:
            logger.error(f"Cannot process task {task.task_id}: AgentExecutor not initialized.")
            self.set_status(AgentStatus.ERROR, "AgentExecutor not initialized.")
            if self.agent_manager and self.agent_manager.task_queue:
                self.agent_manager.task_queue.update_task_status(task.task_id, "failed", {"error": "AgentExecutor not initialized."})
            return

        self.set_status(AgentStatus.THINKING)
        start_time_ns = time.perf_counter_ns()
        success = False
        error_message = None
        result = None
        timer_id = f"react_task_execution_{uuid.uuid4().int}"

        if self.performance_tracker:
            self.performance_tracker.start_timer(self.id, timer_id, start_time_ns)

        try:
            # Prepare inputs for the agent executor
            # CRITICAL CHANGE: Only include keys the agent prompt expects.
            # DO NOT include 'intermediate_steps' here.
            agent_input = {
                "input": task.data.get("input", task.description), # Use task description if no specific input
                # Add chat_history if the prompt/agent uses it
                # "chat_history": self.memory.chat_memory.messages, # Uncomment if needed
            }
            logger.debug(f"Invoking agent executor for task {task.task_id} with input keys: {list(agent_input.keys())}")

            # Define the config for the execution
            config = RunnableConfig(
                configurable={"session_id": task.task_id}, # Use task_id as session_id for memory
                callbacks=self.callback_manager.get_callbacks() # Get callbacks from base class
            )

            # Execute the agent
            response = self.agent_executor.invoke(agent_input, config=config) # Pass only agent_input

            result = response.get("output", "No output generated.")
            logger.info(f"Task {task.task_id} completed. Result: {result[:100]}...")
            success = True
            self.set_status(AgentStatus.IDLE) # Task done, go idle until next task

        except Exception as e:
            error_message = f"Error during ReAct execution for task {task.task_id} in agent {self.name}: {e}"
            logger.error(error_message, exc_info=True)
            result = {"error": str(e)}
            self.set_status(AgentStatus.FAILED) # Mark agent as failed if task execution fails
            success = False

        finally:
            # Stop performance timer
            if self.performance_tracker:
                duration_ms = self.performance_tracker.stop_timer(self.id, timer_id)
                logger.debug(f"Task {task.task_id} execution duration: {duration_ms:.2f} ms. Success: {success}")

            # Update task status in the queue
            if self.agent_manager and self.agent_manager.task_queue:
                final_status = "completed" if success else "failed"
                self.agent_manager.task_queue.update_task_status(task.task_id, final_status, result)

            # Persist agent state (including memory) after processing
            self.save_state()


    def add_tool(self, tool: 'BaseTool'):
        """Adds a tool to the agent and updates the executor if possible."""
        if tool not in self.tools:
            self.tools.append(tool)
            logger.info(f"Added tool '{tool.name}' to agent '{self.name}'.")
            # Re-initialize the agent executor with the new toolset
            self._reinitialize_executor()
        else:
            logger.warning(f"Tool '{tool.name}' already present in agent '{self.name}'.")

    def remove_tool(self, tool_name: str):
        """Removes a tool from the agent and updates the executor."""
        initial_len = len(self.tools)
        self.tools = [t for t in self.tools if t.name != tool_name]
        if len(self.tools) < initial_len:
            logger.info(f"Removed tool '{tool_name}' from agent '{self.name}'.")
            self._reinitialize_executor()
        else:
            logger.warning(f"Tool '{tool_name}' not found in agent '{self.name}'.")

    def _reinitialize_executor(self):
        """Helper method to re-create the agent executor after changes (e.g., tools)."""
        if not self.llm or not self.prompt:
             logger.error(f"Cannot reinitialize executor for '{self.name}': Missing LLM or prompt.")
             self.agent_executor = None
             self.set_status(AgentStatus.ERROR, "Cannot reinit executor: missing LLM/prompt")
             return
        try:
            react_agent_runnable = create_react_agent(self.llm, self.tools or [], self.prompt)
            self.agent_executor = AgentExecutor(
                agent=react_agent_runnable,
                tools=self.tools or [],
                verbose=True,
                max_iterations=self.max_iterations,
                handle_parsing_errors=True,
                memory=self.memory, # Ensure memory is passed again
            )
            logger.info(f"Re-initialized AgentExecutor for '{self.name}' with {len(self.tools)} tools.")
            # If status was ERROR due to previous init failure, reset it
            if self.status == AgentStatus.ERROR:
                 self.set_status(AgentStatus.IDLE)
        except Exception as e:
            logger.error(f"Failed to re-initialize ReAct executor for agent '{self.name}': {e}", exc_info=True)
            self.agent_executor = None
            self.set_status(AgentStatus.ERROR, f"Executor re-init failed: {e}")

    def stop(self):
        """Stops the agent's run loop."""
        if self.status in [AgentStatus.RUNNING, AgentStatus.THINKING]:
             logger.info(f"Stopping TaskAgent {self.name}...")
             # Set status to STOPPED first to signal the loop to exit
             self.set_status(AgentStatus.STOPPED)
             # The loop in _run() should detect the status change and exit.
             # If the agent is stuck in invoke(), stopping might be delayed.
             # Consider adding thread join with timeout if needed, but
             # changing status is usually sufficient for cooperative exit.
        else:
             logger.info(f"TaskAgent {self.name} is not running or thinking, setting status to STOPPED.")
             self.set_status(AgentStatus.STOPPED)
        self.save_state() # Save state on stop


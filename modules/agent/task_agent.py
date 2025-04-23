import logging
import time
import threading
from typing import List, Dict, Any, Optional

# Langchain imports
from langchain.agents import AgentExecutor, create_react_agent # Using ReAct agent type
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain.prompts import PromptTemplate # Or load from hub
from langchain.memory import ConversationBufferWindowMemory # Example memory type
from langchain_core.callbacks import BaseCallbackHandler # For custom callbacks if needed
from langchain_core.prompts.chat import MessagesPlaceholder

# Local imports
from ..base_agent import BaseAgent, AgentStatus
from ..task_queue import Task, TaskStatus, TaskQueue # Import Task and its status
from ..callback_manager import CallbackManager # Use the central callback manager
from ..monitoring.performance_tracker import PerformanceTracker # For tracking performance if needed
# from ..prompts.react_prompt import REACT_PROMPT_TEMPLATE_STR # Example of loading a local prompt string

# Import signal emitter safely
try:
    from ...ui.signal_emitter import signal_emitter
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False
    class DummySignalEmitter:
        def __getattr__(self, name):
            class DummySignal:
                def emit(self, *args, **kwargs): pass
            return DummySignal()
    signal_emitter = DummySignalEmitter()
    # logging.info("TaskAgent running without UI signal emitter.") # Less verbose


logger = logging.getLogger(__name__)

# --- Default ReAct Prompt Template (Example) ---
# You might load this from a file or config instead
# Ensure this prompt template is compatible with the tools provided and the LLM's capabilities.
DEFAULT_REACT_PROMPT_STR = """
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}
"""

# --- Default Prompt Template ---
# This creates the actual prompt structure expected by create_react_agent
DEFAULT_REACT_PROMPT_TEMPLATE = PromptTemplate.from_template(DEFAULT_REACT_PROMPT_STR)


class TaskAgent(BaseAgent):
    """
    A specific agent implementation focused on executing tasks using Langchain's ReAct framework.
    """
    type: str = "TaskAgent" # Class variable defining the agent type

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm: BaseChatModel,
        tools: List[BaseTool],
        agent_manager: Optional[Any] = None, # Expecting AgentManager instance
        callback_manager: Optional[CallbackManager] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
        description: Optional[str] = None,
        prompt_template: Optional[PromptTemplate] = None,
        prompt_template_str: Optional[str] = None, # Allow passing prompt string directly
        memory: Optional[Any] = None, # Allow injecting memory, e.g., ConversationBufferWindowMemory
        memory_k: int = 5, # Default window size for memory
        max_iterations: int = 15,
        handle_parsing_errors: bool = True,
        verbose: bool = False, # Controls Langchain verbosity
        state: Optional[Dict[str, Any]] = None,
        **kwargs # Allow BaseAgent args like initial_status, on_stop_callback
    ):
        # Initialize BaseAgent first
        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            llm=llm, # Pass LLM to base if needed, or just store here
            agent_manager=agent_manager,
            performance_tracker=performance_tracker,
            callback_manager=callback_manager or (agent_manager.callback_manager if agent_manager else None),
            state=state,
            **kwargs # Pass remaining kwargs like initial_status, on_stop_callback
        )

        if not llm:
            logger.error(f"TaskAgent '{name}' ({self.id[:8]}): LLM dependency is missing.")
            self.set_status(AgentStatus.ERROR, message="LLM is required.", initial_setup=True)
            raise ValueError("TaskAgent requires an LLM instance.")
        if not tools:
             logger.warning(f"TaskAgent '{name}' ({self.id[:8]}): No tools provided.")
             # Agent might still function for simple prompts, but tool use is expected

        self.llm = llm
        self.tools = tools
        self.max_iterations = max_iterations
        self.handle_parsing_errors = handle_parsing_errors
        self.verbose_langchain = verbose # Separate from agent's general logging level

        # --- Setup Prompt ---
        if prompt_template:
             self.prompt = prompt_template
        elif prompt_template_str:
             try:
                  self.prompt = PromptTemplate.from_template(prompt_template_str)
             except Exception as e:
                  logger.error(f"Failed to create prompt from provided string for agent {self.id[:8]}: {e}. Using default.", exc_info=True)
                  self.prompt = DEFAULT_REACT_PROMPT_TEMPLATE
        else:
             # Use the default ReAct prompt if none provided
             self.prompt = DEFAULT_REACT_PROMPT_TEMPLATE
             logger.info(f"Agent {self.id[:8]} using default ReAct prompt template.")

        # --- Setup Memory ---
        # Note: Memory state persistence across restarts needs careful handling.
        # For simplicity here, we re-create memory on init. Restore from state if needed.
        if memory:
            self.memory = memory
        else:
            # Example: Use conversation buffer memory
            self.memory = ConversationBufferWindowMemory(
                k=memory_k,
                memory_key="chat_history", # Must match placeholder if used in prompt
                input_key="input", # Key for user input
                output_key="output" # Key for agent's final answer
                # return_messages=True # Set True if LLM expects message objects
            )
        logger.info(f"Agent {self.id[:8]} initialized with memory type: {type(self.memory).__name__}")

        # Add chat_history placeholder if memory uses it and prompt doesn't have it
        # This is crucial for create_react_agent if memory is involved.
        if "chat_history" in self.memory.memory_variables and "chat_history" not in self.prompt.input_variables:
             if isinstance(self.prompt, PromptTemplate) and hasattr(self.prompt, 'template'):
                  # Attempt to add placeholder - this might need adjustment based on exact prompt type
                  try:
                       # This assumes a basic string template. More complex prompts need different handling.
                       if "{chat_history}" not in self.prompt.template:
                            logger.warning(f"Agent {self.id[:8]} prompt doesn't include '{{chat_history}}' placeholder required by memory. Attempting to add.")
                            # A common pattern is adding it before the scratchpad
                            if "{agent_scratchpad}" in self.prompt.template:
                                 self.prompt.template = self.prompt.template.replace("{agent_scratchpad}", "{chat_history}\n{agent_scratchpad}")
                                 self.prompt.input_variables.append("chat_history") # Manually add variable
                            else:
                                 logger.error("Cannot automatically add chat_history placeholder to this prompt structure.")
                                 # Consider raising an error or disabling memory?
                       else:
                            # Placeholder exists, ensure it's in input_variables
                            if "chat_history" not in self.prompt.input_variables:
                                 self.prompt.input_variables.append("chat_history")
                  except Exception as e:
                       logger.error(f"Error adjusting prompt for chat_history placeholder: {e}", exc_info=True)
             else:
                  logger.warning(f"Memory requires 'chat_history', but prompt type ({type(self.prompt)}) is not a simple PromptTemplate. Manual adjustment may be needed.")


        # --- Create Langchain Agent ---
        # Use the create_react_agent function which sets up the specific prompt formatting
        try:
            # Ensure tools are available to the prompt rendering
            if "tools" not in self.prompt.input_variables or "tool_names" not in self.prompt.input_variables:
                 logger.warning(f"ReAct prompt for {self.id[:8]} missing 'tools' and/or 'tool_names' variables. Agent might not list tools correctly.")
                 # Attempt to add if possible, otherwise agent creation might fail or malfunction
                 # prompt.input_variables.extend(["tools", "tool_names"]) # This might break prompts not expecting them

            # Create the runnable agent part (LLM + prompt binding)
            self.agent_runnable = create_react_agent(
                 llm=self.llm,
                 tools=self.tools,
                 prompt=self.prompt
            )
        except Exception as e:
            logger.error(f"Failed create react agent runnable for {self.id[:8]}: {e}", exc_info=True)
            self.set_status(AgentStatus.ERROR, message=f"Failed create agent runnable: {e}", initial_setup=True)
            raise

        # --- Create Agent Executor ---
        # The executor runs the agent loop (thought, action, observation)
        try:
            # Get callbacks from the central manager
            callbacks = self.get_callback_manager().get_callbacks_for_agent(self.id) if self.get_callback_manager() else None

            self.executor = AgentExecutor(
                agent=self.agent_runnable,
                tools=self.tools,
                memory=self.memory,
                verbose=self.verbose_langchain,
                max_iterations=self.max_iterations,
                handle_parsing_errors=self.handle_parsing_errors, # Can provide custom handler
                callbacks=callbacks # Pass the collected callbacks
                # early_stopping_method="generate", # Stop if LLM generates Final Answer token
                # return_intermediate_steps=False # Set True if you need to see the steps
            )
            logger.info(f"TaskAgent '{self.name}' ({self.id[:8]}) initialized successfully.")
            # Initial status is set by BaseAgent, usually INITIALIZING then IDLE/STOPPED after load/create

        except Exception as e:
            logger.error(f"Failed to create AgentExecutor for '{self.name}' ({self.id[:8]}): {e}", exc_info=True)
            self.set_status(AgentStatus.ERROR, message=f"Executor creation failed: {e}", initial_setup=True)
            # Raise error to prevent agent from being used incorrectly
            raise ValueError(f"AgentExecutor creation failed for {self.name}: {e}")


    def get_serializable_state(self) -> Dict[str, Any]:
        """Returns agent state including TaskAgent specifics."""
        state = super().get_serializable_state()
        state.update({
            "max_iterations": self.max_iterations,
            "verbose_langchain": self.verbose_langchain,
            "memory_k": getattr(self.memory, 'k', None), # Get k if memory has it
            "memory_type": type(self.memory).__name__,
            # Optionally serialize memory content if feasible and desired
            # "memory_state": self.memory.save_context(...) # Depends on memory type
            "prompt_template": self.prompt.template if hasattr(self.prompt, 'template') else str(self.prompt),
        })
        return state

    def _run(self):
        """
        Main execution loop for the TaskAgent.
        Continuously checks for tasks in the queue and executes them.
        """
        if not self._agent_manager:
            logger.error(f"Agent {self.id[:8]} cannot run: AgentManager not available.")
            self.set_status(AgentStatus.ERROR, message="AgentManager missing.")
            return
        if not isinstance(self._agent_manager.task_queue, TaskQueue):
             logger.error(f"Agent {self.id[:8]} cannot run: Invalid TaskQueue provided by AgentManager.")
             self.set_status(AgentStatus.ERROR, message="Invalid TaskQueue.")
             return

        task_queue = self._agent_manager.task_queue
        logger.info(f"Agent '{self.name}' ({self.id[:8]}) starting run loop. Waiting for tasks...")
        self.set_status(AgentStatus.IDLE) # Ready to accept tasks

        while not self._stop_event.is_set():
            current_task: Optional[Task] = None
            try:
                # Wait for a task, with a timeout to allow checking the stop event
                # Pass self.id to get_task so queue knows who is asking
                current_task = task_queue.get_task(agent_id=self.id, block=True, timeout=1.0)

                if current_task:
                    logger.info(f"Agent '{self.name}' ({self.id[:8]}) picked up task {current_task.task_id[:8]}: '{current_task.description[:50]}...'")
                    self._current_task_id = current_task.task_id # Track current task
                    self.set_status(AgentStatus.RUNNING, message=f"Starting task {current_task.task_id[:8]}")
                    task_queue.update_task_progress(current_task.task_id, self.id) # Mark as IN_PROGRESS

                    # --- Execute the task ---
                    task_input = current_task.description # Or construct from current_task.data
                    task_result = None
                    task_error = None

                    try:
                        # Core Langchain execution
                        # Prepare inputs for the executor, including memory variables if needed
                        executor_input = {"input": task_input}
                        # Add memory variables if they exist in memory but not directly in input
                        # This depends heavily on the specific memory and agent setup
                        # if "chat_history" in self.memory.memory_variables:
                        #      executor_input["chat_history"] = self.memory.load_memory_variables({})["chat_history"]

                        self.set_status(AgentStatus.THINKING, message=f"Executing task {current_task.task_id[:8]}")
                        logger.debug(f"Invoking AgentExecutor for task {current_task.task_id[:8]} with input: {executor_input}")

                        # Invoke the executor - this runs the ReAct loop
                        response = self.executor.invoke(
                             executor_input,
                             # Pass agent_id to callbacks if needed via config
                             config={'callbacks': self.get_callback_manager().get_callbacks_for_agent(self.id, task_id=current_task.task_id)} if self.get_callback_manager() else None
                             )

                        logger.debug(f"AgentExecutor response for task {current_task.task_id[:8]}: {response}")

                        # Extract the final answer - depends on AgentExecutor output structure
                        # For standard agents, it's usually in the 'output' key
                        task_result = response.get('output', str(response)) # Fallback to string representation
                        logger.info(f"Task {current_task.task_id[:8]} completed successfully by agent {self.id[:8]}.")
                        task_queue.complete_task(current_task.task_id, result=task_result)

                    except Exception as e:
                        logger.error(f"Agent '{self.name}' ({self.id[:8]}) failed task {current_task.task_id[:8]}: {e}", exc_info=True)
                        task_error = str(e)
                        task_queue.fail_task(current_task.task_id, error_message=task_error)
                        # Optionally set agent status to FAILED temporarily? Or just log error?
                        # self.set_status(AgentStatus.FAILED, message=f"Task execution error: {e}")
                        # Revert to IDLE after failure to potentially pick up new tasks
                    finally:
                         # Signal that this task processing attempt is done for queue joining purposes
                         # Needs careful implementation in TaskQueue if used.
                         # task_queue.task_done(current_task.task_id) # Call task_done after processing attempt

                         self.set_status(AgentStatus.IDLE) # Ready for next task
                         self._current_task_id = None # Clear current task tracking
                         self.save_state() # Save state after task completion/failure

                else:
                    # No task received, stay IDLE. Loop will check stop_event and wait again.
                    if self.status != AgentStatus.IDLE:
                         self.set_status(AgentStatus.IDLE) # Ensure status is IDLE if queue is empty
                    # Optional: Add a small sleep here if timeout is very short or None
                    # time.sleep(0.1) # Avoid busy-waiting if block=False or timeout=0

            except queue.Empty:
                 # Expected when queue is empty and timeout occurs
                 if self.status != AgentStatus.IDLE:
                      self.set_status(AgentStatus.IDLE)
                 continue # Go back to start of loop to check stop_event

            except Exception as loop_error:
                # Catch broader errors in the loop itself (e.g., queue access issues)
                logger.error(f"Agent '{self.name}' ({self.id[:8]}) encountered error in main loop: {loop_error}", exc_info=True)
                self.set_status(AgentStatus.FAILED, message=f"Run loop error: {loop_error}")
                # Should we break the loop on general errors? Or try to recover?
                # For now, log and continue, but might need more robust handling.
                time.sleep(5) # Pause briefly after a major loop error

        logger.info(f"Agent '{self.name}' ({self.id[:8]}) run loop stopped.")
        # Final status (STOPPED or FAILED) is typically set by the _run_wrapper in BaseAgent


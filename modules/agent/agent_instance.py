import logging
import threading
import asyncio
import queue # Use standard queue
import time # For timing checks
import traceback # For logging tracebacks
import datetime # For state timestamps
from typing import List, Dict, Optional, Any

# LangChain components (assuming AgentExecutor is passed in)
from langchain.agents import AgentExecutor
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel

# Local imports
from .models import AgentStatus, AgentTask, AgentConfig, AgentState, HistoryEntry
from .persistence.agent_store import AgentStore # For saving state
from ..utils.history_manager import HistoryManager # For logging history
from .task_queue import TaskQueue # Ensure correct import if TaskQueue is a custom class

# Import the shared signal emitter
try:
    from ..ui.signal_emitter import signal_emitter
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False
    class DummySignalEmitter:
        def __getattr__(self, name):
            class DummySignal:
                def emit(self, *args, **kwargs): pass
            return DummySignal()
    # logger.info("AgentInstance running without UI signal emitter.")


logger = logging.getLogger(__name__)

class AgentInstance:
    """
    Represents a single, stateful agent instance that can execute tasks.
    """
    def __init__(
        self,
        agent_id: str,
        name: str,
        config: AgentConfig,
        llm: BaseChatModel,
        tools: List[BaseTool],
        agent_executor: AgentExecutor,
        task_queue: TaskQueue, # Expecting TaskQueue instance
        agent_store: AgentStore,
        history_manager: HistoryManager,
        initial_status: AgentStatus = AgentStatus.IDLE,
        on_stop_callback: Optional[callable] = None # Callback when thread stops
    ):
        self.id = agent_id
        self.name = name
        self.config = config
        self.llm = llm
        self.tools = tools
        self.agent_executor = agent_executor
        self._task_queue = task_queue # The shared queue instance
        self._agent_store = agent_store
        self._history_manager = history_manager
        self._status = initial_status
        self.current_task_id: Optional[str] = None

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._on_stop_callback = on_stop_callback

        # Load history if available
        self._history_manager.load_history(self.id)

        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) initialized with status: {self._status.name}")

    @property
    def status(self) -> AgentStatus:
        return self._status

    def _set_status(self, new_status: AgentStatus):
        """Updates the agent's status and emits a signal."""
        if self._status != new_status:
            old_status = self._status
            self._status = new_status
            logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) status changed from {old_status.name} to {new_status.name}")
            # Add history entry for status change
            try:
                 # *** CORRECTED METHOD NAME (AGAIN - using 'add') ***
                 self._history_manager.add(
                     self.id,
                     HistoryEntry(
                         entry_type="status_change",
                         content={"old": old_status.name, "new": new_status.name}
                     )
                 )
            except AttributeError:
                 # If 'add' fails, log a specific error
                 logger.error(f"HistoryManager has no 'add' method. Cannot log status change for agent {self.id[:8]}. Check HistoryManager definition.")
            except Exception as hist_e:
                 logger.error(f"Failed to add status change history entry for agent {self.id[:8]}: {hist_e}", exc_info=True)

            # Emit signal for UI update
            try:
                 # *** CORRECTED SIGNAL EMISSION - pass enum member ***
                 signal_emitter.agent_status_updated.emit(self.id, new_status)
            except TypeError as sig_e:
                 logger.error(f"TypeError emitting agent_status_updated signal for {self.id[:8]}: {sig_e}. Expected signature [str, AgentStatus]. Passed [str, {type(new_status)}].", exc_info=True)
            except Exception as sig_e:
                 logger.error(f"Error emitting agent_status_updated signal for {self.id[:8]}: {sig_e}", exc_info=True)

            # Persist state change
            self.save_state() # Save state whenever status changes

    def get_state(self) -> AgentState:
        """Returns the current serializable state of the agent."""
        # Placeholder for created_at logic
        created_at_ts = None
        # Logic to get actual created_at if available

        return AgentState(
            agent_id=self.id,
            name=self.name,
            status=self._status,
            config=self.config,
            created_at=created_at_ts,
            last_updated=datetime.datetime.utcnow()
        )

    def save_state(self):
        """Saves the agent's current state using the AgentStore."""
        try:
            state = self.get_state()
            self._agent_store.save_agent_state(self.id, state)
        except Exception as e:
            logger.error(f"Failed to save state for agent '{self.name}' (ID: {self.id[:8]}): {e}", exc_info=True)

    @classmethod
    def from_state(
        cls,
        state_data: Dict[str, Any],
        llm: BaseChatModel,
        tools: List[BaseTool],
        agent_executor: AgentExecutor,
        task_queue: TaskQueue,
        agent_store: AgentStore,
        history_manager: HistoryManager,
        on_stop_callback: Optional[callable] = None,
        default_config: Optional[AgentConfig] = None
        ) -> Optional['AgentInstance']:
        """Creates an AgentInstance from a previously saved state dictionary."""
        try:
            agent_state = AgentState.from_dict(state_data)
            config_to_use = agent_state.config
            if default_config:
                 temp_config_data = default_config.model_dump()
                 temp_config_data.update(agent_state.config.model_dump(exclude_unset=True))
                 try:
                      config_to_use = AgentConfig(**temp_config_data)
                 except Exception as val_err:
                      logger.warning(f"Validation error merging loaded config for agent {agent_state.agent_id[:8]}: {val_err}. Using loaded config.", exc_info=True)
                      config_to_use = agent_state.config # Fallback

            initial_status = agent_state.status
            if initial_status not in AgentStatus:
                 logger.warning(f"Invalid status '{initial_status}' loaded for agent {agent_state.agent_id[:8]}. Setting to STOPPED.")
                 initial_status = AgentStatus.STOPPED

            instance = cls(
                agent_id=agent_state.agent_id, name=agent_state.name, config=config_to_use,
                llm=llm, tools=tools, agent_executor=agent_executor, task_queue=task_queue,
                agent_store=agent_store, history_manager=history_manager,
                initial_status=initial_status, on_stop_callback=on_stop_callback
            )
            # created_at handling if needed
            # if agent_state.created_at: instance.created_at = agent_state.created_at
            return instance
        except Exception as e:
            logger.error(f"Failed to create AgentInstance from state: {e}", exc_info=True)
            return None


    async def _process_task(self, task: AgentTask):
        """Handles the execution of a single task using AgentExecutor."""
        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) processing task {task.task_id[:8]}: '{task.description[:50]}...'")
        self.current_task_id = task.task_id
        task.status = "running"
        # Emit task status update signal
        try:
             signal_emitter.task_status_updated.emit(self.id, task.task_id, task.status, None)
        except Exception as sig_e:
             logger.error(f"Error emitting task_status_updated (running) signal for task {task.task_id[:8]}: {sig_e}", exc_info=True)

        # Add history entry for task start
        try:
             # *** CORRECTED METHOD NAME (using 'add') ***
             self._history_manager.add(
                  self.id, HistoryEntry(entry_type="task_start", content=task.to_dict(), task_id=task.task_id)
             )
        except AttributeError:
             logger.error(f"HistoryManager has no 'add' method. Cannot log task_start for agent {self.id[:8]}. Check HistoryManager definition.")
        except Exception as hist_e:
             logger.error(f"Failed to add task_start history entry for agent {self.id[:8]}: {hist_e}", exc_info=True)


        start_time = time.time()
        final_output = None
        try:
            input_data = {"input": task.description}
            if task.input_data: input_data.update(task.input_data)

            logger.debug(f"Invoking AgentExecutor for task {task.task_id[:8]}...")
            result = await self.agent_executor.ainvoke(input_data)
            logger.debug(f"AgentExecutor result for task {task.task_id[:8]}: {result}")

            final_output = result.get("output", "No output field found in result.")
            task.status = "completed"
            task.result = final_output
            task.updated_at = datetime.datetime.utcnow()

            # Add history entry for final answer
            try:
                 # *** CORRECTED METHOD NAME (using 'add') ***
                 self._history_manager.add(
                      self.id, HistoryEntry(entry_type="final_answer", content=final_output, task_id=task.task_id)
                 )
            except AttributeError:
                 logger.error(f"HistoryManager has no 'add' method. Cannot log final_answer for agent {self.id[:8]}.")
            except Exception as hist_e:
                 logger.error(f"Failed to add final_answer history entry for agent {self.id[:8]}: {hist_e}", exc_info=True)

            logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) completed task {task.task_id[:8]}.")

        except Exception as e:
            logger.error(f"Agent '{self.name}' (ID: {self.id[:8]}) failed task {task.task_id[:8]}: {e}", exc_info=True)
            task.status = "failed"
            task.error_message = str(e)
            task.updated_at = datetime.datetime.utcnow()
            # Add history entry for error
            try:
                 # *** CORRECTED METHOD NAME (using 'add') ***
                 self._history_manager.add(
                      self.id, HistoryEntry(entry_type="error", content={"message": str(e), "traceback": traceback.format_exc()}, task_id=task.task_id)
                 )
            except AttributeError:
                 logger.error(f"HistoryManager has no 'add' method. Cannot log error for agent {self.id[:8]}.")
            except Exception as hist_e:
                 logger.error(f"Failed to add error history entry for agent {self.id[:8]}: {hist_e}", exc_info=True)

            # Optionally set agent status to ERROR on task failure
            # self._set_status(AgentStatus.ERROR)

        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Task {task.task_id[:8]} processing took {duration:.2f} seconds.")
            # Emit final task status update signal
            try:
                 signal_emitter.task_status_updated.emit(
                      self.id, task.task_id, task.status,
                      task.result if task.status == "completed" else task.error_message
                 )
            except Exception as sig_e:
                 logger.error(f"Error emitting final task_status_updated signal for task {task.task_id[:8]}: {sig_e}", exc_info=True)

            self.current_task_id = None
            # Persist history after task completion/failure
            try:
                 self._history_manager.save_history(self.id)
            except Exception as save_e:
                 logger.error(f"Failed to save history after task {task.task_id[:8]} for agent {self.id[:8]}: {save_e}", exc_info=True)


    def _run_async_loop(self):
        """Sets up and runs the asyncio event loop in the agent's thread."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) started asyncio event loop.")
            self._loop.run_until_complete(self._async_execute_loop())
        except Exception as e:
            logger.error(f"Agent '{self.name}' (ID: {self.id[:8]}) execution loop crashed: {e}", exc_info=True)
            self._set_status(AgentStatus.ERROR)
        finally:
            logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) closing asyncio event loop.")
            if self._loop and not self._loop.is_closed():
                 try:
                      # Graceful shutdown
                      tasks = asyncio.all_tasks(self._loop)
                      for t in tasks:
                           if not t.done(): t.cancel()
                      self._loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                      self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                 except Exception as shutdown_e:
                      logger.error(f"Error during asyncio loop shutdown for agent {self.id[:8]}: {shutdown_e}", exc_info=True)
                 finally:
                      self._loop.close()
            logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) asyncio event loop closed.")
            if self._on_stop_callback:
                try: self._on_stop_callback(self.id)
                except Exception as cb_e: logger.error(f"Error in on_stop_callback for agent {self.id[:8]}: {cb_e}", exc_info=True)


    async def _async_execute_loop(self):
        """The main asynchronous execution loop for the agent."""
        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) Async loop starting.")
        if self.status not in [AgentStatus.STOPPED, AgentStatus.ERROR]:
             self._set_status(AgentStatus.IDLE)

        while not self._stop_event.is_set():
            task = None
            try:
                task = self._task_queue.get(block=True, timeout=1.0)
                logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) picked up task {task.task_id[:8]}.")

                if task:
                    self._set_status(AgentStatus.RUNNING)
                    await self._process_task(task)
                    self._task_queue.task_done()
                    if not self._stop_event.is_set():
                         self._set_status(AgentStatus.IDLE)
                    else:
                         logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) stop signal handled post-task.")

            except queue.Empty:
                await asyncio.sleep(0.2) # Idle sleep
                continue

            except Exception as loop_err:
                 logger.error(f"Agent '{self.name}' (ID: {self.id[:8]}) error in execution loop: {loop_err}", exc_info=True)
                 self._set_status(AgentStatus.ERROR)
                 await asyncio.sleep(5) # Wait after error

        # --- Loop Exit ---
        final_status = AgentStatus.STOPPED if self.status != AgentStatus.ERROR else AgentStatus.ERROR
        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) Async loop finished. Final status: {final_status.name}.")
        if self.status != final_status:
             self._set_status(final_status)


    def start(self):
        """Starts the agent's execution thread and loop."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"Agent '{self.name}' (ID: {self.id[:8]}) already running.")
            return
        if self.status in [AgentStatus.RUNNING, AgentStatus.STARTING]:
             logger.warning(f"Agent '{self.name}' (ID: {self.id[:8]}) already {self.status.name}.")
             return

        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) starting...")
        self._set_status(AgentStatus.STARTING)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, name=f"Agent-{self.id[:8]}")
        self._thread.daemon = True
        self._thread.start()
        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) thread started.")


    def stop(self, wait: bool = False, timeout: float = 5.0):
        """Signals the agent's execution loop to stop."""
        if self._stop_event.is_set():
             logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) stop already requested.")
             if self.status not in [AgentStatus.STOPPING, AgentStatus.STOPPED]:
                  self._set_status(AgentStatus.STOPPING) # Ensure status reflects intent
             return

        if not self._thread or not self._thread.is_alive():
            logger.warning(f"Agent '{self.name}' (ID: {self.id[:8]}) not running or thread dead.")
            if self.status not in [AgentStatus.ERROR, AgentStatus.STOPPED]:
                 self._set_status(AgentStatus.STOPPED)
            return

        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) requesting stop...")
        self._set_status(AgentStatus.STOPPING)
        self._stop_event.set()

        if wait and self._thread:
            logger.info(f"Waiting up to {timeout}s for agent '{self.name}' (ID: {self.id[:8]}) thread...")
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"Agent '{self.name}' (ID: {self.id[:8]}) thread did not stop within timeout.")
            else:
                logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) thread finished.")
                # Loop finally block should set final status, but confirm here if needed
                if self.status != AgentStatus.ERROR:
                     self._set_status(AgentStatus.STOPPED)

    def cleanup(self):
        """Performs cleanup, ensuring the thread is stopped and joined."""
        logger.info(f"Cleaning up agent '{self.name}' (ID: {self.id[:8]}...).")
        self.stop(wait=True, timeout=10.0)
        self._thread = None
        self._loop = None
        logger.info(f"Agent '{self.name}' (ID: {self.id[:8]}) cleanup complete.")


    def get_history(self) -> List[Dict[str, Any]]:
         """Retrieves the agent's history."""
         # Ensure history manager method exists before calling
         if hasattr(self._history_manager, 'get_history'):
              return self._history_manager.get_history(self.id)
         else:
              logger.error(f"HistoryManager has no 'get_history' method. Cannot retrieve history for agent {self.id[:8]}.")
              return []

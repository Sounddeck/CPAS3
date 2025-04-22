import openai

class ReActAgent:
    def __init__(self, model="gpt-4", temperature=0.7):
        """
        Initialize the ReAct agent with the specified LLM model and parameters.
        """
        self.model = model
        self.temperature = temperature
        self.memory = []  # Persistent memory to track the agent's context and interactions.

    def reason(self, input_text):
        """
        Perform reasoning based on the input text and the current environment.
        """
        prompt = (
            "You are a reasoning and acting agent. Your job is to analyze the input, "
            "reason about the problem, and decide on the best course of action.\n"
            "Memory: " + "\n".join(self.memory) + "\n"
            "Input: " + input_text + "\n"
            "What should be done next?"
        )
        response = self.query_llm(prompt)
        self.update_memory(input_text, response)
        return response

    def act(self, action):
        """
        Simulate acting in the environment. This method can be expanded to execute actual tasks.
        """
        # For now, we just log the action to memory.
        self.memory.append(f"Acted: {action}")
        return f"Action executed: {action}"

    def query_llm(self, prompt):
        """
        Query the LLM with a specific prompt and return the response.
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}],
                temperature=self.temperature,
            )
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Error querying LLM: {str(e)}"

    def update_memory(self, input_text, response):
        """
        Update the agent's memory with the input and response.
        """
        self.memory.append(f"Input: {input_text}")
        self.memory.append(f"Response: {response}")

    def clear_memory(self):
        """
        Clear the agent's memory.
        """
        self.memory = []

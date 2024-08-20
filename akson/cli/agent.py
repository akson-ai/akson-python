from datetime import datetime

from akson import Agent, AgentInput, AgentOutput


class TimeAgent(Agent):

    name = "Time Agent 2"
    description = "Returns the current time"

    def handle_message(self, input: AgentInput) -> AgentOutput:
        now = datetime.now().strftime("%H:%M:%S")
        return AgentOutput(message=now)


agent = TimeAgent()

"""`akson` CLI implementation."""

import os
import uuid

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

import akson

history = FileHistory(os.path.join(os.environ["HOME"], ".akson_history"))
session = PromptSession(history=history)


@click.command()
@click.option("--agent", default="assistant", required=True, help="Agent name")
@click.option("--message", default="", required=False, help="Message to send")
def main(agent, message):
    # Do not run REPL if message is provided on the command line
    if message:
        reply = _send_message(agent, message)
        print(reply)
        return

    # Run REPL
    session_id = uuid.uuid4().hex
    while True:
        try:
            user_input = session.prompt(">>> ")
        except EOFError:
            break

        if user_input in ["exit", "quit"]:
            break

        reply = _send_message(agent, user_input, session_id)
        print(reply)


def _send_message(agent, message, session_id=None):
    try:
        return akson.send_message(agent, message, session_id=session_id)
    except Exception as e:
        if isinstance(e, akson.AksonException):
            raise click.ClickException(e.message)
        raise


if __name__ == "__main__":
    main()

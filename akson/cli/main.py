"""`akson` CLI implementation."""

import os
import uuid
import asyncio
import logging
import importlib

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

import akson

history = FileHistory(os.path.join(os.environ["HOME"], ".akson_history"))
session = PromptSession(history=history)


@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(debug):
    if debug:
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.option("--agent", default="assistant", required=True, help="Agent name")
@click.option("--message", default="", required=False, help="Message to send")
@click.option("--timeout", default=30, required=False, help="Timeout in seconds")
def chat(agent, message, timeout):
    # Do not run REPL if message is provided on the command line
    if message:
        reply = _send_message(agent, message, timeout=timeout)
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

        reply = _send_message(agent, user_input, session_id=session_id, timeout=timeout)
        print(reply)


@cli.command()
@click.argument("module", required=True, default="agent")
def run(module: str):
    if module.endswith(".py"):
        module = module[:-3]
    module = module.replace("/", ".")
    m = importlib.import_module(module)
    m.agent.run()


def _send_message(agent, message, *, session_id=None, timeout=None):
    try:
        coro = akson.send_message(agent, message, session_id=session_id, timeout=timeout)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except Exception as e:
        if isinstance(e, akson.AksonException):
            raise click.ClickException(e.message)
        raise


if __name__ == "__main__":
    cli()

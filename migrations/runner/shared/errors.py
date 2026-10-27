"""The error that stops a command."""


class Abort(Exception):
    """Stops the command: its message is printed and the command exits non-zero."""

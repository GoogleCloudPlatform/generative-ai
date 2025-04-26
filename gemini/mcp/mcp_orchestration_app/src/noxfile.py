import nox
from nox.sessions import Session


@nox.session
def lint(session: Session) -> None:
    """Run linters."""
    session.install("flake8")
    session.run("flake8", ".")


@nox.session
def format(session: Session) -> None:
    """Run code formatter."""
    session.install("black")
    session.run("black", ".")

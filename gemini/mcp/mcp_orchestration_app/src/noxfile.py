import nox


@nox.session
def lint(session):
    """Run linters."""
    session.install("flake8")
    session.run("flake8", ".")


@nox.session
def format(session):
    """Run code formatter."""
    session.install("black")
    session.run("black", ".")

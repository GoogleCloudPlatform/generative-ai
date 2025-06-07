# noxfile.py
import nox


@nox.session
def format(session):
    session.install("black")
    session.run("black", ".")

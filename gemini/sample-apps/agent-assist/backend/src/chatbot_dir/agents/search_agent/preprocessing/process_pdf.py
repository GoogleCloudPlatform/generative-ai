"""This is a python utility file."""

# pylint: disable=E0401

from preprocessing.make_chunks import make_chunks
from preprocessing.make_embeddings import make_embeddings


def process_pdf(document_path: str, policy_name: str):
    """Processes a PDF document for use in the chatbot.

    Args:
        document_path (str): The path to the PDF document.
        policy_name (str): The name of the policy associated with the document.

    Returns:
        None
    """

    make_chunks(document_path, policy_name)
    make_embeddings(policy_name)


if __name__ == "__main__":
    DOC1 = "data/static/documents/Home_Insurance_bharat-griha-raksha-plus-pw.pdf"
    DOC2 = "data/static/documents/Home_Insurance_ma-home-insurance-premium-pw.pdf"
    DOC3 = "data/static/documents/Home_Insurance_micro-insurance---home-insurance.pdf"
    DOC4 = "data/static/documents/Home_Insurance_policy-wording-home-shield.pdf"
    POL1 = "Bharat Griha Raksha Plus"
    POL2 = "My Asset Home Insurance"
    POL3 = "Micro Insurance - Home Insurance"
    POL4 = "Home Shield"
    process_pdf(DOC1, POL1)
    process_pdf(DOC2, POL2)
    process_pdf(DOC3, POL3)
    process_pdf(DOC4, POL4)

# Document AI and Gemini for Entity Extraction
This repository showcases the power of combining Google Cloud's Document AI and Gemini for advanced entity extraction from documents. It provides two distinct approaches:

## 1. Event-Triggered Cloud Function Pipeline
The cf-trigger-event directory contains a Cloud Function that automatically processes documents uploaded to a Cloud Storage bucket. This pipeline offers a scalable and efficient solution for real-time entity extraction.

**Key Features:**

- Automated Processing: Triggered by document uploads to Cloud Storage, eliminating manual intervention.
- Document AI Integration: Extracts structured data from various document types using Google's powerful OCR and ML models.
- Gemini Enhancement: Leverages Gemini's natural language understanding to further process and analyze extracted data.
- Cloud-Native Architecture: Built on Cloud Functions, Cloud Storage, and Pub/Sub for scalability and reliability.
  
**Learn More:** See the [cf-trigger-event/README.md](./cf-trigger-event/README.md) for detailed setup and deployment instructions.

## 2. Comparative Script for Document AI and Gemini
The scripts directory contains a Python script that demonstrates and compares entity extraction using both Document AI and Gemini independently. This approach provides insights into the strengths of each API.

Key Features:

- Side-by-Side Comparison: Analyzes and compares the results of entity extraction performed by Document AI and Gemini.
- Document AI Expertise: Showcases Document AI's ability to extract structured data from PDFs using predefined schemas.
- Gemini's NLP Prowess: Highlights Gemini's capability to extract entities from unstructured text with nuanced understanding.
- Customizable Code: Provides a foundation for adapting and extending the script to specific document types and entity extraction needs.
  
**Learn More:** Explore the [scripts/README.md](./scripts/README.md) for a deeper dive into the code, setup instructions, and insights into the comparison results.

# Getting Started
- Choose Your Approach: Decide whether you need an automated pipeline (cf-trigger-event) or a comparative analysis script (scripts).
- Explore the Documentation: Refer to the respective README files within each directory for detailed instructions and code examples.
- This repository assumes, that this [codelab](https://www.cloudskillsboost.google/focuses/67855?parent=catalog) has been completed, that a dataset with the test documents is available and there exists a Document AI extractor.

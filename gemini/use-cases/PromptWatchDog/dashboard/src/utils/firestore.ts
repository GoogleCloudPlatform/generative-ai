import { Firestore } from '@google-cloud/firestore';

// Initialize Firestore with specific database ID "watchdog-prompts"
// We assume Google Cloud credentials are available via environment (GCP_PROJECT) or ADC.
const firestore = new Firestore({
    projectId: process.env.GCP_PROJECT,
    databaseId: 'watchdog-prompts',
});

export { firestore };

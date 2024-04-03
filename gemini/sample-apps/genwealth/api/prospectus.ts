import { Storage } from '@google-cloud/storage';
import { SearchServiceClient, DocumentServiceClient, protos } from '@google-cloud/discoveryengine';
import { v4 as uuidv4 } from 'uuid';
import { Database } from './database';

/** 
 */
export class Prospectus {
    private readonly storageClient: Storage;
    private readonly searchClient: SearchServiceClient;
    private readonly bucketName: string;
    private readonly metadataBucketName: string;

    constructor(private db: Database) { 
        this.storageClient = new Storage();
        this.searchClient = new SearchServiceClient();

        this.bucketName = process.env['PROSPECTUS_BUCKET'] ?? '';
        if (this.bucketName === '')
            throw new Error("PROSPECTUS_BUCKET environment variable not set");
       
        this.metadataBucketName = this.bucketName + "-metadata";
    }

    /** Upload a prospectus and generate the metadata for indexing in Vertex Search & Conversation.
     */
    async upload(buffer: Buffer, filename: string, ticker: string) {
        ticker = ticker.toUpperCase();

        const prospectusBlob = this.storageClient.bucket(this.bucketName).file(filename);
        await prospectusBlob.save(buffer);

        const metadata = this.getMetadata(prospectusBlob.cloudStorageURI.href, ticker);
        const metadataBlob = this.storageClient.bucket(this.metadataBucketName).file(`${ticker}.jsonl`);
        await metadataBlob.save(JSON.stringify(metadata));

        console.log(`Uploaded ${filename} to ${this.bucketName}`);

        this.importDocument(metadataBlob.cloudStorageURI.href);
    }

    async search(query: string, ticker: string) {
        ticker = ticker.toUpperCase();

        const request = {
            pageSize: 5,
            query: query,
            contentSearchSpec: {
                summarySpec: {
                    summaryResultCount: 5,
                    ignoreAdversarialQuery: true,
                    includeCitations: false,
                    modelSpec: {
                        version: 'preview',
                        },                    
                },
                snippetSpec: {
                    returnSnippet: false
                },
                extractiveContentSpec: {
                    maxExtractiveAnswerCount: 1
                }
            },
            filter: `ticker: ANY(\"${ticker}\")`,
            servingConfig: await this.getParent(),
        };
            
        // Perform search request
        const response = await this.searchClient.search(request, {
            autoPaginate: false,
        });

        const summaryObject = response[2].summary;
        const summary: string = summaryObject?.summaryText ?? '';
        console.log(summary);
        
        return summary;
    }

    async getTickers(): Promise<string[]> {
        const query = 'SELECT DISTINCT(ticker) FROM langchain_vector_store';

        try
        {
            const rows = await this.db.query(query);
            return rows.map((row) => row.ticker);
        }
        catch (error)
        {
            throw new Error(`getTickers errored with query: ${query}.\nError: ${(error as Error)?.message}`);
        }
    }


    private getMetadata(gcsPath: string, ticker: string) {
        return {
            id: uuidv4(),
            structData: { ticker: ticker },
            content: { mimeType: "application/pdf", uri: gcsPath }
        };
    }

    private async importDocument(gsUri: string) {
        const docsClient = new DocumentServiceClient();

        const importMode = protos.google.cloud.discoveryengine.v1.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL

        const projectId = process.env['PROJECT_ID'] ?? await this.searchClient.getProjectId();

        const dataStoreId = process.env['DATASTORE_ID'];
        if (!dataStoreId) {
            throw new Error('DATASTORE_ID environment variable not set');
        }

        const parent = `projects/${projectId}/locations/global/dataStores/${dataStoreId}/branches/default_branch`;

        const request = {
            parent: parent,
            gcsSource: {
                dataSchema: "document",
                inputUris: [gsUri]
            },
            reconciliationMode: importMode
        };

        await docsClient.importDocuments(request);
        console.log('imported', gsUri);
    }

    private async getParent() {
        const projectId = process.env['PROJECT_ID'] ?? await this.searchClient.getProjectId();

        console.log('search using project id', projectId );

        const dataStoreId = process.env['DATASTORE_ID'];
        if (!dataStoreId) {
            throw new Error('DATASTORE_ID environment variable not set');
        }

        const searchServingConfig = this.searchClient.projectLocationCollectionDataStoreServingConfigPath(
            projectId,
            "global",
            "default_collection",
            dataStoreId,
            "default_search"
        );
        
        return searchServingConfig;
    }
}

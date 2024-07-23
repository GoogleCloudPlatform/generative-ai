import { Database } from "./database";
import { VertexAI } from "@google-cloud/vertexai";

/** Use retrieval augmented search of Prospectus using AlloyDB embeddings & Gemini Pro.
 */
export class ProspectusRag {

    constructor(private readonly db: Database) {}

    async search(userPrompt: string, ticker: string) {
        const context = await this.getContext(userPrompt, ticker);
        const response = await this.generateContent(userPrompt, context.join('\n'));
        return response;
    };

    private async getContext(prompt: string, ticker: string): Promise<string[]> {
        const query = `SELECT content,
                embedding <=> google_ml.embedding('textembedding-gecko@003', '${prompt}')::vector AS distance
            FROM langchain_vector_store
            WHERE ticker='${ticker}'
            ORDER BY distance
            LIMIT 5`;

        try
        {
            const rows = await this.db.query(query);

            if (rows.length == 0)
                throw new Error(`No data for ticker: ${ticker}`);

            return rows.map((row: { content: any; }) => row.content);
        }
        catch (error)
        {
            throw new Error(`getContext errored with query: ${query}.\nError: ${(error as Error)?.message}`);
        }
    }

    private async generateContent(userPrompt: string, context: string) {
        const aiRole = 'AI ROLE: You are an experienced financial analyst. \nUSER ROLE: I am an employee of GenWealth, an Investment Advisory Firm serving clients in North America. \n\nINSTRUCTIONS: \n- Respond to the PROMPT using FEWER than 4000 characters, including white space. The PROMPT begins with "<PROMPT>" and ends with "</PROMPT>". \n- Use as many details as possible from the provided CONTEXT to improve your response. The context begins with "<CONTEXT>" and ends with "</CONTEXT>". \n- Respond with a 1-2 sentence summary, followed by bullet points with specific details. \n- Do not use programming markup or tags in your response. \n- If you cannot answer the question based on the provided context, do not make up an answer. Instead, simply respond by saying, "The provided context does not contain enough relevant information to answer the question."';
        const prompt = `${aiRole}\n\nAnswer truthfully and only if you can find the answer for the following question in the context provided. \n\n<CONTEXT>${context}\n</CONTEXT>\n\n<PROMPT>${userPrompt}</PROMPT>`;

        const projectId = this.getProjectId();
        const region = process.env['REGION'];
        
        if (!region) throw new Error('Missing REGION env variable.');

        // Initialize Vertex AI with your Cloud project and location       
        const vertex_ai = new VertexAI({project: projectId, location: region});
        const model = process.env['RAG_MODEL'] ?? 'gemini-1.0-pro-001';
    
        // Instantiate the models
        const generativeModel = vertex_ai.preview.getGenerativeModel({
            model: model,
            generationConfig: {
                "maxOutputTokens": 2048,
                "temperature": 0.5,
                "topP": 1,
            },
        });
        
        const request = {
            contents: [ {role: 'user', parts: [{text: prompt}]} ]
        };

        const streamingResp = await generativeModel.generateContentStream(request);

        const text = (await streamingResp.response).candidates![0].content.parts[0].text;

        var response = {query: prompt, data: [text]};

        console.log('response', text);

        return response;
    };

    private getProjectId(): string {
        let projectId = process.env['PROJECT_ID'];

        console.log('using projectid', projectId);

        if (!projectId)
            throw new Error("Unable to load project id from PROJECT_ID env variable or Google Cloud metadata");

        return projectId;
    }
}

import { Database, camelCaseRows, safeString } from './database';

export class Investments {
    constructor(private db: Database) { }

    async search(searchTerms: string[]) {
        console.log('using searchTerms', searchTerms);

        // If no search terms are provided, return an empty result set
        if (!Array.isArray(searchTerms) || searchTerms.length === 0) {
            const emptyResult = { data: [], query: '' };
            return emptyResult;
        }

        let query = `SELECT ticker, etf, rating, analysis
            FROM investments
            WHERE analysis LIKE '%${safeString(searchTerms[0]) ?? ''}%'`;
        
        for (let i = 1; i < searchTerms.length; i++) {
            const term = searchTerms[i];
            if (typeof term === 'string' && term.trim() !== '') {
                query += `
                    AND analysis LIKE '%${safeString(term).trim()}%'`;
            }
        }
        
        query += ` 
            LIMIT 5;`

        const rows = await this.db.query(query);
        return { data: camelCaseRows(rows), query: query };
    }

    async semanticSearch(prompt: string) {
        const query = `SELECT ticker, etf, rating, analysis, 
            analysis_embedding <=> google_ml.embedding('text-embedding-005', '${safeString(prompt)}')::vector AS distance
            FROM investments
            ORDER BY distance
            LIMIT 5;`;

        try
        {
            const rows = await this.db.query(query);
            return { data: camelCaseRows(rows), query: query };
        }
        catch (error)
        {
            throw new Error(`semanticSearch errored with query: ${query}.\nError: ${(error as Error)?.message}`);
        }
    }
}

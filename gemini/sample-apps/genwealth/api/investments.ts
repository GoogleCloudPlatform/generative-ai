import { Database, camelCaseRows, safeString } from './database';

export class Investments {
    constructor(private db: Database) { }

    async search(searchTerms: string[]) {
        console.log('using searchTerms', searchTerms);
        let query = `SELECT ticker, etf, rating, analysis
            FROM investments
            WHERE analysis LIKE '%${safeString(searchTerms[0]) ?? ''}%'`;
        
        for (let i = 1; i < searchTerms.length; i++) {
            if (searchTerms[i].trim() !== '') {
                query += `
                    AND analysis LIKE '%${safeString(searchTerms[i]).trim()}%'`;
            }
        }
        
        query += ` 
            LIMIT 5;`

        const rows = await this.db.query(query);
        return { data: camelCaseRows(rows), query: query };
    }

    async semanticSearch(prompt: string) {
        const query = `SELECT ticker, etf, rating, analysis, 
            analysis_embedding <=> embedding('textembedding-gecko@003', '${safeString(prompt)}') AS distance
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

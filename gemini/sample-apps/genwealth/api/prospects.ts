import { Database, camelCaseRows, safeString } from './database';

export class Prospects {
    constructor(private db: Database) { }


    async semanticSearch(prompt: string, riskProfile?: string, minAge?: number, maxAge?: number) {
        let query = `SELECT id, first_name, last_name, email, age, risk_profile, bio,
            bio_embedding <=> embedding('textembedding-gecko@003', '${safeString(prompt)}') AS distance
            FROM user_profiles`;

        let filters = this.getFilters(riskProfile, minAge, maxAge);
        query += filters += ` ORDER BY distance LIMIT 50;`;

        const rows = await this.db.query(query);
        return { data: camelCaseRows(rows), query: query };
    }

    private getFilters(riskProfile?: string, minAge?: number, maxAge?: number) {
        let filter: string;

        if (riskProfile || minAge || maxAge) {
            filter = ` WHERE `;

            if (riskProfile) {
                filter += `risk_profile = '${riskProfile}'`;
            }

            if (minAge) {

                if (riskProfile) {
                    filter += ` AND `;
                }
                filter += ` age >= ${minAge}`;
            }

            if (maxAge) {

                if (riskProfile || minAge) {
                    filter += ` AND `;
                }
                filter += ` age <= ${maxAge}`;
            }
        }
        else {
            filter = ``;
        }

        return filter;
    }
}

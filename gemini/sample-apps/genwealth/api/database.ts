import { Pool } from 'pg'
import * as _ from 'lodash';

/**
 * Required ENV variables to be set:

    PGPORT=5432
    PGDATABASE=ragdemos
    PGUSER=postgres
    PGHOST=
    PGPASSWORD=
 */

/**
 * Converts SQL field names from snake_case to camelCase.
 * 
 * @param rows Rows from a database query
 * @returns 
 */
export const camelCaseRows = (rows: any[]) => _.map(rows, (row) => 
  _.mapKeys(row, (value, key) => _.camelCase(key)));

/**
 * Escapes single quotes in a string.
 * 
 * @param str String to be escaped
 * @returns escaped string
 */
export const safeString = (str: string) => str?.replace(/'/g, "''") ?? '';


export class Database {
  private pool: Pool;

  constructor() {
    if (!process.env['PGHOST']) {
      throw new Error(`Missing required environment variable: 'PGHOST'`);
    }
    this.pool = new Pool()

    // the pool will emit an error on behalf of any idle clients
    // it contains if a backend error or network partition happens
    this.pool.on('error', (err, client) => {
      console.error('Unexpected error on idle client', err);
      throw err;
    })
  }

  async query(query: string) {
    const client = await this.pool.connect()
    const res = await client.query(query)
    client.release()
    return res.rows;
  }

  async end() {
    await this.pool.end()
  }
}

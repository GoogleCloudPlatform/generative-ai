import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { join } from 'path';

import { Database } from './database';
import { Investments } from './investments';
import { Prospects } from './prospects';
import { Chatbot, ChatRequest } from './chatbot';
import { Prospectus } from './prospectus';
import { ProspectusRag } from './prospectus-rag';

//
// Create the express app
//
const app: express.Application = express();
const upload = multer();
const db: Database = new Database();
const investments = new Investments(db);
const prospects = new Prospects(db);
const prospectus = new Prospectus(db);
const prospectusRag = new ProspectusRag(db);
const chatbot = new Chatbot(db);
const staticPath = join(__dirname, 'ui/dist/genwealth-advisor-ui/browser');

//
// Use middleware
//
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(staticPath));

//
// Setup routes
//

/** Find investments by search terms, 
 *  i.e. /investments/search?terms=technology,high%20risk  */
app.get('/api/investments/search', async (req: express.Request, res: express.Response) => {
  try 
  {
    const terms: string[] = req.query.terms as string[];

    const response = await investments.search(terms);
    res.json(response);
  }
  catch (err)
  {
    console.error('error occurred:', err);
    res.status(500).send(err);
  }
});

/** Find investments with naturual language prompts 
 *  i.e. /investments/semantic_search?prompt=hedge%20against%20%high%20inflation */
app.get('/api/investments/semantic-search', async (req: express.Request, res: express.Response) => {
  try
  {
    const prompt: string = req.query.prompt as string;

    const response = await investments.semanticSearch(prompt);
    res.json(response);
  }
    catch (err)
    {
      console.error('error occurred:', err);
      res.status(500).send(err);
    }    
});

/** Find prospects with naturual language prompt and optional filters
 *  i.e. /prospects/search?prompt=young%20aggressive%20investor&risk_profile=low&min_age=25&max_age=40 */ 
 app.get('/api/prospects/search', async (req: express.Request, res: express.Response) => {
  try
  {
    const prompt: string = req.query.prompt as string;
    const riskProfile: string | undefined = req.query.risk_profile as string;
    const minAge: number | undefined = req.query.min_age ? Number(req.query.min_age) : undefined;
    const maxAge: number | undefined = req.query.max_age ? Number(req.query.max_age) : undefined;

    const response = await prospects.semanticSearch(prompt, riskProfile, minAge, maxAge);
    res.json(response);
  }
  catch (err)
  {
    console.error('error occurred:', err);
    res.status(500).send(err);
  }        
});

/** Chat with a financial advisor, 
 */
app.post('/api/chat', async (req: express.Request, res: express.Response) => {
  try
  {  
    const chatRequest: ChatRequest = req.body;

    const data = await chatbot.chat(chatRequest);
    res.json(data);
  }
  catch (err)
  {
    console.error('error occurred:', err);
    res.status(500).send(err);
  }      
});

/** Upload prospectus files.
 */
app.post('/api/prospectus/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      console.log('No file received.');
      return res.status(400).send('No file received.');
    }

    // Get the file from the request
    const file = req.file;
    const ticker = req.body.ticker;

    console.log('Uploading file:', file.originalname, ticker);

    // Upload
    await prospectus.upload(file.buffer, file.originalname, ticker);

    res.status(200).send();
  }
  catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
});

app.get('/api/prospectus/search', async (req, res) => {
  try {
    const ticker = req.query.ticker as string;
    const query = req.query.query as string;
    const response = await prospectus.search(query, ticker);
    res.json(response);
  }
  catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
});

app.get('/api/prospectus/rag-search', async (req, res) => {
  try {
    const ticker = req.query.ticker as string;
    const query = req.query.query as string;
    const response = await prospectusRag.search(query, ticker);
    res.json(response);
  }
  catch (err) {
    console.error(err);
    const message = (err as Error)?.message ?? err;
    res.status(500).send(message);
  }
});

app.get('/api/prospectus/tickers', async (req, res) => {
  try {
    const response = await prospectus.getTickers();
    res.json(response);
  }
  catch (err) {
    console.error(err);
    res.status(500).send(err);
  }
});

/** Send any other request just to the static content
*/
app.get('*', (req, res) => {
  res.sendFile(join(staticPath, 'index.html'));
});

//
// Start the server
//
const port: number = parseInt(process.env.PORT ?? '8080');

app.listen(port, () => {
  console.log(`GenWealth Advisor API: listening on port ${port}`);
});

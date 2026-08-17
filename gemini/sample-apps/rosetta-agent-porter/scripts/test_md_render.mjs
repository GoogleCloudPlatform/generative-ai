// Extracts the REAL markdown renderer from frontend/index.html and runs the two
// chat samples from the bug report through it, asserting proper HTML (headings,
// lists, bold, hr, code) and NO leftover raw markdown. Run: node scripts/test_md_render.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const html = fs.readFileSync(path.join(root, 'frontend', 'index.html'), 'utf8');

// pull the real esc + mdInline + renderMarkdown definitions out of the file
const escM = html.match(/const esc = \(t\)=>[\s\S]*?;\n/);
const mdM = html.match(/\/\* --- inline markdown[\s\S]*?function renderAnswer\(t\)\{ return renderMarkdown\(t\); \}/);
// includes jsonEnd/prettifyJson* + mdInline + renderMarkdown + renderAnswer
if (!escM || !mdM) { console.error('FAIL: could not extract renderer from index.html'); process.exit(1); }

const factory = new Function(`${escM[0]}\n${mdM[0]}\nreturn { esc, mdInline, renderMarkdown, renderAnswer };`);
const { renderAnswer } = factory();

let failures = 0;
function check(name, cond) {
  if (cond) { console.log('  ok  ' + name); } else { console.log('  XX  ' + name); failures++; }
}

// ---- Sample A: image 1 (headings + bulleted list + bold + hr) ----
const A = [
  'As a **Lead Market Analyst**, I specialize in dissecting online business landscapes.',
  '',
  'Here is how I can assist you:',
  '',
  '---',
  '',
  '### 1. Target Audience & Customer Profiling',
  '* **Demographics & Psychographics:** Identify age, location, income level.',
  '* **Pain Points & Preferences:** Pinpoint customer needs, buying triggers.',
  '',
  '### 2. Deep Competitor Intelligence',
  '* **Competitor Identification:** Uncover top direct and indirect competitors.',
].join('\n');
const a = renderAnswer(A);
console.log('\n[Sample A]');
check('heading rendered as md-h (not raw ###)', a.includes('<div class="md-h md-h3">') && a.includes('Target Audience'));
check('no literal ### remains', !a.includes('###'));
check('unordered list rendered', a.includes('<ul class="md-ul">') && a.includes('<li>'));
check('no list item starts with raw "* "', !/<li>\s*\*\s/.test(a));
check('bold rendered', a.includes('<b>Lead Market Analyst</b>') && a.includes('<b>Demographics &amp; Psychographics:</b>'));
check('hr rendered', a.includes('<hr class="md-hr">'));
check('ampersand safely escaped', a.includes('Target Audience &amp; Customer Profiling'));

// ---- Sample B: image 2 (ordered list + JSON blob doesn't crash) ----
const B = [
  '### Ready to get started?',
  'Tell me a bit about your project:',
  '1. **What is your product or service?**',
  '2. **Who is your ideal target audience?**',
  '3. **What is your main goal right now?**',
  '',
  '{"name":"Comprehensive Full-Funnel Growth","channels":"Paid Search, SEO"}',
].join('\n');
const b = renderAnswer(B);
console.log('\n[Sample B]');
check('ordered list rendered', b.includes('<ol class="md-ol">') && b.includes('<li>'));
check('bold inside list item', b.includes('<b>What is your product or service?</b>'));
check('no literal 1. remains as text start', !/<li>\s*1\.\s/.test(b));
check('trailing JSON object rendered as a code block', b.includes('<pre class="md-pre">') && b.includes('Comprehensive Full-Funnel Growth'));

// ---- Safety: no script injection, only http links ----
console.log('\n[Safety]');
const x = renderAnswer('hi <img src=x onerror=alert(1)> [ok](javascript:alert(1)) [good](https://example.com)');
check('raw HTML escaped (no live <img>)', !x.includes('<img') && x.includes('&lt;img'));
check('javascript: link NOT turned into anchor', !/href="javascript:/.test(x));
check('http link IS turned into safe anchor', x.includes('<a href="https://example.com"') && x.includes('rel="noopener noreferrer"'));
const code = renderAnswer('use `**not bold**` here');
check('bold inside inline code is NOT applied', code.includes('<code class="md-code">**not bold**</code>'));

// ---- output_schema JSON dump: raw JSON becomes a pretty ```json code block ----
console.log('\n[Structured JSON output — the reported bug]');
// prose from a no-schema agent, immediately followed by two output_schema JSON dumps
const strategy = JSON.stringify({name:'Full-Funnel Growth', tactics:'TOFU/MOFU/BOFU', channels:['Meta Ads','SEO'], KPIs:['CAC','ROAS','LTV']});
const copy  = JSON.stringify({campaign_name:'Wear Return Repeat', ideas:[{title:'Footprint Unmasked', description:'short-form video series', audience:'Gen Z', channel:'TikTok', expected_impact:'builds trust'}], headline:'Turn Old Kicks Into VIP', body:'Send us any worn-out pair.', call_to_action:'Join now'});
const mixed = 'As a **Lead Market Analyst**, here is the plan.\n\n### Strategy\n* channel focus\n' + strategy + copy;
const r = renderAnswer(mixed);
check('prose still renders (heading + bold + list)', r.includes('<div class="md-h md-h3">') && r.includes('<b>Lead Market Analyst</b>') && r.includes('<ul class="md-ul">'));
check('first JSON object rendered as a <pre> code block', (r.match(/<pre class="md-pre">/g)||[]).length >= 2);
check('JSON is pretty-printed (indented, multi-line)', r.includes('&quot;channels&quot;') && r.includes('\n  &quot;'));
check('no raw one-line JSON leaks into a paragraph', !/<p class="md-p">[^<]*\{&quot;name&quot;/.test(r));
check('array values preserved inside the block', r.includes('Meta Ads') && r.includes('ROAS'));
// already-fenced JSON must not be double-wrapped
const fenced = renderAnswer('```json\n{"a":1,"b":2,"c":3,"d":4,"e":5}\n```');
check('pre-fenced JSON not double-processed', (fenced.match(/<pre class="md-pre">/g)||[]).length === 1);
// invalid JSON (unquoted keys) is left as prose, not crashed
const not_json = renderAnswer('config looks like {name: value, x: y} in pseudo-code');
check('invalid JSON left as text (no crash, no code block)', !not_json.includes('<pre class="md-pre">') && not_json.includes('pseudo-code'));

console.log('\n' + (failures ? `FAILED (${failures})` : 'ALL PASSED'));
process.exit(failures ? 1 : 0);

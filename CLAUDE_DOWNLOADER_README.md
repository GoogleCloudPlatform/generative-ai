# Claude.ai Conversation Downloader

A Python script to download Claude.ai conversation links and save them as text files.

## Features

- **Browser Automation**: Uses Playwright to access authenticated Claude.ai conversations
- **Batch Download**: Download multiple conversations from a list of URLs
- **Manual Mode**: Simple copy-paste interface for quick downloads
- **Clean Output**: Saves conversations as formatted text files with metadata

## Installation

### 1. Install Python Dependencies

```bash
pip install -r download_claude_links_requirements.txt
```

### 2. Install Playwright Browser

```bash
playwright install chromium
```

## Usage

### Quick Start - Manual Mode (Easiest)

The simplest way to download a conversation without authentication hassle:

```bash
python download_claude_links.py --manual
```

Then:
1. Open your Claude.ai conversation in a browser
2. Select all (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C)
3. Paste into the terminal
4. Press Ctrl+D (Unix/Mac) or Ctrl+Z then Enter (Windows) to finish

### Download Single Conversation

```bash
python download_claude_links.py https://claude.ai/chat/abc123-def456-ghi789
```

The browser will open automatically. If you're not logged in:
1. Log in to Claude.ai in the browser window
2. Press Enter in the terminal to continue
3. The script will download the conversation

### Download Multiple Conversations

Create a text file (e.g., `urls.txt`) with one URL per line:

```
https://claude.ai/chat/conversation-id-1
https://claude.ai/chat/conversation-id-2
https://claude.ai/chat/conversation-id-3
```

Then run:

```bash
python download_claude_links.py --file urls.txt
```

### Specify Output Directory

```bash
python download_claude_links.py --output my_conversations https://claude.ai/chat/abc123
```

## Command-Line Options

```
positional arguments:
  urls                  Claude.ai conversation URLs to download

optional arguments:
  -h, --help            show help message and exit
  --file FILE, -f FILE  File containing list of URLs (one per line)
  --output DIR, -o DIR  Output directory for saved conversations
                        (default: claude_conversations)
  --manual, -m          Manual mode: paste conversation content directly
```

## Output Format

Each conversation is saved as a text file with:
- Filename: `claude_chat_{conversation_id}_{timestamp}.txt` or custom title
- Header with source URL and download timestamp
- Full conversation content

Example output structure:
```
claude_conversations/
├── claude_chat_abc123_20240116_143022.txt
├── claude_chat_def456_20240116_143125.txt
└── my_custom_title_20240116_143230.txt
```

## Tips

1. **For Best Results**: Use manual mode (`--manual`) if you're having authentication issues
2. **Multiple Downloads**: The script adds a 2-second delay between downloads to be respectful to the service
3. **Browser Window**: Don't close the browser window while the download is in progress
4. **Large Conversations**: May take a few seconds to fully load before content is extracted

## Troubleshooting

### "Playwright not installed" Error

```bash
pip install playwright
playwright install chromium
```

### Authentication Issues

If the automated browser login isn't working:
1. Use `--manual` mode instead
2. Or keep the browser window open and manually log in when prompted

### Content Not Downloading

- Wait a few extra seconds after the page loads
- Ensure you're logged in to Claude.ai
- Check that the URL is correct and the conversation exists

## Examples

### Example 1: Quick download of one conversation
```bash
python download_claude_links.py https://claude.ai/chat/abc123-def456
```

### Example 2: Batch download with custom output directory
```bash
python download_claude_links.py --file my_urls.txt --output backup/claude_chats
```

### Example 3: Manual mode for quick copy-paste
```bash
python download_claude_links.py --manual
# Then paste your conversation content
```

## Notes

- This script requires authentication to Claude.ai
- Downloaded content is for personal use only
- The script respects Claude.ai's terms of service by using normal browser automation
- Content is saved locally as plain text files

## License

This script is provided as-is for personal use.

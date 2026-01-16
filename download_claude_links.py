#!/usr/bin/env python3
"""
Script to download Claude.ai conversation links to text files.

This script provides multiple methods to download Claude.ai conversations:
1. Using browser automation with Playwright (recommended for authenticated access)
2. Manual copy-paste mode for simple use cases

Usage:
    # Install dependencies first:
    pip install playwright beautifulsoup4
    playwright install chromium

    # Download single conversation:
    python download_claude_links.py https://claude.ai/chat/[conversation-id]

    # Download multiple conversations from a file:
    python download_claude_links.py --file urls.txt

    # Manual mode (copy-paste content):
    python download_claude_links.py --manual

Requirements:
    - playwright
    - beautifulsoup4
"""

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not installed. Install with: pip install playwright && playwright install chromium")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: BeautifulSoup not installed. Install with: pip install beautifulsoup4")


class ClaudeDownloader:
    """Download Claude.ai conversations to text files."""

    def __init__(self, output_dir: str = "claude_conversations"):
        """Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded conversations
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """Sanitize text for use as filename.

        Args:
            text: Text to sanitize
            max_length: Maximum length for filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        text = re.sub(r'[<>:"/\\|?*]', '_', text)
        text = re.sub(r'\s+', '_', text)
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        return text.strip('_')

    def extract_conversation_id(self, url: str) -> Optional[str]:
        """Extract conversation ID from Claude.ai URL.

        Args:
            url: Claude.ai conversation URL

        Returns:
            Conversation ID or None if not found
        """
        match = re.search(r'claude\.ai/chat/([a-f0-9\-]+)', url)
        return match.group(1) if match else None

    async def download_with_playwright(self, url: str, email: Optional[str] = None) -> Optional[str]:
        """Download conversation using Playwright browser automation.

        Args:
            url: Claude.ai conversation URL
            email: Optional email for login (will prompt for manual login if not provided)

        Returns:
            Conversation text content or None if failed
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("Error: Playwright is not installed. Install with: pip install playwright && playwright install chromium")
            return None

        async with async_playwright() as p:
            # Launch browser in headful mode for authentication
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                print(f"Opening {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Wait a bit for initial load
                await asyncio.sleep(3)

                # Check if login is required
                if "login" in page.url or "auth" in page.url:
                    print("\n" + "="*60)
                    print("AUTHENTICATION REQUIRED")
                    print("="*60)
                    print("Please log in to Claude.ai in the browser window.")
                    print("After logging in and seeing your conversation, press Enter here...")
                    print("="*60 + "\n")
                    input()

                    # Navigate to the conversation URL again after login
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(3)

                # Wait for conversation content to load
                print("Waiting for conversation to load...")
                await asyncio.sleep(5)

                # Extract conversation content
                # Claude.ai uses dynamic content, so we'll get the full page text
                content = await page.content()

                if BS4_AVAILABLE:
                    soup = BeautifulSoup(content, 'html.parser')

                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "header", "footer"]):
                        script.decompose()

                    # Get text
                    text = soup.get_text()

                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                else:
                    # Fallback: just get text content
                    text = await page.inner_text('body')

                print(f"Downloaded {len(text)} characters")
                return text

            except Exception as e:
                print(f"Error downloading conversation: {e}")
                return None
            finally:
                await browser.close()

    def save_conversation(self, content: str, url: str, title: Optional[str] = None) -> str:
        """Save conversation content to a text file.

        Args:
            content: Conversation text content
            url: Original conversation URL
            title: Optional title for the conversation

        Returns:
            Path to saved file
        """
        conversation_id = self.extract_conversation_id(url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if title:
            filename = f"{self.sanitize_filename(title)}_{timestamp}.txt"
        elif conversation_id:
            filename = f"claude_chat_{conversation_id}_{timestamp}.txt"
        else:
            filename = f"claude_conversation_{timestamp}.txt"

        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Source URL: {url}\n")
            f.write(f"Downloaded: {datetime.now().isoformat()}\n")
            f.write("="*80 + "\n\n")
            f.write(content)

        print(f"Saved to: {filepath}")
        return str(filepath)

    def manual_mode(self):
        """Manual mode: prompt user to paste conversation content."""
        print("\n" + "="*80)
        print("MANUAL MODE")
        print("="*80)
        print("1. Open your Claude.ai conversation in a browser")
        print("2. Select all text (Ctrl+A / Cmd+A)")
        print("3. Copy to clipboard (Ctrl+C / Cmd+C)")
        print("4. Paste below and press Ctrl+D (Unix) or Ctrl+Z (Windows) when done")
        print("="*80 + "\n")

        print("Paste conversation content (press Ctrl+D or Ctrl+Z when done):")
        try:
            content = sys.stdin.read()
            if content.strip():
                url = input("\nEnter the conversation URL (optional): ").strip()
                if not url:
                    url = "manual_entry"

                title = input("Enter a title for this conversation (optional): ").strip()

                self.save_conversation(content, url, title)
                print("\n✓ Conversation saved successfully!")
            else:
                print("No content provided.")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download Claude.ai conversations to text files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a single conversation:
  python download_claude_links.py https://claude.ai/chat/abc123

  # Download multiple conversations from a file:
  python download_claude_links.py --file urls.txt

  # Manual copy-paste mode:
  python download_claude_links.py --manual

  # Specify output directory:
  python download_claude_links.py --output my_chats https://claude.ai/chat/abc123
        """
    )

    parser.add_argument(
        'urls',
        nargs='*',
        help='Claude.ai conversation URLs to download'
    )
    parser.add_argument(
        '--file', '-f',
        help='File containing list of URLs (one per line)'
    )
    parser.add_argument(
        '--output', '-o',
        default='claude_conversations',
        help='Output directory for saved conversations (default: claude_conversations)'
    )
    parser.add_argument(
        '--manual', '-m',
        action='store_true',
        help='Manual mode: paste conversation content directly'
    )

    args = parser.parse_args()

    downloader = ClaudeDownloader(output_dir=args.output)

    # Manual mode
    if args.manual:
        downloader.manual_mode()
        return

    # Collect URLs
    urls: List[str] = []

    if args.urls:
        urls.extend(args.urls)

    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                urls.extend(file_urls)
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found")
            return
        except Exception as e:
            print(f"Error reading file: {e}")
            return

    if not urls:
        parser.print_help()
        print("\nError: No URLs provided. Use --manual for manual mode or provide URLs.")
        return

    # Download conversations
    print(f"\nDownloading {len(urls)} conversation(s)...\n")

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")

        if not PLAYWRIGHT_AVAILABLE:
            print("Skipping: Playwright not available. Install with: pip install playwright && playwright install chromium")
            continue

        content = await downloader.download_with_playwright(url)

        if content:
            downloader.save_conversation(content, url)
            print("✓ Success")
        else:
            print("✗ Failed")

        # Add delay between downloads to be respectful
        if i < len(urls):
            await asyncio.sleep(2)

    print(f"\n{'='*80}")
    print(f"Download complete! Files saved to: {downloader.output_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        # Fix for Windows event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())

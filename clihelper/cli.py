#!/usr/bin/env python3
"""CLIHelper - Instant command-line help using Claude AI"""

import sys
import os
import subprocess
from pathlib import Path
from anthropic import Anthropic

__version__ = "0.1.0"

class CLIHelper:
    def __init__(self):
        self.api_key = self.get_or_setup_api_key()
        
    def get_or_setup_api_key(self):
        """Get API key from file or prompt for it."""
        key_file = Path.home() / ".clihelper_key"
        
        # Check file first
        if key_file.exists():
            return key_file.read_text().strip()
        
        # Check environment
        if key := os.getenv("ANTHROPIC_API_KEY"):
            return key
            
        # First time setup
        print("🚀 Welcome to CLIHelper!")
        print("\nGet your API key at: https://console.anthropic.com/settings/keys")
        key = input("Enter your Anthropic API key: ").strip()
        
        # Save for next time
        key_file.write_text(key)
        key_file.chmod(0o600)
        print("✅ Key saved to ~/.clihelper_key\n")
        return key
    
    def get_recent_history(self, n=5):
        """Get recent bash history."""
        try:
            result = subprocess.run(
                ['bash', '-i', '-c', f'history {n}'],
                capture_output=True, text=True, timeout=1
            )
            return result.stdout
        except:
            return ""
    
    def analyze(self, error_output, user_context=""):
        """Send to Claude for analysis."""
        history = self.get_recent_history()
        
        prompt = f"""You are a CLI assistant. A user ran a command that didn't work.

Recent command history:
{history}

Error output:
{error_output}

{f"User context: {user_context}" if user_context else ""}

Please:
1. Briefly explain what went wrong
2. Provide the correct command (prefix with $)
3. Add a short explanation

Be concise and practical."""

        client = Anthropic(api_key=self.api_key)
        
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error calling Claude API: {e}"

def main():
    """Main entry point."""
    helper = CLIHelper()
    
    # Check if data is being piped in
    if sys.stdin.isatty():
        print("CLIHelper - Instant command-line help")
        print("\nUsage:")
        print("  command_that_fails 2>&1 | clihelper")
        print("  command_that_fails 2>&1 | clihelper 'optional context'")
        print("\nExample:")
        print("  ls --fake-flag 2>&1 | clihelper")
        sys.exit(0)
    
    # Read piped input
    error_output = sys.stdin.read()
    user_context = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    # Get and display analysis
    result = helper.analyze(error_output, user_context)
    
    print("\n" + "="*50)
    print("🤖 CLIHelper says:")
    print("="*50)
    print(result)
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
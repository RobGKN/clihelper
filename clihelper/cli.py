#!/usr/bin/env python3
"""CLIHelper - Instant command-line help using Claude AI"""

import sys
import os
import re
import subprocess
from pathlib import Path
from anthropic import Anthropic

__version__ = "0.2.0"

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
    
    def redact_sensitive_info(self, text):
        """Remove sensitive information from text."""
        # Patterns to redact
        patterns = [
            # API Keys (various formats)
            (r'(sk-[a-zA-Z0-9]{20,})', 'sk-REDACTED'),
            (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})', r'\1REDACTED'),
            (r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})', r'\1REDACTED'),
            (r'(bearer\s+)([a-zA-Z0-9_\-\.]{20,})', r'\1REDACTED'),
            
            # AWS Keys
            (r'(AKIA[0-9A-Z]{16})', 'AWS_KEY_REDACTED'),
            (r'(aws_secret_access_key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9/+=]{40})', r'\1REDACTED'),
            
            # Passwords in common formats
            (r'(password["\']?\s*[:=]\s*["\']?)([^\s\'"]+)', r'\1REDACTED'),
            (r'(passwd["\']?\s*[:=]\s*["\']?)([^\s\'"]+)', r'\1REDACTED'),
            (r'(pwd["\']?\s*[:=]\s*["\']?)([^\s\'"]+)', r'\1REDACTED'),
            
            # SSH/URLs with passwords
            (r'(://[^:]+:)([^@]+)(@)', r'\1REDACTED\3'),
            (r'(sshpass\s+-p\s+)([^\s]+)', r'\1REDACTED'),
            
            # Credit card-like numbers
            (r'\b([0-9]{4}[\s\-]?){3}[0-9]{4}\b', 'CARD_REDACTED'),
            
            # Private keys
            (r'(-----BEGIN [A-Z ]*PRIVATE KEY-----)[\s\S]+(-----END [A-Z ]*PRIVATE KEY-----)', 
             '-----BEGIN PRIVATE KEY-----\nREDACTED\n-----END PRIVATE KEY-----'),
        ]
        
        result = text
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def get_recent_history_with_context(self, n=10):
        """Get recent bash history with limited output context."""
        try:
            # Get command history
            history_result = subprocess.run(
                ['bash', '-i', '-c', f'history {n}'],
                capture_output=True, text=True, timeout=1
            )
            
            # Get the last command's output (if available)
            # This is a simplified approach - getting full output history is complex
            last_cmd_result = subprocess.run(
                ['bash', '-i', '-c', 'fc -ln -1'],
                capture_output=True, text=True, timeout=1
            )
            
            history = history_result.stdout
            last_cmd = last_cmd_result.stdout.strip()
            
            context = f"Recent command history:\n{history}\n"
            
            if last_cmd:
                context += f"\nLast command run: {last_cmd}"
            
            return self.redact_sensitive_info(context)
            
        except:
            return "Could not retrieve command history"
    
    def analyze_direct_query(self, query):
        """Handle direct queries without piped input."""
        history_context = self.get_recent_history_with_context()
        
        prompt = f"""You are a helpful CLI assistant. A user wants help with command-line tasks.

{history_context}

User's question: {query}

Please provide helpful command-line advice. If they're asking about a specific command:
1. Explain what the command does
2. Provide the correct syntax (prefix commands with $)
3. Give practical examples

Be concise and practical."""

        return self.call_api(prompt)
    
    def analyze_error(self, error_output, user_context=""):
        """Analyze a command error."""
        # Redact sensitive info from error output
        safe_output = self.redact_sensitive_info(error_output)
        safe_context = self.redact_sensitive_info(user_context)
        
        history_context = self.get_recent_history_with_context()
        
        prompt = f"""You are a CLI assistant. A user ran a command that didn't work.

{history_context}

Error output:
{safe_output}

{f"User context: {safe_context}" if safe_context else ""}

Please:
1. Briefly explain what went wrong
2. Provide the correct command (prefix with $)
3. Add a short explanation

Be concise and practical."""

        return self.call_api(prompt)
    
    def call_api(self, prompt):
        """Call Claude API with the prompt."""
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
        # No pipe - check for direct query arguments
        if len(sys.argv) > 1:
            # Direct query mode
            query = " ".join(sys.argv[1:])
            
            print("\n🔍 Analyzing your query with recent command context...")
            result = helper.analyze_direct_query(query)
            
            print("\n" + "="*50)
            print("🤖 CLIHelper says:")
            print("="*50)
            print(result)
            print("="*50 + "\n")
        else:
            # No arguments - show usage
            print("CLIHelper v" + __version__ + " - Instant command-line help")
            print("\nUsage:")
            print("  clihelper 'how do I find large files?'        # Direct query")
            print("  clihelper 'what was that git command?'        # Ask about recent commands")
            print("  command_that_fails 2>&1 | clihelper           # Analyze error")
            print("  command_that_fails 2>&1 | clihelper 'context' # Analyze with context")
            print("\nExamples:")
            print("  clihelper 'how to compress a directory'")
            print("  clihelper 'explain the last command'")
            print("  ls --fake-flag 2>&1 | clihelper")
        sys.exit(0)
    
    # Piped mode - analyze error
    error_output = sys.stdin.read()
    user_context = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    # Get and display analysis
    result = helper.analyze_error(error_output, user_context)
    
    print("\n" + "="*50)
    print("🤖 CLIHelper says:")
    print("="*50)
    print(result)
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
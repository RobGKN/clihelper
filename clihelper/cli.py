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
    def __init__(self, debug=False):
        self.debug = debug
        self.api_key = self.get_or_setup_api_key()
        self.ensure_prompt_command()
        
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
    
    def ensure_prompt_command(self):
        """Ask user if they want to enable live shell history syncing."""
        marker = Path.home() / ".clihelper_prompt_command_configured"

        # Only run once
        if marker.exists():
            return

        # Only apply to bash
        shell = os.getenv("SHELL", "")
        if "bash" not in shell:
            marker.write_text("skipped (non-bash shell)")
            return

        bashrc = Path.home() / ".bashrc"

        print("\n📘 CLIHelper setup: Improve shell history detection\n")
        print("CLIHelper can give MUCH better answers if Bash writes history")
        print("after every command instead of only on logout.\n")
        print("Would you like to enable this by adding the following line to ~/.bashrc?\n")
        print("    export PROMPT_COMMAND=\"history -a\"\n")

        choice = input("Enable this? [Y/n]: ").strip().lower()

        if choice in ["", "y", "yes"]:
            try:
                with bashrc.open("a") as f:
                    f.write("\n# Added by CLIHelper to sync shell history\n")
                    f.write('export PROMPT_COMMAND="history -a"\n')

                print("\n✅ Enabled! Bash will now sync history after each command.")
                print("   You need to open a new terminal for this to take effect.\n")

                marker.write_text("enabled")
            except Exception as e:
                print(f"⚠️ Could not modify ~/.bashrc: {e}")
                marker.write_text("failed")
        else:
            print("\n❌ Skipped. CLIHelper will work, but may not detect recent commands.")
            marker.write_text("skipped")
    
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
        try:
            history_file = Path.home() / ".bash_history"
            if not history_file.exists():
                return "No Bash history found."

            # Read last N lines
            lines = history_file.read_text().splitlines()[-n:]
            context = "Recent command history:\n" + "\n".join(lines)
            return self.redact_sensitive_info(context)

        except Exception as e:
            return f"Could not retrieve command history: {e}"
    
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

        if self.debug:
            print("\n[CLIHelper DEBUG] Prompt being sent to LLM:\n")
            print(prompt)
            print("\n[CLIHelper DEBUG] End prompt\n")

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
    # Parse --debug flag and strip it from args
    debug = False
    args = sys.argv[1:]
    if "--debug" in args:
        debug = True
        args = [a for a in args if a != "--debug"]

    helper = CLIHelper(debug=debug)
    
    # Check if data is being piped in
    if sys.stdin.isatty():
        # No pipe - check for direct query arguments
        if len(args) > 0:
            # Direct query mode
            query = " ".join(args)
            
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
            print("  clihelper --debug 'how do I find large files?' # Debug prompt to LLM")
            print("\nExamples:")
            print("  clihelper 'how to compress a directory'")
            print("  clihelper 'explain the last command'")
            print("  ls --fake-flag 2>&1 | clihelper")
        sys.exit(0)
    
    # Piped mode - analyze error
    error_output = sys.stdin.read()
    user_context = " ".join(args) if len(args) > 0 else ""
    
    # Get and display analysis
    result = helper.analyze_error(error_output, user_context)
    
    print("\n" + "="*50)
    print("🤖 CLIHelper says:")
    print("="*50)
    print(result)
    print("="*50 + "\n")

if __name__ == "__main__":
    main()

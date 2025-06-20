
"""
Script to convert Anthropic Claude PG-MCP client code to use OpenAI API instead.

This script looks for Claude-specific imports and API calls in Python files
and replaces them with OpenAI equivalents.
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Tuple

# Patterns to search for and their replacements
REPLACEMENTS = [
    # Import replacements
    (
        r"from anthropic import Anthropic",
        "from openai import OpenAI"
    ),
    (
        r"from anthropic.async_api import AsyncAnthropic",
        "from openai import AsyncOpenAI"
    ),
    (
        r"import anthropic",
        "import openai"
    ),
    
    # Client initialization
    (
        r"anthropic_client\s*=\s*Anthropic\(api_key=.*\)",
        "openai_client = OpenAI(api_key=os.environ.get(\"OPENAI_API_KEY\"))"
    ),
    (
        r"async_anthropic_client\s*=\s*AsyncAnthropic\(api_key=.*\)",
        "async_openai_client = AsyncOpenAI(api_key=os.environ.get(\"OPENAI_API_KEY\"))"
    ),
    
    # API call replacements
    (
        r"anthropic_client\.messages\.create\(\s*model\s*=\s*[\"']claude-.*[\"'],",
        "openai_client.chat.completions.create(\n    model=os.environ.get(\"OPENAI_MODEL\", \"gpt-4o\"),"
    ),
    (
        r"async_anthropic_client\.messages\.create\(\s*model\s*=\s*[\"']claude-.*[\"'],",
        "async_openai_client.chat.completions.create(\n    model=os.environ.get(\"OPENAI_MODEL\", \"gpt-4o\"),"
    ),
    
    # Parameter replacements
    (
        r"max_tokens\s*=\s*\d+",
        "max_tokens=1024"
    ),
    (
        r"temperature\s*=\s*\d+(\.\d+)?",
        "temperature=0.7"
    ),
    
    # Message format replacements
    (
        r"system\s*=\s*",
        "messages=[{\"role\": \"system\", \"content\": "
    ),
    (
        r"messages\s*=\s*\[\s*\{\s*\"role\"\s*:\s*\"user\"",
        "messages=[{\"role\": \"system\", \"content\": system_prompt}, {\"role\": \"user\""
    ),
    
    # Response handling
    (
        r"response\.content\[0]\.text",
        "response.choices[0].message.content"
    ),
    
    # Tool calling replacements
    (
        r"tools\s*=\s*\[\s*\{\s*\"type\"\s*:\s*\"function\"",
        "tools=tool_list"
    ),
    
    # Environment variable replacements
    (
        r"ANTHROPIC_API_KEY",
        "OPENAI_API_KEY"
    ),
    (
        r"CLAUDE_MODEL",
        "OPENAI_MODEL"
    ),
]

def convert_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    Convert a single file by applying all replacements.
    
    Args:
        file_path: Path to the file to convert
        
    Returns:
        Tuple containing count of replacements made and list of modifications
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Apply all replacements
    for pattern, replacement in REPLACEMENTS:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            changes.append(f"- Replaced '{pattern}' with '{replacement}' ({count} occurrences)")
            content = new_content
    
    # Count total changes
    total_changes = len(changes)
    
    # Only write to file if changes were made
    if content != original_content:
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
            
        # Write converted content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return total_changes, changes

def convert_directory(directory_path: Path) -> Tuple[int, int]:
    """
    Convert all Python files in a directory.
    
    Args:
        directory_path: Path to directory to convert
        
    Returns:
        Tuple containing count of files modified and total replacements made
    """
    files_modified = 0
    total_replacements = 0
    
    # Find all Python files
    python_files = list(directory_path.glob('**/*.py'))
    print(f"Found {len(python_files)} Python files to check")
    
    for file_path in python_files:
        changes, modifications = convert_file(file_path)
        
        if changes > 0:
            files_modified += 1
            total_replacements += changes
            print(f"\nModified: {file_path} ({changes} replacements)")
            for mod in modifications:
                print(f"  {mod}")
    
    return files_modified, total_replacements

def main():
    """Main function to run the conversion script"""
    parser = argparse.ArgumentParser(description="Convert PG-MCP client from Anthropic to OpenAI")
    parser.add_argument("path", help="Path to file or directory to convert")
    args = parser.parse_args()
    
    target_path = Path(args.path)
    
    if not target_path.exists():
        print(f"Error: {target_path} does not exist")
        return
    
    print(f"Converting {target_path} from Anthropic to OpenAI...")
    
    if target_path.is_file():
        if target_path.suffix != '.py':
            print(f"Error: {target_path} is not a Python file")
            return
            
        changes, modifications = convert_file(target_path)
        if changes > 0:
            print(f"Successfully converted {target_path} with {changes} replacements:")
            for mod in modifications:
                print(f"  {mod}")
        else:
            print(f"No changes needed for {target_path}")
            
    elif target_path.is_dir():
        files_modified, total_replacements = convert_directory(target_path)
        print(f"\nConversion complete: Modified {files_modified} files with {total_replacements} total replacements")
        print("Backup files with .py.bak extension were created for modified files")
    
if __name__ == "__main__":
    main()

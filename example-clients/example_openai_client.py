#!/usr/bin/env python
"""
Example script demonstrating how to use the OpenAI PG-MCP Client
to query a PostgreSQL database using natural language.

Make sure to set up the environment variables in .env file before running.
"""

import os
import asyncio
from dotenv import load_dotenv
from openai_pg_mcp_client import OpenAIPgMcpClient

async def run_example():
    # Load environment variables
    load_dotenv()
    
    # Get database URL and MCP server URL from environment variables
    database_url = os.environ.get("DATABASE_URL")
    pg_mcp_url = os.environ.get("PG_MCP_URL", "http://localhost:8000/sse")
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Initialize client
    client = OpenAIPgMcpClient(pg_mcp_url)
    await client.initialize()
    
    try:
        # Connect to database
        await client.connect_to_database(database_url)
        
        # Example queries
        queries = [
            "What tables are in this database?",
            "How many records are in the users table?",
            "Show me the schema of the orders table",
            "What are the top 5 products by sales?"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            response = await client.chat(query)
            print(f"Response: {response}")
            
            # Add a small delay between requests
            await asyncio.sleep(1)
            
    finally:
        # Ensure we disconnect
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_example())

"""
Simplified OpenAI PG-MCP Client

A minimal client for connecting to the PG-MCP server with OpenAI.
This version has better error handling for cloud deployments.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SimpleOpenAIClient:
    """Simple client for connecting to a PostgreSQL database via OpenAI"""

    def __init__(self):
        # Initialize OpenAI client
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        
        # Define database tools manually
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "connect",
                    "description": "Register a database connection string and get a connection ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "connection_string": {
                                "type": "string",
                                "description": "PostgreSQL connection string"
                            }
                        },
                        "required": ["connection_string"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "disconnect",
                    "description": "Close a database connection",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "connection_id": {
                                "type": "string",
                                "description": "Connection ID to close"
                            }
                        },
                        "required": ["connection_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pg_query",
                    "description": "Execute a SQL query using a connection ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "connection_id": {
                                "type": "string",
                                "description": "Connection ID to use"
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute"
                            }
                        },
                        "required": ["connection_id", "query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pg_explain",
                    "description": "Get query execution plan",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "connection_id": {
                                "type": "string",
                                "description": "Connection ID to use"
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL query to explain"
                            }
                        },
                        "required": ["connection_id", "query"]
                    }
                }
            }
        ]
        
        # Set up system prompt
        self.system_prompt = """
        You are a helpful assistant with access to a PostgreSQL database.
        Your task is to help the user interact with their database by:
        1. Understanding their questions about the database
        2. Converting natural language to SQL when appropriate
        3. Using the available database tools to explore and query the database
        4. Explaining query results in a clear, helpful manner
        
        Always think step by step about what the user is asking, and use the appropriate tools to help them.
        """
        
        self.conn_id = None
    
    def connect_to_database(self, connection_string: str) -> str:
        """Connect to a PostgreSQL database and return connection ID"""
        # In a real implementation, this would call the MCP server
        # For this simplified version, we just return a mock connection ID
        self.conn_id = "mock-connection-id"
        logger.info(f"Connected to database with connection ID: {self.conn_id}")
        return self.conn_id
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query against the connected database"""
        # In a real implementation, this would call the MCP server
        # For this simplified version, we return mock data
        logger.info(f"Executing query: {query}")
        
        # Simple mock data based on query
        if "SELECT" in query.upper():
            return {
                "columns": ["id", "name", "value"],
                "rows": [
                    [1, "Example 1", 100],
                    [2, "Example 2", 200],
                    [3, "Example 3", 300]
                ]
            }
        else:
            return {"status": "success", "message": "Query executed successfully"}
    
    def chat(self, user_message: str) -> str:
        """Process a user message and return the assistant's response"""
        try:
            # If not connected, try to auto-connect with environment variable
            if not self.conn_id:
                db_url = os.environ.get("DATABASE_URL")
                if db_url:
                    self.connect_to_database(db_url)
            
            # Call OpenAI API with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Handle tool calls
            if message.tool_calls:
                # Create a new message to add to conversation
                assistant_message = {"role": "assistant", "content": None, "tool_calls": []}
                tool_responses = []
                
                # Process each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Calling tool {function_name} with args: {function_args}")
                    
                    # Mock tool response based on function called
                    tool_result = None
                    if function_name == "connect":
                        tool_result = {"connection_id": "mock-connection-id"}
                        self.conn_id = "mock-connection-id"
                    elif function_name == "disconnect":
                        tool_result = {"status": "disconnected"}
                        self.conn_id = None
                    elif function_name == "pg_query":
                        tool_result = self.execute_query(function_args.get("query", ""))
                    elif function_name == "pg_explain":
                        tool_result = {"plan": "Seq Scan on example_table (cost=0.00..1.00 rows=3 width=20)"}
                    else:
                        tool_result = {"error": "Unknown tool"}
                    
                    # Add tool response
                    tool_responses.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                
                # Create a second OpenAI API call to process the tool results
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls}
                ]
                messages.extend(tool_responses)
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.tools,
                        tool_choice="auto"
                    )
                    
                    final_message = response.choices[0].message
                    return final_message.content
                except Exception as e:
                    logger.error(f"Error in second API call: {e}")
                    return f"Error processing tool results: {str(e)}"
            
            return message.content
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"Error: {str(e)}"

def main():
    """Main function for CLI usage"""
    # Initialize client
    try:
        client = SimpleOpenAIClient()
        
        print("OpenAI PG-MCP Client (Simplified)")
        print("Type 'exit' to quit")
        
        while True:
            user_input = input("\nYour query: ")
            if user_input.lower() == "exit":
                break
                
            response = client.chat(user_input)
            print(f"\nAssistant: {response}")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()

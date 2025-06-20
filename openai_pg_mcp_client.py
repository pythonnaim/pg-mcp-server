"""
OpenAI PG-MCP Client

A modified version of the PG-MCP client that uses OpenAI models instead of Anthropic's Claude.
This client connects to a PostgreSQL MCP server and allows querying databases using natural language.
"""

import os
import json
import asyncio
import argparse
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
import logging

# MCP client imports
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.shared.schema import ToolDefinition, ToolParam

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class OpenAIPgMcpClient:
    """Client for connecting to a PostgreSQL MCP server using OpenAI models"""

    def __init__(self, pg_mcp_url: str):
        self.pg_mcp_url = pg_mcp_url
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.async_openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.session: Optional[ClientSession] = None
        self.conn_id: Optional[str] = None
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        
        # Set up system prompt
        self.system_prompt = """
        You are a helpful assistant with access to a PostgreSQL database through the PG-MCP server.
        Your task is to help the user interact with their database by:
        1. Understanding their questions about the database
        2. Converting natural language to SQL when appropriate
        3. Using the available database tools to explore and query the database
        4. Explaining query results in a clear, helpful manner
        
        Available tools:
        - connect: Register a database connection string and get a connection ID
        - disconnect: Close a database connection
        - pg_query: Execute SQL queries using a connection ID
        - pg_explain: Get query execution plans
        
        Always think step by step about what the user is asking, and use the appropriate tools to help them.
        """

    async def initialize(self):
        """Initialize the client session and connect to the MCP server"""
        transport = await sse_client(self.pg_mcp_url)
        self.session = await ClientSession.create(transport=transport)
        await self._load_tools()
        
    async def _load_tools(self):
        """Load available tools from the MCP server"""
        server_info = await self.session.server_info()
        tools = server_info.tools or []
        
        # Convert MCP tools to OpenAI function format
        for tool in tools:
            openai_tool = self._convert_tool_to_openai_format(tool)
            self.tools[tool.name] = openai_tool
            
        logger.info(f"Loaded {len(self.tools)} tools from MCP server")
        
    def _convert_tool_to_openai_format(self, tool: ToolDefinition) -> Dict[str, Any]:
        """Convert MCP tool definition to OpenAI function calling format"""
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        if tool.params:
            for param in tool.params:
                param_schema = self._convert_param_schema(param)
                parameters["properties"][param.name] = param_schema
                
                if param.required:
                    parameters["required"].append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Tool for {tool.name}",
                "parameters": parameters
            }
        }
    
    def _convert_param_schema(self, param: ToolParam) -> Dict[str, Any]:
        """Convert MCP parameter schema to OpenAI function parameter schema"""
        # This is a simplified conversion - expand as needed
        schema = {}
        
        if param.description:
            schema["description"] = param.description
            
        # Map MCP param types to JSON schema types
        if param.type == "string":
            schema["type"] = "string"
        elif param.type == "number":
            schema["type"] = "number"
        elif param.type == "integer":
            schema["type"] = "integer"
        elif param.type == "boolean":
            schema["type"] = "boolean"
        elif param.type == "array":
            schema["type"] = "array"
            # Add items schema if available
            if hasattr(param, "items") and param.items:
                schema["items"] = {"type": param.items}
        else:
            # Default to string for unknown types
            schema["type"] = "string"
            
        return schema
    
    async def connect_to_database(self, connection_string: str) -> str:
        """Connect to a PostgreSQL database using the connect tool"""
        if not self.session:
            raise ValueError("Client not initialized. Call initialize() first.")
            
        result = await self.session.call_tool("connect", {"connection_string": connection_string})
        self.conn_id = result.get("connection_id")
        
        if not self.conn_id:
            raise ValueError("Failed to connect to database. No connection ID returned.")
            
        logger.info(f"Connected to database with connection ID: {self.conn_id}")
        return self.conn_id
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query against the connected database"""
        if not self.session or not self.conn_id:
            raise ValueError("Not connected to database. Call connect_to_database() first.")
            
        result = await self.session.call_tool(
            "pg_query", 
            {"connection_id": self.conn_id, "query": query}
        )
        return result
    
    async def explain_query(self, query: str) -> Dict[str, Any]:
        """Get the execution plan for a SQL query"""
        if not self.session or not self.conn_id:
            raise ValueError("Not connected to database. Call connect_to_database() first.")
            
        result = await self.session.call_tool(
            "pg_explain", 
            {"connection_id": self.conn_id, "query": query}
        )
        return result
    
    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.session and self.conn_id:
            await self.session.call_tool("disconnect", {"connection_id": self.conn_id})
            self.conn_id = None
            logger.info("Disconnected from database")
    
    async def chat(self, user_message: str) -> str:
        """Process a user message and return the assistant's response"""
        if not self.session:
            raise ValueError("Client not initialized. Call initialize() first.")
        
        # Create function list for OpenAI
        openai_tools = list(self.tools.values())
        
        # Call OpenAI API with function calling
        response = await self.async_openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            tools=openai_tools,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # Handle tool calls
        if message.tool_calls:
            # Create a new message to add to conversation
            assistant_message = {"role": "assistant", "content": None, "tool_calls": []}
            
            # Process each tool call
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Calling tool {function_name} with args: {function_args}")
                
                # Call the MCP tool
                tool_result = await self.session.call_tool(function_name, function_args)
                
                # Add tool call to the assistant message
                assistant_message["tool_calls"].append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": tool_call.function.arguments
                    }
                })
                
                # Add tool response to messages
                tool_response = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                }
                
                # Create a second OpenAI API call to process the tool results
                response = await self.async_openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls},
                        tool_response
                    ],
                    tools=openai_tools,
                    tool_choice="auto"
                )
                
                final_message = response.choices[0].message
                return final_message.content
        
        return message.content

async def main():
    """Main function for CLI usage"""
    parser = argparse.ArgumentParser(description="OpenAI PG-MCP Client")
    parser.add_argument("--query", help="Natural language query to execute")
    args = parser.parse_args()
    
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
        
        if args.query:
            # Execute single query mode
            response = await client.chat(args.query)
            print(response)
        else:
            # Interactive mode
            print("Connected to PostgreSQL database. Type 'exit' to quit.")
            while True:
                user_input = input("\nYour query: ")
                if user_input.lower() == "exit":
                    break
                    
                response = await client.chat(user_input)
                print(f"\nAssistant: {response}")
    finally:
        # Ensure we disconnect
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

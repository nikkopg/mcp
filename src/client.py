from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from openai import OpenAI
import json

client = OpenAI(
     base_url="http://localhost:11434/v1",
     api_key="ollama"
)

def call_llm(functions, prompt="Explain what MXFP4 quantization is."):
    response = client.chat.completions.create(
        model="gpt-oss:20b",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        tools = functions
    )

    functions_to_call = []

    if response.choices:
        for choice in response.choices:
            if choice.message and choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    print("TOOL: ", tool_call)
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    functions_to_call.append({ "name": name, "args": args })

    return functions_to_call

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="mcp",  # Executable
    args=["run", "src/server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

async def run():
        """Main client execution function"""
        print("🚀 Starting MCP Python Client...")

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    print("📡 Connecting to MCP server...")
                    
                    # Initialize the connection
                    await session.initialize()
                    print("✅ Connected to MCP server successfully!")

                    # List available tools
                    functions = await list_tools(session)
                    
                    prompt = "Add 220 to 321"
                    # ask LLM what tools to all, if any
                    functions_to_call = call_llm(functions, prompt)

                    # call suggested functions
                    for f in functions_to_call:
                        result = await session.call_tool(f["name"], arguments=f["args"])
                        print("TOOLS result: ", result.content)
                    
                    # Test calculator operations
                    await test_calculator_operations(session)
                    
                    # List and test resources
                    await list_and_test_resources(session)
                    
                    print("\n✨ Client operations completed successfully!")

        except Exception as e:
            print(f"❌ Error running MCP client: {e}")
            raise

async def list_tools(session: ClientSession):
        """List all available tools on the server"""
        print("\n📋 Listing available tools:")
        try:
            functions = []
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
                print("Tool", tool.inputSchema["properties"])
                functions.append(convert_to_llm_tool(tool))
                return functions
            
        except Exception as e:
            print(f"  Error listing tools: {e}")

async def test_calculator_operations(session: ClientSession):
        """Test various calculator operations"""
        print("\n🧮 Testing Calculator Operations:")

        operations = [
            ("add", {"a": 5, "b": 3}, "Add 5 + 3"),
            ("subtract", {"a": 10, "b": 4}, "Subtract 10 - 4"),
            ("multiply", {"a": 6, "b": 7}, "Multiply 6 × 7"),
            ("divide", {"a": 20, "b": 4}, "Divide 20 ÷ 4"),
            ("help", {}, "Help Information"),
        ]

        for tool_name, arguments, description in operations:
            try:
                result = await session.call_tool(tool_name, arguments=arguments)
                result_text = extract_text_result(result)
                
                if tool_name == "help":
                    print(f"\n📖 {description}:")
                    print(result_text)
                else:
                    print(f"{description} = {result_text}")
                    
            except Exception as e:
                print(f"  Error calling {tool_name}: {e}")

async def list_and_test_resources(session: ClientSession):
        """List and test reading resources"""
        print("\n📄 Listing available resources:")
        try:
            resources = await session.list_resources()
            for resource in resources.resources:
                print(f"  - {resource.name}: {resource.description}")
                print(f"    URI: {resource.uri}")

            # Test reading a resource if available
            if resources.resources:
                first_resource = resources.resources[0]
                print(f"\n📖 Reading resource: {first_resource.name}")
                try:
                    content = await session.read_resource(first_resource.uri)
                    print(f"Resource content: {content}")
                except Exception as e:
                    print(f"  Error reading resource: {e}")
            else:
                print("  No resources available")
                
        except Exception as e:
            print(f"  Error listing resources: {e}")

def extract_text_result(result) -> str:
    """
    Extract text content from a tool result object.

    This method attempts to extract the text content from the `content` attribute
    of the result object. If no text content is found, it falls back to converting
    the result to a string. If an error occurs during extraction, it returns "No result".

    Args:
        result: The result object returned by a tool, which may contain a `content` attribute
                with text or other types of data.

    Returns:
        A string representing the extracted text content, or a fallback string if no text is found.
    """
    try:
        if hasattr(result, 'content') and result.content:
            for content_item in result.content:
                if hasattr(content_item, 'text') and content_item.text:
                    return content_item.text
                elif hasattr(content_item, 'type') and content_item.type == "text":
                    return getattr(content_item, 'text', str(content_item))
        
        # Fallback: try to convert to string
        return str(result)
    except Exception:
        return "No result"
    
def convert_to_llm_tool(tool):
    tool_schema = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "type": "function",
            "parameters": {
                "type": "object",
                "properties": tool.inputSchema["properties"]
            }
        }
    }

    return tool_schema


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
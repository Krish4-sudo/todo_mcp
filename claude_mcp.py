# claude_todo_integration.py
"""
This script demonstrates how to integrate Claude Desktop with our Todo API using the Model Control Protocol (MCP).
It allows you to manage your todo items through natural language conversations with Claude.
"""

import requests
import json
import subprocess
import re
import os
import time

# Configuration
API_BASE_URL = "http://localhost:8000/api"
CLAUDE_MCP_PORT = 8080  # Default MCP port for Claude Desktop

class ClaudeMCPTodoAssistant:
    def __init__(self, api_base_url=API_BASE_URL, mcp_port=CLAUDE_MCP_PORT):
        self.api_base_url = api_base_url
        self.mcp_port = mcp_port
        self.mcp_url = f"http://localhost:{mcp_port}/v1/messages"
        
    def send_to_claude(self, message):
        """Send a message to Claude via MCP and get the response"""
        try:
            payload = {
                "model": "claude-3-opus-20240229",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 4000
            }
            
            response = requests.post(self.mcp_url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Extract the assistant's message content
            return response_data["content"][0]["text"]
            
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Claude: {e}")
            if "Connection refused" in str(e):
                print("Make sure Claude Desktop is running and MCP is enabled.")
            return None
    
    def get_todos(self):
        """Get all todos from the API"""
        try:
            response = requests.get(f"{self.api_base_url}/todos/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting todos: {e}")
            return []
    
    def create_todo(self, title, description=""):
        """Create a new todo item"""
        try:
            data = {"title": title, "description": description}
            response = requests.post(f"{self.api_base_url}/todos/", json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating todo: {e}")
            return None
    
    def update_todo(self, todo_id, update_data):
        """Update an existing todo item"""
        try:
            response = requests.put(f"{self.api_base_url}/todos/{todo_id}", json=update_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error updating todo: {e}")
            return None
    
    def delete_todo(self, todo_id):
        """Delete a todo item"""
        try:
            response = requests.delete(f"{self.api_base_url}/todos/{todo_id}")
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error deleting todo: {e}")
            return False
    
    def interpret_command(self, user_input):
        """Use Claude to interpret the user's natural language command and execute the appropriate action"""
        # Prepare prompt for Claude
        todos = self.get_todos()
        todos_list = "\n".join([f"{t['id']}: {t['title']} - {t['description'] or 'No description'} - {'Completed' if t['completed'] else 'Not completed'}" for t in todos])
        
        prompt = f"""
        You are a Todo management assistant. I want you to help me manage my todo list using natural language commands.
        
        Current Todo Items:
        {todos_list if todos else "No todos available."}
        
        Based on the user's message, determine what action they want to take:
        1. Create a new todo
        2. Update an existing todo
        3. Mark a todo as complete/incomplete
        4. Delete a todo
        5. List todos
        6. Get details about a specific todo
        
        For your response, use one of these formats:
        CREATE: <title> | <description>
        UPDATE: <id> | <field> | <new_value>
        COMPLETE: <id> | <true/false>
        DELETE: <id>
        LIST:
        GET: <id>
        UNKNOWN: <explanation>
        
        USER MESSAGE: "{user_input}"
        """
        
        # Send to Claude and get the interpreted command
        claude_response = self.send_to_claude(prompt)
        
        if not claude_response:
            return "Sorry, I couldn't connect to Claude. Please check if Claude Desktop is running with MCP enabled."
        
        # Execute the command
        command_match = re.match(r"^(CREATE|UPDATE|COMPLETE|DELETE|LIST|GET|UNKNOWN):\s*(.*)$", claude_response, re.DOTALL)
        
        if not command_match:
            return f"I couldn't interpret Claude's response correctly. Raw response: {claude_response}"
        
        command, params = command_match.groups()
        params = params.strip()
        
        # Execute the command
        if command == "CREATE":
            parts = params.split('|', 1)
            title = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ""
            result = self.create_todo(title, description)
            if result:
                return f"Created new todo: '{title}'"
            else:
                return "Failed to create todo."
                
        elif command == "UPDATE":
            parts = params.split('|')
            if len(parts) != 3:
                return "Invalid update format."
            todo_id = int(parts[0].strip())
            field = parts[1].strip()
            value = parts[2].strip()
            
            update_data = {}
            if field == "title":
                update_data["title"] = value
            elif field == "description":
                update_data["description"] = value
            elif field == "completed":
                update_data["completed"] = value.lower() == "true"
            
            result = self.update_todo(todo_id, update_data)
            if result:
                return f"Updated todo #{todo_id}: {field} set to '{value}'"
            else:
                return f"Failed to update todo #{todo_id}."
                
        elif command == "COMPLETE":
            parts = params.split('|')
            todo_id = int(parts[0].strip())
            completed = parts[1].strip().lower() == "true"
            result = self.update_todo(todo_id, {"completed": completed})
            status = "completed" if completed else "marked as incomplete"
            if result:
                return f"Todo #{todo_id} {status}."
            else:
                return f"Failed to update todo #{todo_id}."
                
        elif command == "DELETE":
            todo_id = int(params.strip())
            if self.delete_todo(todo_id):
                return f"Deleted todo #{todo_id}."
            else:
                return f"Failed to delete todo #{todo_id}."
                
        elif command == "LIST":
            if not todos:
                return "Your todo list is empty."
            
            # Ask Claude to format the todos in a nice way
            format_prompt = f"""
            Please format this todo list in a clean, user-friendly way:
            
            {todos_list}
            """
            formatted_list = self.send_to_claude(format_prompt)
            return formatted_list
                
        elif command == "GET":
            todo_id = int(params.strip())
            found = next((t for t in todos if t["id"] == todo_id), None)
            if found:
                return f"Todo #{found['id']}: {found['title']}\nDescription: {found['description'] or 'None'}\nStatus: {'Completed' if found['completed'] else 'Not completed'}"
            else:
                return f"Todo #{todo_id} not found."
                
        elif command == "UNKNOWN":
            return f"I'm not sure what you want to do. Claude says: {params}"
        
        return "Something went wrong interpreting your command."

def main():
    print("="*50)
    print("Todo Assistant with Claude MCP Integration")
    print("="*50)
    print("Make sure:")
    print("1. Your FastAPI Todo app is running on http://localhost:8000")
    print("2. Claude Desktop is running with MCP enabled on port 8080")
    print("="*50)
    
    assistant = ClaudeMCPTodoAssistant()
    
    # Test connection to Claude MCP
    print("Testing connection to Claude...")
    test_response = assistant.send_to_claude("Hello, are you there?")
    if test_response:
        print("Successfully connected to Claude Desktop via MCP!")
    else:
        print("Could not connect to Claude Desktop. Please make sure it's running with MCP enabled.")
        return
    
    # Test connection to Todo API
    print("Testing connection to Todo API...")
    try:
        todos = assistant.get_todos()
        print(f"Successfully connected to Todo API! Found {len(todos)} todos.")
    except Exception as e:
        print(f"Could not connect to Todo API: {e}")
        print("Please make sure your FastAPI application is running.")
        return
    
    print("\nYou can now use natural language to manage your todos!")
    print("Examples:")
    print("  - Add a new todo to buy milk")
    print("  - Mark todo #1 as complete")
    print("  - Update the description of todo #2 to high priority")
    print("  - Delete todo #3")
    print("  - Show all my todos")
    print("  - What's on my todo list?")
    print("\nType 'exit' to quit.")
    print("-"*50)
    
    while True:
        user_input = input("\nWhat would you like to do? > ")
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        response = assistant.interpret_command(user_input)
        print("\n" + response)

if __name__ == "__main__":
    main()
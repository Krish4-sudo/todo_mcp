from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import httpx
import json
import os
import sqlite3
from datetime import datetime

load_dotenv()
mcp = FastMCP("todos")

# Database setup
def init_db():
    conn = sqlite3.connect("todos.db")
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

@mcp.tool()
async def add_todo(title: str, description: str = ""):
    """
    Add a new todo item to the database.
    Args:
        title: The title of the todo item
        description: Optional description of the todo item
    Returns:
        Dictionary with the created todo information
    """
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect("todos.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO todos (title, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, description, now, now)
    )
    todo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": todo_id,
        "title": title,
        "description": description,
        "status": "pending",
        "created_at": now,
        "updated_at": now
    }

@mcp.tool()
async def list_todos(status: str = None):
    """
    List all todos, optionally filtered by status.
    Args:
        status: Optional filter by status ('pending', 'completed')
    Returns:
        List of todo items
    """
    conn = sqlite3.connect("todos.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status:
        cursor.execute("SELECT * FROM todos WHERE status = ?", (status,))
    else:
        cursor.execute("SELECT * FROM todos")
        
    rows = cursor.fetchall()
    todos = [dict(row) for row in rows]
    conn.close()
    
    return todos

@mcp.tool()
async def get_todo(todo_id: int):
    """
    Get a specific todo by ID.
    Args:
        todo_id: The ID of the todo to retrieve
    Returns:
        Todo item details or error message if not found
    """
    conn = sqlite3.connect("todos.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"error": f"Todo with ID {todo_id} not found"}
    
    return dict(row)

@mcp.tool()
async def update_todo(todo_id: int, title: str = None, description: str = None, status: str = None):
    """
    Update an existing todo.
    Args:
        todo_id: The ID of the todo to update
        title: Optional new title
        description: Optional new description
        status: Optional new status ('pending', 'completed')
    Returns:
        Updated todo information or error message
    """
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect("todos.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # First check if todo exists
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    todo = cursor.fetchone()
    
    if not todo:
        conn.close()
        return {"error": f"Todo with ID {todo_id} not found"}
    
    # Prepare update fields
    todo_dict = dict(todo)
    updates = {}
    
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if status is not None:
        if status not in ["pending", "completed"]:
            conn.close()
            return {"error": "Status must be either 'pending' or 'completed'"}
        updates["status"] = status
    
    updates["updated_at"] = now
    
    # Construct update query
    if not updates:
        conn.close()
        return {"error": "No updates provided"}
    
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(todo_id)
    
    cursor.execute(f"UPDATE todos SET {set_clause} WHERE id = ?", values)
    conn.commit()
    
    # Get updated todo
    cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
    updated_todo = cursor.fetchone()
    conn.close()
    
    return dict(updated_todo)

@mcp.tool()
async def delete_todo(todo_id: int):
    """
    Delete a todo by ID.
    Args:
        todo_id: The ID of the todo to delete
    Returns:
        Success message or error message
    """
    conn = sqlite3.connect("todos.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM todos WHERE id = ?", (todo_id,))
    todo = cursor.fetchone()
    
    if not todo:
        conn.close()
        return {"error": f"Todo with ID {todo_id} not found"}
    
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"Todo with ID {todo_id} deleted"}

if __name__ == "__main__":
    mcp.run(transport="stdio")

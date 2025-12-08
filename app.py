import pyodbc
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time

import os

# Fetch the connection string from the environment variable
connection_string = "Driver={ODBC Driver 18 for SQL Server};Server=tcp:blib-sqlserver.database.windows.net,1433;Database=blib-db;Uid=tani;Pwd=Sql@Admin#8974;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# Check if the connection string is available
if connection_string:
    print(f"Connection String: {connection_string}")
else:
    print("Connection string not found in environment variables.")
    
app = FastAPI()
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])

@app.middleware("http")
async def prometheus_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(request.method, request.url.path).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(duration)

    return response

# Configure CORSMiddleware to allow all origins (disable CORS for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This allows all origins (use '*' for development only)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define the Task model
class Task(BaseModel):
    title: str
    description: str

# Create a table for tasks (You can run this once outside of the app)
@app.get("/")
def create_tasks_table():
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE Tasks (
                ID int NOT NULL PRIMARY KEY IDENTITY,
                Title varchar(255),
                Description text
            );
        """)
        conn.commit() 
        return "Get Tasks API Ready."       
    except Exception as e:
        print(e)
        if "There is already an object named 'Tasks' in the database." in str(e):
            return "Get Tasks API Ready."
        else:
            return "Error. Please check Logs."

# List all tasks
@app.get("/tasks")
def get_tasks():
    tasks = []
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks")
        for row in cursor.fetchall():
            task = {
                "ID": row.ID,
                "Title": row.Title,
                "Description": row.Description
            }
            tasks.append(task)
    return tasks

# Retrieve a single task by ID
@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks WHERE ID = ?", task_id)
        row = cursor.fetchone()
        if row:
            task = {
                "ID": row.ID,
                "Title": row.Title,
                "Description": row.Description
            }
            return task
        return {"message": "Task not found"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    create_tasks_table()

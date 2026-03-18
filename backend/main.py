"""
QueryViz Backend — FastAPI Application
POST /api/query → NL → SQL → JSON response with chart config
POST /api/upload → CSV upload and schema inference
Includes error handling, clarification, conversation context, and fallback systems.
"""
from __future__ import annotations


import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, execute_query, get_connection
from llm_engine import generate_sql, determine_chart_type
from csv_handler import upload_csv, get_dataset, list_datasets, delete_dataset
from conversation_manager import create_conversation, add_to_context, get_context
from insight_generator import generate_insight

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- Lifespan: load DB on startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[STARTUP] Loading dataset into SQLite...")
    init_db()
    logger.info("[STARTUP] Ready.")
    yield
    logger.info("[SHUTDOWN] Goodbye.")


app = FastAPI(title="QueryViz API", version="1.0.0", lifespan=lifespan)

# CORS — allow all for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response Models ---
class QueryRequest(BaseModel):
    query: str
    dataset_id: str | None = None
    conversation_id: str | None = None


class QueryResponse(BaseModel):
    sql: str | None
    data: list[dict]
    columns: list[str]
    chart_type: str
    error: str | None = None
    execution_time: int
    suggested_columns: list[str] | None = None
    needs_clarification: bool = False
    clarification: str | None = None
    conversation_id: str
    context_used: bool = False
    insight: str | None = None


class UploadResponse(BaseModel):
    dataset_id: str
    filename: str
    columns: list[str]
    row_count: int
    preview: list[dict]


class DatasetListResponse(BaseModel):
    datasets: list[dict]


# --- Health Check ---
@app.get("/health")
def health():
    return {"status": "ok", "service": "queryviz-api"}


# --- Main Query Endpoint ---
@app.post("/api/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    start = time.time()
    
    conversation_id = create_conversation(req.conversation_id)
    logger.info(f"Query: {req.query} (dataset={req.dataset_id}, conv={conversation_id})")

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if len(req.query) > 1000:
        raise HTTPException(status_code=400, detail="Query exceeds 1000 character limit.")

    context = get_context(conversation_id)
    
    try:
        llm_result = generate_sql(req.query, dataset_id=req.dataset_id, conversation_context=context)
    except Exception as e:
        logger.error(f"LLM failed: {str(e)}")
        elapsed = int((time.time() - start) * 1000)
        return QueryResponse(
            sql=None, data=[], columns=[], chart_type="kpi",
            execution_time=elapsed, error="Service unavailable.",
            conversation_id=conversation_id
        )
    
    if llm_result.get("needs_clarification"):
        elapsed = int((time.time() - start) * 1000)
        return QueryResponse(
            sql=None, data=[], columns=[], chart_type="kpi",
            execution_time=elapsed, needs_clarification=True,
            clarification=llm_result["clarification"],
            conversation_id=conversation_id,
            context_used=llm_result.get("context_used", False)
        )

    if llm_result["error"]:
        elapsed = int((time.time() - start) * 1000)
        return QueryResponse(
            sql=None, data=[], columns=[], chart_type="kpi",
            execution_time=elapsed, error=llm_result["error"],
            suggested_columns=llm_result.get("suggested_columns"),
            conversation_id=conversation_id,
            context_used=llm_result.get("context_used", False)
        )

    sql = llm_result["sql"]
    context_used = llm_result.get("context_used", False)

    try:
        result = execute_query(sql)
    except ValueError as e:
        elapsed = int((time.time() - start) * 1000)
        return QueryResponse(
            sql=sql, data=[], columns=[], chart_type="kpi",
            execution_time=elapsed, error=f"Blocked: {str(e)}",
            conversation_id=conversation_id, context_used=context_used
        )
    except Exception as e:
        try:
            retry_result = generate_sql(req.query, error_context=str(e), dataset_id=req.dataset_id, conversation_context=context)
        except Exception:
            logger.error("Retry SQL generation also failed")
            elapsed = int((time.time() - start) * 1000)
            return QueryResponse(
                sql=sql, data=[], columns=[], chart_type="kpi",
                execution_time=elapsed, error=f"Failed: {str(e)}",
                conversation_id=conversation_id, context_used=context_used
            )
        
        if retry_result["error"] or not retry_result["sql"]:
            elapsed = int((time.time() - start) * 1000)
            return QueryResponse(
                sql=sql, data=[], columns=[], chart_type="kpi",
                execution_time=elapsed, error=f"Failed: {str(e)}",
                conversation_id=conversation_id, context_used=context_used
            )

        try:
            sql = retry_result["sql"]
            result = execute_query(sql)
        except Exception as e2:
            elapsed = int((time.time() - start) * 1000)
            return QueryResponse(
                sql=sql, data=[], columns=[], chart_type="kpi",
                execution_time=elapsed, error=f"Failed: {str(e2)}",
                conversation_id=conversation_id, context_used=context_used
            )

    try:
        chart_type = determine_chart_type(req.query, sql, result["columns"], result["row_count"])
    except Exception as chart_err:
        logger.warning(f"Chart type detection failed: {chart_err}")
        chart_type = "bar"
    
    insight = generate_insight(result["data"], result["columns"], chart_type)
    
    add_to_context(conversation_id, req.query, sql, result["data"], result["columns"], chart_type)

    elapsed = int((time.time() - start) * 1000)
    return QueryResponse(
        sql=sql, data=result["data"], columns=result["columns"],
        chart_type=chart_type, execution_time=elapsed,
        conversation_id=conversation_id, context_used=context_used,
        insight=insight
    )


# --- CSV Upload Endpoint ---
@app.post("/api/upload", response_model=UploadResponse)
async def upload_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
    
    try:
        content = await file.read()
        conn = get_connection()
        result = upload_csv(content, file.filename, conn)
        return UploadResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Upload failed")


@app.get("/api/datasets", response_model=DatasetListResponse)
def list_datasets_endpoint():
    return DatasetListResponse(datasets=list_datasets())


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset_endpoint(dataset_id: str):
    if not delete_dataset(dataset_id, get_connection()):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Deleted"}

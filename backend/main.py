import os
import json
import asyncio
import hashlib
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, create_engine, Session, select
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Import Google GenAI SDK
from google import genai
from google.genai import types

# Import TTE Security
from tte_security import tte_vault

load_dotenv()

app = FastAPI(title="AI Data Intelligence Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing. Please set it in your .env file.")

client = genai.Client(api_key=api_key)

# ---------------- DATABASE MODELS ----------------
class Workflow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    prompt: str
    search_query: str
    target_schema: str  # JSON String
    status: str = "PLANNED"  # PLANNED, RUNNING, COMPLETED

class ExtractedRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int
    source_url: str
    data_json: str
    content_hash: str

engine = create_engine("sqlite:///data_intelligence.db", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session

# Global memory queue for broadcasting SSE logs to frontend
execution_logs = {}

# ---------------- API ENDPOINTS ----------------
class PlanRequest(BaseModel):
    prompt: str

@app.post("/api/plan")
def plan_workflow(req: PlanRequest, db: Session = Depends(get_db)):
    """Convert natural language to search query and JSON extraction schema using Gemini + TTE."""
    
    # 1. TTE Protection: Redact PII / Secrets before sending to LLM
    secured_prompt, enclave_mappings = tte_vault.secure_payload(req.prompt)

    system_instruction = """
    You are an AI Data Engine operating inside a secure TTE wrapper.
    Given a user request, return a JSON object containing:
    1. "search_query": The best web search query to find this information.
    2. "target_schema": An array of key-value pairs representing data fields to extract.
    CRITICAL: Preserve any [SECURE_*] tokens exactly as written in your response.
    """
    
    # 2. Gemini API Call
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=secured_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json"
        ),
    )
    
    raw_plan_json = response.text

    # 3. TTE Restore: Re-hydrate tokens back into user prompt context locally
    hydrated_plan_str = tte_vault.restore_payload(raw_plan_json, enclave_mappings)
    plan = json.loads(hydrated_plan_str)
    
    workflow = Workflow(
        prompt=req.prompt,
        search_query=plan.get("search_query", req.prompt),
        target_schema=json.dumps(plan.get("target_schema", []))
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    return {
        "workflow_id": workflow.id, 
        "plan": plan,
        "tte_secured": True,
        "tokens_protected": len(enclave_mappings)
    }

async def run_pipeline(workflow_id: int):
    execution_logs[workflow_id] = []
    
    def log(msg: str):
        execution_logs[workflow_id].append(msg)
    
    with Session(engine) as db:
        wf = db.get(Workflow, workflow_id)
        wf.status = "RUNNING"
        db.add(wf)
        db.commit()
        
        log(f"Searching web for query: '{wf.search_query}'...")
        
        # Step 1: Discover URLs
        urls = []
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(wf.search_query, max_results=3))
                urls = [r["href"] for r in results if "href" in r]
            log(f"Discovered {len(urls)} target sources.")
        except Exception as e:
            log(f"Search warning: {str(e)}. Proceeding with direct extraction.")
        
        schema = json.loads(wf.target_schema)
        
        # Step 2: Scrape & Extract
        for url in urls:
            log(f"Scraping & parsing: {url[:50]}...")
            try:
                async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client_http:
                    resp = await client_http.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Strip non-text
                    for s in soup(['script', 'style', 'nav', 'footer']):
                        s.decompose()
                    clean_text = soup.get_text(separator=' ', strip=True)[:3500]

                log(f"Extracting schema attributes using Gemini 2.5...")
                
                # Apply TTE Vault on scraped page text before passing to Gemini
                secured_text, enclave_mappings = tte_vault.secure_payload(clean_text)

                extract_prompt = f"""
                Extract records from the following text based on this schema specification:
                Schema: {json.dumps(schema)}
                Text: {secured_text}
                
                Return JSON format: {{"records": [{{"field": "val"}}]}}
                """
                
                ai_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=extract_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                hydrated_records_str = tte_vault.restore_payload(ai_res.text, enclave_mappings)
                records = json.loads(hydrated_records_str).get("records", [])
                
                # Step 3: Deduplicate & Store
                added_count = 0
                for record in records:
                    record_str = json.dumps(record, sort_keys=True)
                    record_hash = hashlib.md5(record_str.encode('utf-8')).hexdigest()
                    
                    # Deduplication query
                    dup = db.exec(
                        select(ExtractedRecord)
                        .where(ExtractedRecord.workflow_id == workflow_id)
                        .where(ExtractedRecord.content_hash == record_hash)
                    ).first()
                    
                    if not dup:
                        rec = ExtractedRecord(
                            workflow_id=workflow_id,
                            source_url=url,
                            data_json=record_str,
                            content_hash=record_hash
                        )
                        db.add(rec)
                        added_count += 1
                        
                db.commit()
                log(f"Extracted {added_count} unique structured items from source.")
            except Exception as err:
                log(f"Error scraping {url}: {str(err)}")

        wf.status = "COMPLETED"
        db.add(wf)
        db.commit()
        log("Execution pipeline finished successfully!")

@app.post("/api/workflows/{workflow_id}/execute")
def execute_workflow(workflow_id: int, bg_tasks: BackgroundTasks):
    bg_tasks.add_task(run_pipeline, workflow_id)
    return {"status": "Execution started"}

@app.get("/api/workflows/{workflow_id}/stream")
async def stream_logs(workflow_id: int):
    """Server-Sent Events (SSE) log streamer."""
    async def event_generator():
        sent_index = 0
        while True:
            logs = execution_logs.get(workflow_id, [])
            if sent_index < len(logs):
                for i in range(sent_index, len(logs)):
                    yield f"data: {logs[i]}\n\n"
                sent_index = len(logs)
                if logs and logs[-1] == "Execution pipeline finished successfully!":
                    break
            await asyncio.sleep(0.5)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/workflows/{workflow_id}/results")
def get_results(workflow_id: int, db: Session = Depends(get_db)):
    records = db.exec(select(ExtractedRecord).where(ExtractedRecord.workflow_id == workflow_id)).all()
    parsed = []
    for r in records:
        data = json.loads(r.data_json)
        data["_source_url"] = r.source_url
        parsed.append(data)
    return {"results": parsed}
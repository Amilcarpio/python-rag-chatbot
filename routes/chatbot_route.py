from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
import time

from database.connection import get_db
from services.guardrails_service import GuardrailsService
from services.retrieval_service import RetrievalService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.observability_service import ObservabilityService

router = APIRouter(prefix="/chat", tags=["chatbot"])

observability = ObservabilityService()

class ChatRequest(BaseModel):

    question: str
    top_k: Optional[int] = None

class Source(BaseModel):

    document: str
    excerpt: str
    similarity: float

class Metrics(BaseModel):

    total_latency: float
    retrieval_latency: float
    llm_latency: float
    total_tokens: int
    cost: float
    chunks_retrieved: int

class ChatResponse(BaseModel):

    answer: str
    citations: List[Source]
    metrics: Optional[Metrics] = None

@router.post("/ask", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    tracking_context = observability.start_query(request.question)

    try:
        start = time.time()
        guardrails = GuardrailsService()
        validation = guardrails.validate_query(request.question)
        observability.record_stage(tracking_context, 'guardrails', time.time() - start)

        if not validation['is_valid']:
            guardrails.log_violation(
                request.question,
                validation['violations'],
                validation['severity']
            )

            return ChatResponse(
                answer=validation['message'],
                citations=[],
                metrics=None
            )

        start = time.time()
        retrieval_service = RetrievalService(db)
        retrieval_data = retrieval_service.retrieve_with_metadata(
            query=request.question,
            top_k=request.top_k
        )
        retrieval_latency = time.time() - start
        observability.record_stage(
            tracking_context,
            'retrieval',
            retrieval_latency,
            metadata=retrieval_data
        )

        retrieval_results = retrieval_data['results']

        if not retrieval_results:
            return ChatResponse(
                answer="I could not find relevant information in the available documents to answer your question. Please try reformulating or asking another question about the attached documents.",
                citations=[],
                metrics=None
            )

        prompt_service = PromptService()
        messages = prompt_service.create_conversation_prompt(
            question=request.question,
            retrieval_results=retrieval_results
        )

        llm_service = LLMService()
        llm_response = llm_service.generate_response(messages)

        metrics_data = observability.finish_query(
            context=tracking_context,
            answer=llm_response['answer'],
            retrieval_results=retrieval_results,
            llm_response=llm_response,
            guardrails_result=validation
        )

        sanitized_answer = guardrails.sanitize_response(llm_response['answer'])

        seen_citations = set()
        citations = []
        for r in retrieval_results:
            excerpt = r['content'][:500] + "..." if len(r['content']) > 500 else r['content']
            citation_key = (r['document'].original_filename, excerpt[:100])
            
            if citation_key not in seen_citations:
                seen_citations.add(citation_key)
                citations.append(
                    Source(
                        document=r['document'].original_filename,
                        excerpt=excerpt,
                        similarity=r['similarity']
                    )
                )

        metrics = Metrics(
            total_latency=metrics_data.total_latency,
            retrieval_latency=metrics_data.retrieval_latency,
            llm_latency=metrics_data.llm_latency,
            total_tokens=metrics_data.total_tokens,
            cost=metrics_data.total_cost,
            chunks_retrieved=metrics_data.chunks_retrieved
        )

        return ChatResponse(
            answer=sanitized_answer,
            citations=citations,
            metrics=metrics
        )

    except Exception as e:
        print(f"Erro no pipeline: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing question: {str(e)}"
        )

@router.get("/metrics")
async def get_metrics(last_n: Optional[int] = None):

    stats = observability.get_statistics(last_n=last_n)
    return {
        "success": True,
        "statistics": stats
    }

@router.get("/metrics/recent")
async def get_recent_queries(n: int = 10):

    recent = observability.get_recent_queries(n=n)
    return {
        "success": True,
        "recent_queries": recent
    }

@router.get("/metrics/bottlenecks")
async def get_bottlenecks():

    analysis = observability.identify_bottlenecks()
    return {
        "success": True,
        "analysis": analysis
    }

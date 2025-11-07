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
    conversation_id: str = ""
    top_k: Optional[int] = None

class Source(BaseModel):

    id: int
    filename: str
    file_type: str
    similarity: float
    chunk_index: int

class Metrics(BaseModel):

    total_latency: float
    retrieval_latency: float
    llm_latency: float
    total_tokens: int
    cost: float
    chunks_retrieved: int

class ChatResponse(BaseModel):

    answer: str
    sources: List[Source]
    conversation_id: str
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
                sources=[],
                conversation_id=request.conversation_id or "default"
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
                answer="Não encontrei informações relevantes nos documentos disponíveis para responder sua pergunta. Por favor, tente reformular ou fazer outra pergunta sobre os documentos anexados.",
                sources=[],
                conversation_id=request.conversation_id or "default"
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

        sources = [
            Source(
                id=i,
                filename=r['document'].filename,
                file_type=r['document'].file_type,
                similarity=r['similarity'],
                chunk_index=r['chunk_index']
            )
            for i, r in enumerate(retrieval_results, 1)
        ]

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
            sources=sources,
            conversation_id=request.conversation_id or "default",
            metrics=metrics
        )

    except Exception as e:
        print(f"Erro no pipeline: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar pergunta: {str(e)}"
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

import time
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from core.logging_config import get_logger

logger = get_logger("observability")

@dataclass
class QueryMetrics:

    timestamp: str
    question: str

    guardrails_latency: float = 0.0
    retrieval_latency: float = 0.0
    llm_latency: float = 0.0
    total_latency: float = 0.0

    query_tokens: int = 0
    context_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    retrieval_cost: float = 0.0
    llm_cost: float = 0.0
    total_cost: float = 0.0

    chunks_retrieved: int = 0
    avg_similarity: float = 0.0

    success: bool = True
    error: Optional[str] = None

    guardrails_passed: bool = True
    guardrails_violations: Optional[List[str]] = None

    def __post_init__(self):
        if self.guardrails_violations is None:
            self.guardrails_violations = []

class ObservabilityService:

    def __init__(self):
        self.metrics_history: List[QueryMetrics] = []

    def start_query(self, question: str) -> Dict:

        logger.info(
            f"Starting query tracking",
            extra={
                'question_preview': question[:100],
                'question_length': len(question)
            }
        )

        return {
            'question': question,
            'start_time': time.time(),
            'timestamp': datetime.now().isoformat(),
            'stage_times': {}
        }

    def record_stage(
        self,
        context: Dict,
        stage: str,
        duration: float,
        metadata: Optional[Dict] = None
    ):

        logger.debug(
            f"Stage completed: {stage}",
            extra={
                'stage': stage,
                'duration': round(duration, 3),
                'metadata': metadata
            }
        )

        context['stage_times'][stage] = duration
        if metadata:
            context[f'{stage}_metadata'] = metadata

    def finish_query(
        self,
        context: Dict,
        answer: str,
        retrieval_results: List[Dict],
        llm_response: Dict,
        guardrails_result: Dict
    ) -> QueryMetrics:

        total_time = time.time() - context['start_time']

        chunks_retrieved = len(retrieval_results)
        avg_similarity = (
            sum(r.get('similarity', 0) for r in retrieval_results) / chunks_retrieved
            if chunks_retrieved > 0 else 0.0
        )

        logger.info(
            f"Query completed",
            extra={
                'total_latency': round(total_time, 3),
                'chunks_retrieved': chunks_retrieved,
                'avg_similarity': round(avg_similarity, 3),
                'llm_cost': llm_response.get('cost', 0),
                'success': 'error' not in llm_response,
                'guardrails_passed': guardrails_result.get('is_valid', True)
            }
        )

        metrics = QueryMetrics(
            timestamp=context['timestamp'],
            question=context['question'],

            guardrails_latency=context['stage_times'].get('guardrails', 0),
            retrieval_latency=context['stage_times'].get('retrieval', 0),
            llm_latency=llm_response.get('latency', 0),
            total_latency=round(total_time, 2),

            query_tokens=context.get('retrieval_metadata', {}).get('query_tokens', 0),
            context_tokens=context.get('retrieval_metadata', {}).get('context_tokens', 0),
            prompt_tokens=llm_response.get('usage', {}).get('prompt_tokens', 0),
            completion_tokens=llm_response.get('usage', {}).get('completion_tokens', 0),
            total_tokens=llm_response.get('usage', {}).get('total_tokens', 0),

            retrieval_cost=0.0,
            llm_cost=llm_response.get('cost', 0),
            total_cost=llm_response.get('cost', 0),

            chunks_retrieved=chunks_retrieved,
            avg_similarity=round(avg_similarity, 3),

            success='error' not in llm_response,
            error=llm_response.get('error'),

            guardrails_passed=guardrails_result.get('is_valid', True),
            guardrails_violations=guardrails_result.get('violations', [])
        )

        self.metrics_history.append(metrics)

        return metrics

    def get_statistics(self, last_n: Optional[int] = None) -> Dict:

        if not self.metrics_history:
            return {
                'total_queries': 0,
                'message': 'No metrics recorded yet'
            }

        metrics = self.metrics_history[-last_n:] if last_n else self.metrics_history

        total = len(metrics)
        successful = sum(1 for m in metrics if m.success)
        failed = total - successful

        avg_total_latency = sum(m.total_latency for m in metrics) / total
        avg_llm_latency = sum(m.llm_latency for m in metrics) / total
        avg_retrieval_latency = sum(m.retrieval_latency for m in metrics) / total

        total_tokens = sum(m.total_tokens for m in metrics)
        avg_tokens = total_tokens / total

        total_cost = sum(m.total_cost for m in metrics)
        avg_cost = total_cost / total

        avg_chunks = sum(m.chunks_retrieved for m in metrics) / total
        avg_similarity = sum(m.avg_similarity for m in metrics) / total

        guardrails_violations = sum(1 for m in metrics if not m.guardrails_passed)

        return {
            'total_queries': total,
            'successful_queries': successful,
            'failed_queries': failed,
            'success_rate': round(successful / total * 100, 2),

            'latency': {
                'avg_total': round(avg_total_latency, 2),
                'avg_llm': round(avg_llm_latency, 2),
                'avg_retrieval': round(avg_retrieval_latency, 2),
                'min_total': min(m.total_latency for m in metrics),
                'max_total': max(m.total_latency for m in metrics)
            },

            'tokens': {
                'total': total_tokens,
                'avg_per_query': round(avg_tokens, 0),
                'avg_prompt': round(sum(m.prompt_tokens for m in metrics) / total, 0),
                'avg_completion': round(sum(m.completion_tokens for m in metrics) / total, 0)
            },

            'cost': {
                'total': round(total_cost, 4),
                'avg_per_query': round(avg_cost, 6),
                'estimated_per_1k_queries': round(avg_cost * 1000, 2)
            },

            'retrieval': {
                'avg_chunks_retrieved': round(avg_chunks, 1),
                'avg_similarity': round(avg_similarity, 3)
            },

            'guardrails': {
                'violations': guardrails_violations,
                'violation_rate': round(guardrails_violations / total * 100, 2)
            }
        }

    def get_recent_queries(self, n: int = 10) -> List[Dict]:

        recent = self.metrics_history[-n:]
        return [asdict(m) for m in recent]

    def identify_bottlenecks(self) -> Dict:

        if not self.metrics_history:
            return {'message': 'Dados insuficientes'}

        metrics = self.metrics_history

        avg_total = sum(m.total_latency for m in metrics) / len(metrics)
        avg_guardrails = sum(m.guardrails_latency for m in metrics) / len(metrics)
        avg_retrieval = sum(m.retrieval_latency for m in metrics) / len(metrics)
        avg_llm = sum(m.llm_latency for m in metrics) / len(metrics)

        breakdown = {
            'guardrails': round(avg_guardrails / avg_total * 100, 1),
            'retrieval': round(avg_retrieval / avg_total * 100, 1),
            'llm': round(avg_llm / avg_total * 100, 1)
        }

        bottleneck = max(breakdown.items(), key=lambda x: x[1])[0] if breakdown else "unknown"

        return {
            'average_latencies': {
                'total': round(avg_total, 2),
                'guardrails': round(avg_guardrails, 2),
                'retrieval': round(avg_retrieval, 2),
                'llm': round(avg_llm, 2)
            },
            'time_breakdown_percent': breakdown,
            'primary_bottleneck': bottleneck,
            'recommendation': self._get_bottleneck_recommendation(bottleneck)
        }

    def _get_bottleneck_recommendation(self, bottleneck: str) -> str:

        recommendations = {
            'guardrails': 'Optimize regex patterns or consider validation cache',
            'retrieval': 'Optimize pgvector indices or reduce top_k',
            'llm': 'Consider faster model or implement response cache'
        }
        return recommendations.get(bottleneck, 'No specific recommendation')

    def export_metrics(self) -> List[Dict]:

        return [asdict(m) for m in self.metrics_history]

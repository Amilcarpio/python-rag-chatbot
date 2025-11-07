import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable
import logging

from core.logging_config import get_logger

logger = get_logger("http_middleware")

class RequestLoggingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get('X-Request-ID', f"req_{int(time.time() * 1000)}")
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            f"Request started: {method} {url}",
            extra={
                'request_id': request_id,
                'method': method,
                'url': url,
                'path': request.url.path,
                'client': client_host,
                'user_agent': request.headers.get('user-agent', 'unknown')
            }
        )

        request.state.request_id = request_id

        start_time = time.time()

        try:
            response = await call_next(request)

            latency = time.time() - start_time

            logger.info(
                f"Request completed: {method} {url} - Status: {response.status_code}",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'url': url,
                    'status_code': response.status_code,
                    'latency': round(latency, 3),
                    'client': client_host
                }
            )

            response.headers['X-Request-ID'] = request_id
            response.headers['X-Response-Time'] = f"{latency:.3f}s"

            return response

        except Exception as e:
            latency = time.time() - start_time

            logger.error(
                f"Request failed: {method} {url} - Error: {str(e)}",
                extra={
                    'request_id': request_id,
                    'method': method,
                    'url': url,
                    'latency': round(latency, 3),
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'client': client_host
                },
                exc_info=True
            )

            raise

class MetricsMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = {
            'total_requests': 0,
            'total_errors': 0,
            'total_latency': 0.0,
            'endpoints': {}
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        self.metrics['total_requests'] += 1

        start_time = time.time()

        try:
            response = await call_next(request)
            latency = time.time() - start_time

            self.metrics['total_latency'] += latency

            endpoint = request.url.path
            if endpoint not in self.metrics['endpoints']:
                self.metrics['endpoints'][endpoint] = {
                    'count': 0,
                    'total_latency': 0.0,
                    'errors': 0
                }

            self.metrics['endpoints'][endpoint]['count'] += 1
            self.metrics['endpoints'][endpoint]['total_latency'] += latency

            if response.status_code >= 400:
                self.metrics['total_errors'] += 1
                self.metrics['endpoints'][endpoint]['errors'] += 1

            return response

        except Exception as e:
            self.metrics['total_errors'] += 1

            endpoint = request.url.path
            if endpoint in self.metrics['endpoints']:
                self.metrics['endpoints'][endpoint]['errors'] += 1

            raise

    def get_metrics(self) -> dict:

        if self.metrics['total_requests'] == 0:
            return {
                'total_requests': 0,
                'avg_latency': 0.0,
                'error_rate': 0.0,
                'endpoints': {}
            }

        avg_latency = self.metrics['total_latency'] / self.metrics['total_requests']
        error_rate = (self.metrics['total_errors'] / self.metrics['total_requests']) * 100

        endpoint_metrics = {}
        for endpoint, data in self.metrics['endpoints'].items():
            if data['count'] > 0:
                endpoint_metrics[endpoint] = {
                    'count': data['count'],
                    'avg_latency': round(data['total_latency'] / data['count'], 3),
                    'errors': data['errors'],
                    'error_rate': round((data['errors'] / data['count']) * 100, 2)
                }

        return {
            'total_requests': self.metrics['total_requests'],
            'total_errors': self.metrics['total_errors'],
            'avg_latency': round(avg_latency, 3),
            'error_rate': round(error_rate, 2),
            'endpoints': endpoint_metrics
        }

metrics_collector = None

def get_metrics_collector():

    return metrics_collector

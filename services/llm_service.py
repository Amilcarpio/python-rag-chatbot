import time
from typing import Dict, List, Optional, Generator, Any, cast
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import tiktoken

from core.config import settings

class LLMService:

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.MAX_TOKENS

        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def _is_gpt5_model(self, model: Optional[str] = None) -> bool:
        """
        Check if the model is a GPT-5 model that requires max_completion_tokens
        and only supports temperature=1
        """
        model_name = (model or self.model).lower()
        return "gpt-5" in model_name
    
    def _get_completion_params(
        self,
        token_limit: int,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the appropriate completion parameters based on the model type.
        
        GPT-5 models require:
        - max_completion_tokens instead of max_tokens
        - temperature=1 (fixed, cannot be changed)
        
        Other models (GPT-4.1, GPT-3.5, etc.) use:
        - max_tokens
        - temperature configurable
        """
        is_gpt5 = self._is_gpt5_model(model)
        
        params = {}
        
        if is_gpt5:
            params["temperature"] = 1.0
            params["max_completion_tokens"] = token_limit
        else:
            params["max_tokens"] = token_limit
            params["temperature"] = temperature or self.temperature
        
        return params

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:

        start_time = time.time()

        try:
            typed_messages = cast(List[ChatCompletionMessageParam], messages)
            token_limit = max_tokens or self.max_tokens
            
            create_params = {
                "model": self.model,
                "messages": typed_messages,
            }

            completion_params = self._get_completion_params(
                token_limit=token_limit,
                temperature=temperature,
                model=self.model
            )
            create_params.update(completion_params)
            
            response = self.client.chat.completions.create(**create_params)

            latency = time.time() - start_time

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message

            answer = message.content if message.content is not None else ""

            if not answer and response.usage and response.usage.completion_tokens > 0:
                from core.logging_config import get_logger
                logger = get_logger("llm_service")
                logger.warning(
                    f"Empty answer but {response.usage.completion_tokens} completion tokens generated. "
                    f"Finish reason: {finish_reason}, Model: {self.model}"
                )

            usage = {
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                'total_tokens': response.usage.total_tokens if response.usage else 0
            }

            cost = self._calculate_cost(
                usage['prompt_tokens'],
                usage['completion_tokens']
            )

            return {
                'answer': answer,
                'usage': usage,
                'cost': cost,
                'latency': round(latency, 2),
                'model': self.model,
                'finish_reason': response.choices[0].finish_reason
            }

        except Exception as e:
            return {
                'answer': f"Error generating response: {str(e)}",
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                'cost': 0.0,
                'latency': time.time() - start_time,
                'model': self.model,
                'error': str(e)
            }

    def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:

        try:
            typed_messages = cast(List[ChatCompletionMessageParam], messages)
            token_limit = max_tokens or self.max_tokens
            
            create_params = {
                "model": self.model,
                "messages": typed_messages,
                "stream": True
            }
            
            completion_params = self._get_completion_params(
                token_limit=token_limit,
                temperature=temperature,
                model=self.model
            )
            create_params.update(completion_params)
            
            stream = self.client.chat.completions.create(**create_params)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Erro no streaming: {str(e)}"

    def count_tokens(self, text: str) -> int:

        return len(self.encoding.encode(text))

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:

        tokens_per_message = 3
        tokens_per_name = 1

        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(str(value)))
                if key == "name":
                    num_tokens += tokens_per_name

        num_tokens += 3
        return num_tokens

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:

        if "gpt-4" in self.model:
            input_cost = (prompt_tokens / 1000) * 0.03
            output_cost = (completion_tokens / 1000) * 0.06
        else:
            input_cost = (prompt_tokens / 1000) * 0.0005
            output_cost = (completion_tokens / 1000) * 0.0015

        return round(input_cost + output_cost, 6)

    def validate_model(self) -> bool:

        try:
            create_params = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
            }

            completion_params = self._get_completion_params(
                token_limit=5,
                temperature=None,
                model=self.model
            )
            create_params.update(completion_params)
            
            response = self.client.chat.completions.create(**create_params)
            return True
        except Exception as e:
            print(f"Erro ao validar modelo: {e}")
            return False

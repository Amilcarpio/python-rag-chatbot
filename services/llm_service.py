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

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:

        start_time = time.time()

        try:
            typed_messages = cast(List[ChatCompletionMessageParam], messages)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=typed_messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            latency = time.time() - start_time

            answer = response.choices[0].message.content or ""

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
                'answer': f"Erro ao gerar resposta: {str(e)}",
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
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=typed_messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True
            )

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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"Erro ao validar modelo: {e}")
            return False

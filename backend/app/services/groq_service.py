# Groq Service for LLM Generation
import os
import logging
from typing import Optional, List

from app.config import settings


class GroqService:
    """
    Groq API client for LLM text generation.
    Uses open-weight models: llama-3.1-70b, llama-3.1-8b, mixtral-8x7b.
    """
    
    # Model configuration - prefer larger models, fallback to smaller
    PRIMARY_MODEL = "llama-3.1-70b-versatile"
    FALLBACK_MODELS = ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    
    def __init__(self):
        self.logger = logging.getLogger("groq_service")
        self.api_key = settings.groq_api_key
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self._client = None
        self._current_model = self.PRIMARY_MODEL

    
    def _get_client(self):
        """Lazy load the Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                self.logger.error("groq package not installed. Run: pip install groq")
                raise
        return self._client
    
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """
        Generate text using Groq API.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text string
        """
        client = self._get_client()
        
        models_to_try = [self._current_model] + [
            m for m in self.FALLBACK_MODELS if m != self._current_model
        ]
        
        last_error = None
        
        for model in models_to_try:
            try:
                self.logger.info(f"Generating with model: {model}")
                
                # Groq client is synchronous, run in thread for async compatibility
                import asyncio
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert encyclopedic writer. Write high-quality, neutral, factual content."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        max_tokens=max_tokens,
                        temperature=0.7,
                    )
                )
                
                # Update current model on success
                self._current_model = model
                
                generated_text = response.choices[0].message.content
                self.logger.info(f"Generated {len(generated_text)} characters")
                
                return generated_text
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Model {model} failed: {str(e)}, trying fallback...")
                continue
        
        # All models failed
        raise RuntimeError(f"All Groq models failed. Last error: {last_error}")
    
    async def generate_with_retry(
        self, 
        prompt: str, 
        max_tokens: int = 4096,
        max_retries: int = 3
    ) -> str:
        """
        Generate with retry logic for transient failures.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            max_retries: Number of retry attempts
            
        Returns:
            Generated text string
        """
        import asyncio
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await self.generate(prompt, max_tokens)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"Generation failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
        
        raise RuntimeError(f"Generation failed after {max_retries} attempts: {last_error}")

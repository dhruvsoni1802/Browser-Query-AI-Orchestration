from pydantic_settings import BaseSettings
from pydantic import HttpUrl, Field
from typing import Optional


class Settings(BaseSettings):

    # Project configurations
    project_name: str = Field(default="Browser Query AI Orchestration", description="The name of the project")
    project_version: str = Field(default="0.1.0", description="The version of the project")

    # Infrastructure configurations
    infrastructure_url: HttpUrl = Field(default=HttpUrl("http://localhost:8080"), description="The URL of the infrastructure layer")
    redis_url: Optional[HttpUrl] = Field(default=None, description="The URL of the Redis instance")

    # LLM configurations
    llm_provider: str = Field(default="ollama", description="The LLM provider: 'ollama', 'openai', 'anthropic'")
    llm_model: str = Field(default="qwen2.5", description="The LLM model to use")
    llm_base_url: str = Field(default="http://localhost:11434", description="Base URL for the LLM API (used by Ollama)")
    llm_api_key: Optional[str] = Field(default=None, description="The LLM API key (not needed for Ollama)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
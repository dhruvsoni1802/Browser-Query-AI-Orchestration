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
  llm_provider: Optional[str] = Field(default=None, description="The LLM provider to use")
  llm_model: Optional[str] = Field(default=None, description="The LLM model to use")
  llm_api_key: Optional[str] = Field(default=None, description="The LLM API key to use")

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"

settings = Settings()


from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "UniAgent"
    llm_provider: str = "mock"
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./app.db"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: str = "dev-secret-change-me-0123456789abcdef"  # >= 32 bytes for HS256
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720  # 12 hours; plenty for a hackathon demo

    # --- RAG (S3) ---
    # Multilingual sentence-transformers model: an Uzbek question must retrieve
    # English/Russian documents too. Runs locally, no API key.
    embedding_model: str = "intfloat/multilingual-e5-small"
    # e5 models expect these prefixes; empty strings for models that do not.
    embedding_query_prefix: str = "query: "
    embedding_passage_prefix: str = "passage: "
    # Mean-centering removes the model's anisotropy ("hub") direction. Without
    # it an Uzbek question matches *any* Uzbek chunk better than the correct
    # English one; measured on the seed corpus: 12/16 -> 15/16 top-1 hits.
    embedding_center: bool = True
    chroma_path: str = "./chroma_data"
    chroma_collection: str = "uniagent_documents"
    # Hybrid search: keyword overlap weight when re-ranking the vector hits.
    # 0 = pure semantic. Measured on the seed corpus (24 queries, top-1):
    # 14/24 plain -> 16/24 centered -> 19/24 centered + lexical at 0.3.
    search_lexical_weight: float = 0.3
    # How many vector hits to re-rank before cutting down to top_k.
    search_candidate_factor: int = 4
    search_min_candidates: int = 20
    # Chunking budget in characters (~1 token = 3-4 chars for our corpus);
    # kept under the model's 512-token window so nothing is truncated.
    chunk_target_chars: int = 1600
    chunk_max_chars: int = 2200

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

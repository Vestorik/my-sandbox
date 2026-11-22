from torch import torch as tr
from os import getenv

DEVICE = tr.device("cuda" if tr.cuda.is_available() else "cpu")
SENTECE_TRANSFORM_MODEL_STR: str = getenv(
    "SENTECE_TRANSFORM_MODEL_NAME", "sberbank-ai/sbert_large_nlu_ru"
)


# Qdrant API
VECTOR_BD_URL = getenv("QDRANT_HOST", "http://localhost:") + getenv(
    "QDRANT_PORT", "6333"
)
VECTOR_BD_API_KEY = getenv("QDRANT_API_KEY", "")

# ---


class PlayloadPoint(BaseModel):
    text: str = Field(..., min_length=1, description="Текст чанка")
    source: Optional[str] = Field(None, description="Источник: имя файла, URL и т.п.")
    metadata: Dict[str, str | int | float] = Field(
        default_factory=dict, description="Дополнительные поля: title, page и т.п."
    )


from langsmith.prompt_cache import Cache
from sentence_transformers import SentenceTransformer
from config import (
    DEVICE,
    SENTECE_TRANSFORM_MODEL_STR,
    VECTOR_BD_API_KEY,
    VECTOR_BD_URL,
    CACHE_PATH,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

QDRANT_URL: str = VECTOR_BD_URL
QDRANT_KEY: str = VECTOR_BD_API_KEY

BASE_COLLECTION_NAME: str = "BASE_COLLECTION"

# Трансформеры текста
SENTECE_TRANSFORM_MODEL = SentenceTransformer(SENTECE_TRANSFORM_MODEL_STR)
#   cache_folder=str(CACHE_PATH / 'models' / SENTECE_TRANSFORM_MODEL_STR))
SENTECE_TRANSFORM_MODEL = SENTECE_TRANSFORM_MODEL.to(DEVICE)

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

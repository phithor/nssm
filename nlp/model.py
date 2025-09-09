"""
Hugging Face Model Loading and Caching for Norwegian/Swedish Sentiment Analysis

Provides lazy loading and caching of BERT models fine-tuned for Scandinavian languages.
Handles model downloads, GPU/CPU device selection, and memory optimization.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)

# Model configurations for Norwegian, Swedish, and English
MODEL_CONFIGS = {
    "no": {
        "model_name": "ltg/norbert-sentiment",
        "description": "Norwegian BERT model fine-tuned for sentiment analysis",
        "max_length": 512,
    },
    "sv": {
        "model_name": "KBLab/bert-base-swedish-cased",
        "description": "Swedish BERT base model for sentiment analysis",
        "max_length": 512,
    },
    "en": {
        "model_name": "cardiffnlp/twitter-roberta-base-sentiment-latest",
        "description": "English RoBERTa model for sentiment analysis",
        "max_length": 512,
    },
}


class ModelCache:
    """Cache for loaded models and tokenizers to avoid repeated loading."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize model cache.

        Args:
            cache_dir: Custom cache directory for models. Defaults to HF cache.
        """
        # Use mounted models directory in Docker, fallback to default
        if cache_dir is None:
            docker_models_dir = Path("/app/models")
            if docker_models_dir.exists():
                self.cache_dir = docker_models_dir
            else:
                self.cache_dir = Path.home() / ".cache" / "nssm" / "models"
        else:
            self.cache_dir = cache_dir

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache for loaded models
        self._model_cache: Dict[str, Tuple[PreTrainedTokenizer, PreTrainedModel]] = {}
        self._device = self._get_optimal_device()

    def _get_optimal_device(self) -> torch.device:
        """Get the optimal device for model inference."""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")

    def get_model(self, lang: str) -> Tuple[PreTrainedTokenizer, PreTrainedModel]:
        """
        Get tokenizer and model for specified language with caching.

        Args:
            lang: Language code ('no' or 'sv')

        Returns:
            Tuple of (tokenizer, model)

        Raises:
            ValueError: If language is not supported
        """
        if lang not in MODEL_CONFIGS:
            raise ValueError(
                f"Unsupported language: {lang}. Supported: {list(MODEL_CONFIGS.keys())}"
            )

        # Check cache first
        if lang in self._model_cache:
            return self._model_cache[lang]

        # Load model and tokenizer
        config = MODEL_CONFIGS[lang]
        model_name = config["model_name"]

        print(f"Loading {config['description']}...")

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=str(self.cache_dir),
                local_files_only=False,  # Allow downloads to create proper cache
                use_fast=True,
            )

            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                cache_dir=str(self.cache_dir),
                local_files_only=False,  # Allow downloads to create proper cache
                torch_dtype=(
                    torch.float16 if self._device.type == "cuda" else torch.float32
                ),
                device_map="auto" if self._device.type == "cuda" else None,
            )

            # Move to device if not using device_map
            if self._device.type != "cuda":
                model = model.to(self._device)

            # Set model to evaluation mode
            model.eval()

            # Cache the loaded model
            self._model_cache[lang] = (tokenizer, model)

            print(f"Successfully loaded {lang.upper()} model on {self._device}")
            return tokenizer, model

        except Exception as e:
            raise RuntimeError(
                f"Failed to load {lang.upper()} model '{model_name}': {e}"
            )

    def clear_cache(self, lang: Optional[str] = None):
        """
        Clear cached models from memory.

        Args:
            lang: Specific language to clear, or None to clear all
        """
        if lang:
            if lang in self._model_cache:
                del self._model_cache[lang]
                print(f"Cleared {lang.upper()} model from cache")
        else:
            self._model_cache.clear()
            print("Cleared all models from cache")

    def get_cache_info(self) -> Dict:
        """Get information about cached models."""
        return {
            "cached_languages": list(self._model_cache.keys()),
            "cache_directory": str(self.cache_dir),
            "device": str(self._device),
            "cuda_available": torch.cuda.is_available(),
            "mps_available": torch.backends.mps.is_available(),
        }


# Global model cache instance
_model_cache = ModelCache()


def get_model(lang: str) -> Tuple[PreTrainedTokenizer, PreTrainedModel]:
    """
    Convenience function to get model and tokenizer for a language.

    Args:
        lang: Language code ('no' or 'sv')

    Returns:
        Tuple of (tokenizer, model)
    """
    return _model_cache.get_model(lang)


def get_model_info() -> Dict:
    """Get information about available models and cache status."""
    info = {
        "supported_languages": list(MODEL_CONFIGS.keys()),
        "model_configs": MODEL_CONFIGS.copy(),
    }
    info.update(_model_cache.get_cache_info())
    return info


def preload_models(languages: Optional[list[str]] = None):
    """
    Preload models for specified languages to reduce startup time.

    Args:
        languages: List of language codes to preload. If None, preload all.
    """
    if languages is None:
        languages = list(MODEL_CONFIGS.keys())

    print(f"Preloading models for languages: {languages}")
    for lang in languages:
        try:
            get_model(lang)
        except Exception as e:
            print(f"Warning: Failed to preload {lang.upper()} model: {e}")


def set_cache_dir(cache_dir: Union[str, Path]):
    """Set custom cache directory for models."""
    global _model_cache
    _model_cache = ModelCache(Path(cache_dir))


# Environment variable configuration
if cache_dir_env := os.getenv("NSSM_MODEL_CACHE_DIR"):
    set_cache_dir(Path(cache_dir_env))

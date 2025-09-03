"""
Unit tests for NLP model loading and caching module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nlp.model import (
    MODEL_CONFIGS,
    ModelCache,
    get_model,
    get_model_info,
    preload_models,
    set_cache_dir,
)


class TestModelConfigs:
    """Test model configuration constants."""

    def test_model_configs_structure(self):
        """Test that MODEL_CONFIGS has expected structure."""
        assert isinstance(MODEL_CONFIGS, dict)
        assert "no" in MODEL_CONFIGS
        assert "sv" in MODEL_CONFIGS
        assert "en" in MODEL_CONFIGS

        for lang, config in MODEL_CONFIGS.items():
            assert "model_name" in config
            assert "description" in config
            assert "max_length" in config
            assert isinstance(config["model_name"], str)
            assert isinstance(config["description"], str)
            assert isinstance(config["max_length"], int)

    def test_norwegian_config(self):
        """Test Norwegian model configuration."""
        config = MODEL_CONFIGS["no"]
        assert "NbAiLab/nb-bert-base" in config["model_name"]
        assert "Norwegian" in config["description"]

    def test_swedish_config(self):
        """Test Swedish model configuration."""
        config = MODEL_CONFIGS["sv"]
        assert "KBLab/swe-bert-base" in config["model_name"]
        assert "Swedish" in config["description"]

    def test_english_config(self):
        """Test English model configuration."""
        config = MODEL_CONFIGS["en"]
        assert (
            "cardiffnlp/twitter-roberta-base-sentiment-latest" in config["model_name"]
        )
        assert "English" in config["description"]


class TestModelCache:
    """Test ModelCache class functionality."""

    def test_init_default_cache_dir(self):
        """Test initialization with default cache directory."""
        cache = ModelCache()
        assert cache.cache_dir.exists()
        assert "nssm" in str(cache.cache_dir)
        assert "models" in str(cache.cache_dir)
        assert len(cache._model_cache) == 0

    def test_init_custom_cache_dir(self):
        """Test initialization with custom cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "custom_cache"
            cache = ModelCache(custom_dir)
            assert cache.cache_dir == custom_dir
            assert cache.cache_dir.exists()

    def test_get_optimal_device_cpu(self):
        """Test device selection when only CPU is available."""
        with patch("torch.cuda.is_available", return_value=False), patch(
            "torch.backends.mps.is_available", return_value=False
        ):

            cache = ModelCache()
            device = cache._get_optimal_device()
            assert str(device) == "cpu"

    @patch("torch.cuda.is_available", return_value=True)
    def test_get_optimal_device_cuda(self, mock_cuda):
        """Test device selection when CUDA is available."""
        cache = ModelCache()
        device = cache._get_optimal_device()
        assert str(device) == "cuda"

    @patch("torch.backends.mps.is_available", return_value=True)
    @patch("torch.cuda.is_available", return_value=False)
    def test_get_optimal_device_mps(self, mock_cuda, mock_mps):
        """Test device selection when MPS is available."""
        cache = ModelCache()
        device = cache._get_optimal_device()
        assert str(device) == "mps"

    def test_get_model_unsupported_language(self):
        """Test that unsupported language raises ValueError."""
        cache = ModelCache()

        with pytest.raises(ValueError, match="Unsupported language"):
            cache.get_model("unsupported_lang")

    @patch("nlp.model.AutoTokenizer")
    @patch("nlp.model.AutoModelForSequenceClassification")
    def test_get_model_success(self, mock_model_class, mock_tokenizer_class):
        """Test successful model loading and caching."""
        # Mock the HF classes
        mock_tokenizer = Mock()
        mock_model = Mock()
        mock_model.to.return_value = mock_model  # Mock the to() method
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_model

        cache = ModelCache()

        # First call should load the model
        tokenizer, model = cache.get_model("no")

        assert tokenizer == mock_tokenizer
        assert model == mock_model
        assert "no" in cache._model_cache

        # Second call should return cached model
        tokenizer2, model2 = cache.get_model("no")
        assert tokenizer2 == mock_tokenizer
        assert model2 == mock_model

        # Verify from_pretrained was called only once
        mock_tokenizer_class.from_pretrained.assert_called_once()
        mock_model_class.from_pretrained.assert_called_once()

    @patch("nlp.model.AutoTokenizer")
    @patch("nlp.model.AutoModelForSequenceClassification")
    def test_get_model_loading_error(self, mock_model_class, mock_tokenizer_class):
        """Test error handling during model loading."""
        mock_tokenizer_class.from_pretrained.side_effect = Exception("Network error")

        cache = ModelCache()

        with pytest.raises(RuntimeError, match="Failed to load NO model"):
            cache.get_model("no")

    def test_clear_cache_specific_language(self):
        """Test clearing cache for specific language."""
        cache = ModelCache()
        cache._model_cache["no"] = (Mock(), Mock())

        cache.clear_cache("no")
        assert "no" not in cache._model_cache

    def test_clear_cache_all(self):
        """Test clearing all cached models."""
        cache = ModelCache()
        cache._model_cache["no"] = (Mock(), Mock())
        cache._model_cache["sv"] = (Mock(), Mock())

        cache.clear_cache()
        assert len(cache._model_cache) == 0

    def test_get_cache_info(self):
        """Test cache information retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = ModelCache(Path(temp_dir))

            info = cache.get_cache_info()

            assert "cached_languages" in info
            assert "cache_directory" in info
            assert "device" in info
            assert "cuda_available" in info
            assert "mps_available" in info
            assert info["cached_languages"] == []


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch("nlp.model._model_cache")
    def test_get_model_convenience(self, mock_cache):
        """Test get_model convenience function."""
        mock_tokenizer, mock_model = Mock(), Mock()
        mock_cache.get_model.return_value = (mock_tokenizer, mock_model)

        result_tokenizer, result_model = get_model("no")

        assert result_tokenizer == mock_tokenizer
        assert result_model == mock_model
        mock_cache.get_model.assert_called_once_with("no")

    @patch("nlp.model._model_cache")
    def test_get_model_info(self, mock_cache):
        """Test get_model_info function."""
        mock_cache.get_cache_info.return_value = {"device": "cpu"}

        info = get_model_info()

        assert "supported_languages" in info
        assert "model_configs" in info
        assert "device" in info

    @patch("nlp.model.get_model")
    def test_preload_models_all(self, mock_get_model):
        """Test preloading all models."""
        preload_models()
        assert mock_get_model.call_count == 2  # no and sv

    @patch("nlp.model.get_model")
    def test_preload_models_specific(self, mock_get_model):
        """Test preloading specific models."""
        preload_models(["no"])
        mock_get_model.assert_called_once_with("no")

    @patch("nlp.model.get_model")
    def test_preload_models_with_error(self, mock_get_model):
        """Test preloading when model loading fails."""
        mock_get_model.side_effect = Exception("Load failed")

        # Should not raise exception, just print warning
        preload_models(["no"])

    def test_set_cache_dir(self):
        """Test setting custom cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "test_cache"
            set_cache_dir(cache_dir)

            # Import the module again to get the updated cache
            from nlp import model

            assert model._model_cache.cache_dir == cache_dir


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    def test_cache_dir_from_env(self):
        """Test setting cache directory from environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_cache_dir = Path(temp_dir) / "env_cache"

            # Set environment variable
            os.environ["NSSM_MODEL_CACHE_DIR"] = str(env_cache_dir)

            try:
                # Re-import to trigger environment variable check
                import importlib

                import nlp.model

                importlib.reload(nlp.model)

                assert nlp.model._model_cache.cache_dir == env_cache_dir
            finally:
                # Clean up environment variable
                del os.environ["NSSM_MODEL_CACHE_DIR"]
                importlib.reload(nlp.model)

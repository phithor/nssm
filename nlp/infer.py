"""
Batch Inference Logic for Norwegian/Swedish Sentiment Analysis

Provides efficient batch processing of forum posts using Hugging Face models,
with proper error handling and performance optimizations.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import PreTrainedModel, PreTrainedTokenizer

from .lang_detect import detect_lang
from .model import get_model
from .preprocess import clean_text


@dataclass
class SentimentResult:
    """Result of sentiment analysis for a single post."""

    post_id: str
    score: float
    confidence: float
    language: str
    processing_time: float
    error: Optional[str] = None


@dataclass
class BatchInferenceResult:
    """Result of batch sentiment analysis."""

    results: List[SentimentResult]
    batch_size: int
    processing_time: float
    success_count: int
    error_count: int


class SentimentAnalyzer:
    """Handles batch sentiment analysis with automatic language detection and model selection."""

    def __init__(self, batch_size: int = 16, max_length: int = 512):
        """
        Initialize the sentiment analyzer.

        Args:
            batch_size: Number of texts to process simultaneously
            max_length: Maximum sequence length for tokenization
        """
        self.batch_size = batch_size
        self.max_length = max_length
        self._model_cache: Dict[str, Tuple[PreTrainedTokenizer, PreTrainedModel]] = {}

    def analyze_batch(
        self, posts: List[Dict[str, Any]], locale_hint: Optional[str] = None
    ) -> BatchInferenceResult:
        """
        Analyze sentiment for a batch of posts.

        Args:
            posts: List of post dictionaries with 'id' and 'text' keys
            locale_hint: Optional locale hint to guide language detection

        Returns:
            BatchInferenceResult with sentiment scores for all posts
        """
        start_time = time.time()

        # Language detection and grouping
        language_groups = self._group_posts_by_language(posts, locale_hint)

        all_results = []

        # Process each language group
        for lang, lang_posts in language_groups.items():
            try:
                lang_results = self._analyze_language_batch(lang, lang_posts)
                all_results.extend(lang_results)
            except Exception as e:
                # If language processing fails, mark all posts in that language as errors
                error_results = [
                    SentimentResult(
                        post_id=post["id"],
                        score=0.0,
                        confidence=0.0,
                        language=lang,
                        processing_time=0.0,
                        error=str(e),
                    )
                    for post in lang_posts
                ]
                all_results.extend(error_results)

        processing_time = time.time() - start_time
        success_count = sum(1 for r in all_results if r.error is None)
        error_count = len(all_results) - success_count

        return BatchInferenceResult(
            results=all_results,
            batch_size=len(posts),
            processing_time=processing_time,
            success_count=success_count,
            error_count=error_count,
        )

    def _group_posts_by_language(
        self, posts: List[Dict[str, Any]], locale_hint: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group posts by detected language."""
        language_groups = {"no": [], "sv": []}

        for post in posts:
            text = post.get("text", "")
            if not text.strip():
                # Empty text - default to Norwegian
                language_groups["no"].append(post)
                continue

            try:
                detected_lang = detect_lang(text, locale_hint)
                language_groups[detected_lang].append(post)
            except Exception:
                # On detection error, default to Norwegian
                language_groups["no"].append(post)

        return {k: v for k, v in language_groups.items() if v}  # Remove empty groups

    def _analyze_language_batch(
        self, lang: str, posts: List[Dict[str, Any]]
    ) -> List[SentimentResult]:
        """Analyze sentiment for posts in a specific language."""
        if lang not in self._model_cache:
            tokenizer, model = get_model(lang)
            self._model_cache[lang] = (tokenizer, model)
        else:
            tokenizer, model = self._model_cache[lang]

        results = []

        # Process in batches for efficiency
        for i in range(0, len(posts), self.batch_size):
            batch_posts = posts[i : i + self.batch_size]
            batch_results = self._analyze_single_batch(
                tokenizer, model, batch_posts, lang
            )
            results.extend(batch_results)

        return results

    def _analyze_single_batch(
        self,
        tokenizer: PreTrainedTokenizer,
        model: PreTrainedModel,
        posts: List[Dict[str, Any]],
        lang: str,
    ) -> List[SentimentResult]:
        """Analyze sentiment for a single batch of posts."""
        batch_start_time = time.time()

        batch_texts = []
        batch_posts_data = []

        # Preprocess texts and collect post data
        for post in posts:
            text = post.get("text", "")
            if not text.strip():
                # Handle empty text
                batch_texts.append("")
                batch_posts_data.append(post)
                continue

            try:
                cleaned_text = clean_text(text)
                batch_texts.append(cleaned_text)
                batch_posts_data.append(post)
            except Exception as e:
                # If preprocessing fails, create error result
                results = [
                    SentimentResult(
                        post_id=post["id"],
                        score=0.0,
                        confidence=0.0,
                        language=lang,
                        processing_time=time.time() - batch_start_time,
                        error=f"Preprocessing failed: {e}",
                    )
                ]
                return results

        if not batch_texts:
            return []

        try:
            # Tokenize batch
            inputs = tokenizer(
                batch_texts,
                max_length=self.max_length,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )

            # Move to model's device
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            # Run inference
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits

            # Apply softmax to get probabilities
            probabilities = torch.softmax(logits, dim=-1)

            # Cardiff multilingual model has 3 classes: [NEGATIVE, NEUTRAL, POSITIVE]
            # Calculate sentiment score as: (positive_prob - negative_prob + 1) / 2
            # This maps [-1, 1] to [0, 1] where 0=negative, 0.5=neutral, 1=positive
            negative_probs = probabilities[:, 0]  # NEGATIVE
            neutral_probs = probabilities[:, 1]   # NEUTRAL  
            positive_probs = probabilities[:, 2]  # POSITIVE
            
            # Sentiment score: weighted by positive vs negative (ignoring neutral)
            sentiment_scores = (positive_probs - negative_probs + 1) / 2
            sentiment_scores = sentiment_scores.cpu().numpy()

            # Calculate confidence as max probability (how sure is the model?)
            confidences = torch.max(probabilities, dim=-1)[0].cpu().numpy()

            batch_processing_time = time.time() - batch_start_time

            # Create results
            results = []
            for i, post in enumerate(batch_posts_data):
                if batch_texts[
                    i
                ].strip():  # Only if text was not empty after preprocessing
                    results.append(
                        SentimentResult(
                            post_id=post["id"],
                            score=float(sentiment_scores[i]),
                            confidence=float(confidences[i]),
                            language=lang,
                            processing_time=batch_processing_time
                            / len(batch_posts_data),
                            error=None,
                        )
                    )
                else:
                    results.append(
                        SentimentResult(
                            post_id=post["id"],
                            score=0.5,  # Neutral score for empty text
                            confidence=0.0,
                            language=lang,
                            processing_time=batch_processing_time
                            / len(batch_posts_data),
                            error="Empty text after preprocessing",
                        )
                    )

            return results

        except Exception as e:
            batch_processing_time = time.time() - batch_start_time
            return [
                SentimentResult(
                    post_id=post["id"],
                    score=0.0,
                    confidence=0.0,
                    language=lang,
                    processing_time=batch_processing_time / len(batch_posts_data),
                    error=f"Inference failed: {e}",
                )
                for post in batch_posts_data
            ]


# Convenience functions
def analyze_sentiment(
    posts: List[Dict[str, Any]], locale_hint: Optional[str] = None, batch_size: int = 16
) -> BatchInferenceResult:
    """
    Convenience function for sentiment analysis.

    Args:
        posts: List of post dictionaries with 'id' and 'text' keys
        locale_hint: Optional locale hint for language detection
        batch_size: Number of posts to process simultaneously

    Returns:
        BatchInferenceResult with sentiment analysis results
    """
    analyzer = SentimentAnalyzer(batch_size=batch_size)
    return analyzer.analyze_batch(posts, locale_hint)


def analyze_single_post(
    post_id: str, text: str, locale_hint: Optional[str] = None
) -> SentimentResult:
    """
    Analyze sentiment for a single post.

    Args:
        post_id: Unique identifier for the post
        text: Post text content
        locale_hint: Optional locale hint for language detection

    Returns:
        SentimentResult for the post
    """
    posts = [{"id": post_id, "text": text}]
    result = analyze_sentiment(posts, locale_hint)

    if result.results:
        return result.results[0]
    else:
        # Fallback result
        return SentimentResult(
            post_id=post_id,
            score=0.0,
            confidence=0.0,
            language="unknown",
            processing_time=0.0,
            error="Analysis failed",
        )

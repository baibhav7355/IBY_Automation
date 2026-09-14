"""src/segmentation/__init__.py"""
from src.segmentation.llm_labeler import LABELING_PROMPT_TEMPLATE, predict_label
from src.segmentation.ml_segmenter import MLGoldenThreadSegmenter
from src.segmentation.segmenter import (
    GoldenThreadSegmenter,
    Segment,
    extract_segment_context,
    filter_events,
    generate_segment_label,
    merge_segments,
    segment_session,
)

__all__ = [
    "GoldenThreadSegmenter",
    "MLGoldenThreadSegmenter",
    "Segment",
    "generate_segment_label",
    "merge_segments",
    "predict_label",
    "extract_segment_context",
    "filter_events",
    "segment_session",
    "LABELING_PROMPT_TEMPLATE",
]

from typing import Dict, Any


def compute_wer_cer(reference_text: str, hypothesis_text: str) -> Dict[str, Any]:
    """
    Computes Word Error Rate (WER) and Character Error Rate (CER) between
    ground-truth reference text and the ASR hypothesis.
    """
    if not reference_text or not reference_text.strip():
        raise ValueError("Reference text cannot be empty for evaluation.")

    try:
        from jiwer import wer, cer
    except ImportError:
        raise ImportError(
            "The 'jiwer' library is required for WER/CER evaluation. Install it via 'pip install jiwer'."
        )

    clean_ref = reference_text.strip()
    clean_hyp = hypothesis_text.strip() if hypothesis_text else ""

    wer_score = float(wer(clean_ref, clean_hyp))
    cer_score = float(cer(clean_ref, clean_hyp))

    return {
        "wer": round(wer_score, 4),
        "cer": round(cer_score, 4),
        "reference_words": len(clean_ref.split()),
        "hypothesis_words": len(clean_hyp.split()) if clean_hyp else 0,
    }

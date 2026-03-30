import os


def main() -> int:
    """
    Build-time warmup for PaddleOCR models so runtime doesn't block on first request.
    Safe to run even when Paddle deps are missing (it will just exit 0).
    """
    try:
        import paddle  # noqa: F401
        from paddleocr import PaddleOCR  # noqa: F401
    except Exception:
        print("warmup_paddle: paddle/paddleocr not installed; skipping")
        return 0

    # Keep logs minimal during image build
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_use_new_executor", "0")
    os.environ.setdefault("FLAGS_enable_onednn", "0")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")

    try:
        from backend.services.paddle_ocr_runtime import get_paddle_engine

        get_paddle_engine()
        print("warmup_paddle: ok")
        return 0
    except Exception as e:
        # Do not fail the build hard; runtime can fall back to Gemini.
        print(f"warmup_paddle: failed: {e}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())


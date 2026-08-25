"""UI band — single-page Streamlit app (composition root).

Contains no business logic (docs/UI_ARCHITECTURE.md): the pure presentation
model lives in ``ui_model`` (Streamlit-free, unit-tested); all math and all
validation live in the ``universality`` package. The app is the composition
root: it collects primitives, calls ``universality.evaluate`` (via the
public API), and renders the outcome.

Entry point: ``ui/app.py`` (run with ``streamlit run ui/app.py``).
"""

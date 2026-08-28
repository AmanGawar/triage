"""
Knowledge-base loading, chunking, and retrieval.

Design decision (see DESIGN_NOTE.md): retrieval uses TF-IDF (scikit-learn) over
the KB chunks rather than a hosted embedding API. For a KB this size (9 markdown
files), TF-IDF keyword/phrase matching is fast, free, needs no network call or
API key, and is easy to explain in the demo. At real-world KB scale this would
be swapped for a proper embedding index (e.g. sentence-transformers + FAISS) —
noted explicitly as a scaling limitation in DESIGN_NOTE.md.

Chunking strategy follows DATA_SCHEMA.md's own recommendation: split on `---`
horizontal rules, keep heading hierarchy as metadata, treat table blocks as
atomic chunks.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Chunk:
    doc_path: str          # relative path, e.g. "products/databridge-pro.md"
    heading: str            # nearest preceding heading, for citation
    text: str
    chunk_id: str = field(default="")

    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = f"{self.doc_path}#{abs(hash(self.text)) % 10**6}"


def _split_into_chunks(doc_path: str, raw_text: str) -> List[Chunk]:
    """Split on --- horizontal rules; track the most recent markdown heading per chunk."""
    sections = re.split(r"\n-{3,}\n", raw_text)
    chunks: List[Chunk] = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        headings = re.findall(r"^(#{1,3})\s+(.*)$", section, flags=re.MULTILINE)
        heading = headings[-1][1] if headings else "(no heading)"
        # Sub-split very long sections further by ## boundaries so chunks stay focused
        subsections = re.split(r"\n(?=## )", section)
        for sub in subsections:
            sub = sub.strip()
            if len(sub) < 20:
                continue
            sub_heading_match = re.match(r"^#{1,3}\s+(.*)$", sub, flags=re.MULTILINE)
            sub_heading = sub_heading_match.group(1) if sub_heading_match else heading
            chunks.append(Chunk(doc_path=doc_path, heading=sub_heading, text=sub))
    return chunks


def load_knowledge_base(kb_root: str) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for dirpath, _, filenames in os.walk(kb_root):
        for fname in sorted(filenames):
            if not fname.endswith(".md"):
                continue
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, kb_root)
            with open(full_path, "r", encoding="utf-8") as f:
                raw = f.read()
            all_chunks.extend(_split_into_chunks(rel_path, raw))
    return all_chunks


class KBIndex:
    """TF-IDF index over knowledge-base chunks, with a simple .search(query, k) API."""

    def __init__(self, kb_root: str):
        self.chunks = load_knowledge_base(kb_root)
        if not self.chunks:
            raise ValueError(f"No knowledge-base chunks found under {kb_root}")
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        corpus = [c.text for c in self.chunks]
        self._matrix = self._vectorizer.fit_transform(corpus)

    def search(self, query: str, k: int = 3, min_score: float = 0.05):
        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix)[0]
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)
        results = [(chunk, float(score)) for chunk, score in ranked[:k] if score >= min_score]
        return results

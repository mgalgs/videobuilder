"""A tiny BM25 index, pure Python (no new dependency; this project favours
easy self-hosting): used by suggest.py to narrow its much-too-large lists
(hundreds of capabilities, plus sound effects and music tracks) down to a
per-note shortlist before any of it reaches a model's prompt.

    index = BM25([('whoosh_fast/tight', 'whoosh classic a fast pass...'), ...])
    index.query('add a quick air sound as the title flies in', 15)

Tokenizing is deliberately light: lowercase, strip punctuation, a simple
plural strip -- never stemmed harder than that (see `tokenize`).
"""
import math
import re

_WORD_RE = re.compile(r'[a-z0-9]+')
_K1 = 1.5
_B = 0.75


def tokenize(text):
    """Lowercase words, with a simple plural strip (trailing 's' off a word
    longer than 3 letters, 'es' off one longer than 4) -- not real
    stemming, just enough that "whooshes" and "whoosh" share a term."""
    words = []
    for w in _WORD_RE.findall(text.lower()):
        if len(w) > 4 and w.endswith('es'):
            w = w[:-2]
        elif len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
            w = w[:-1]
        words.append(w)
    return words


class BM25:
    """A BM25 index over `(id, text)` pairs, queried with free text. `ids`
    holds every id the index was built from, build order."""

    def __init__(self, docs):
        self.ids = [id_ for id_, _ in docs]
        self._lens = []
        self._postings = {}  # term -> {doc index: count in that doc}
        for i, (_, text) in enumerate(docs):
            freq = {}
            for t in tokenize(text):
                freq[t] = freq.get(t, 0) + 1
            self._lens.append(sum(freq.values()))
            for t, f in freq.items():
                self._postings.setdefault(t, {})[i] = f
        n = len(self.ids)
        self._n = n
        self.avgdl = (sum(self._lens) / n) if n else 0.0
        self._idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self._postings.items()}

    def query(self, text, top_n):
        """The `top_n` ids scoring highest, best first; an index with no
        documents, or a query with no term the index has ever seen, answers
        an empty list."""
        terms = tokenize(text)
        if not self._n or not terms:
            return []
        scores = {}
        for t in terms:
            postings = self._postings.get(t)
            if not postings:
                continue
            idf = self._idf[t]
            for i, f in postings.items():
                denom = f + _K1 * (1 - _B + _B * self._lens[i] / self.avgdl)
                scores[i] = scores.get(i, 0.0) + idf * (f * (_K1 + 1)) / denom
        ranked = sorted(scores, key=lambda i: (-scores[i], i))
        return [self.ids[i] for i in ranked[:top_n]]

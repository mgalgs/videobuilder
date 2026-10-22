"""The BM25 index (suggest_index.py) suggest.py builds its per-note
shortlists from: ranking sanity against small, hand-built document sets,
never against the real catalogs (those are covered by tests/test_suggest.py
and the retrieval-recall test)."""
import unittest

from videobuilder.suggest_index import BM25, tokenize


class Tokenize(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(tokenize('Make it Whoosh, fast!'), ['make', 'it', 'whoosh', 'fast'])

    def test_light_plural_strip(self):
        self.assertEqual(tokenize('whooshes whoosh glasses'), ['whoosh', 'whoosh', 'glass'])

    def test_short_words_not_stripped(self):
        self.assertEqual(tokenize('bus gas yes'), ['bus', 'gas', 'yes'])


class Query(unittest.TestCase):
    DOCS = [
        ('whoosh', 'whoosh a fast pass a whip pan a fly-in an element moving'),
        ('ding', 'ding a short clean notification chime'),
        ('tick', 'tick a tiny hover detent a counter'),
    ]

    def test_best_matching_doc_ranks_first(self):
        idx = BM25(self.DOCS)
        self.assertEqual(idx.query('a quick whip pan whoosh on the cut', 3)[0], 'whoosh')

    def test_top_n_is_respected(self):
        idx = BM25(self.DOCS)
        self.assertEqual(len(idx.query('whoosh ding tick', 2)), 2)

    def test_unmatched_query_returns_empty(self):
        idx = BM25(self.DOCS)
        self.assertEqual(idx.query('zzyzx quux unmatched gibberish', 3), [])

    def test_empty_query_returns_empty(self):
        idx = BM25(self.DOCS)
        self.assertEqual(idx.query('', 3), [])

    def test_empty_index_returns_empty(self):
        idx = BM25([])
        self.assertEqual(idx.query('whoosh', 3), [])

    def test_ids_in_build_order(self):
        idx = BM25(self.DOCS)
        self.assertEqual(idx.ids, ['whoosh', 'ding', 'tick'])

    def test_a_term_repeated_in_the_query_does_not_crowd_out_other_matches(self):
        idx = BM25(self.DOCS)
        result = idx.query('ding ding ding chime notification tick detent counter', 3)
        self.assertEqual(set(result), {'ding', 'tick'})


if __name__ == '__main__':
    unittest.main()

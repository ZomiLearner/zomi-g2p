import logging
from zomi_g2p.lexicon import LexiconEntry
from zomi_g2p.utils.provenance import TONES_SOURCE_RULE

logger = logging.getLogger("zomi_g2p.utils.helpers")

def _reconcile(self, entry: LexiconEntry) -> LexiconEntry:
        """Cross-check rule-sourced tones against the rule engine."""
        if TONES_SOURCE_RULE not in entry.tone_sources:
            return entry
        predicted, sources = self.rule_engine.predict_tones(entry.syllables)
        new_tones = []
        new_sources = []
        for old_tone, old_src, pred_tone, pred_src in zip(
            entry.tones, entry.tone_sources, predicted, sources
        ):
            if old_src == TONES_SOURCE_RULE and old_tone != pred_tone:
                logger.warning(
                    "tone mismatch for %r syllable %r: lexicon=%s, rule=%s",
                    entry.word, entry.syllables, old_tone, pred_tone,
                )
                # Trust the rule engine over a stale default.
                new_tones.append(pred_tone)
                new_sources.append(pred_src)
            else:
                new_tones.append(old_tone)
                new_sources.append(old_src)
        return entry._replace(tones=tuple(new_tones), tone_sources=tuple(new_sources))
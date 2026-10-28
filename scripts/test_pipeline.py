"""
Maintainer smoke test: print all output representations for a known word.

Usage:
    python scripts/test_pipeline.py [word]

Not part of the pytest suite. Run manually after editing lexicon.csv,
segments.yaml, or tones.yaml to confirm the pipeline produces the
expected IPA / ASCII output.
"""

# from zomi_g2p import ZomiG2P
# from zomi_g2p.lexicon import load_lexicon_from_dir

# # lex = load_lexicon_from_dir("/path/to/your/data")  # dir with lexicon.csv, segments.yaml, tones.yaml
# g2p = ZomiG2P() #lex)
# g2p.convert("ankham").joined()

from zomi_g2p import ZomiG2P, load_default_lexicon

g2p = ZomiG2P(load_default_lexicon())

result = g2p.convert("ankham", output="ascii")
print(result.joined())          # ascii output
print(result.joined(sep="-"))   # custom separator

result = g2p.convert("ankham")
print(result)
print(result.joined())          # IPA output
print(result.joined(sep="-"))   # custom separator
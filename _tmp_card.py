import re
html = open('briefs/brief_20260310.html', encoding='utf-8').read()
# Find actual div id="card-..." elements
matches = list(re.finditer(r'id="card-(eurusd|usdjpy|usdinr)"', html))
for m in matches:
    print(m.start(), repr(html[m.start()-5:m.start()+80]))

# Also check gold specifically
gold_matches = list(re.finditer(r'gold_usdjpy_corr_60d', html))
print()
print('gold_usdjpy_corr_60d occurrences:')
for m in gold_matches:
    print(' ', m.start(), repr(html[m.start()-50:m.start()+60]))

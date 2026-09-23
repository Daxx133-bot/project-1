with open('generate_full_report_utf8.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 1283-1285 (0-indexed): broken PageRank ref_item
lines[1283] = "        ('L. Page, S. Brin, R. Motwani, and T. Winograd, '\n"
lines[1284] = "         'The PageRank citation ranking: Bringing order to the web, Stanford InfoLab Technical Report, 1999.', False),\n"

with open('generate_full_report_utf8.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('done')

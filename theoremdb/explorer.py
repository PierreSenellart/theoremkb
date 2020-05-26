import re,os,sys,pickle,shutil,fitz
from simple_term_menu import TerminalMenu


sys.path.append("..")
from config import TARGET_PATH, WORKING_PATH, DATA_PATH, ensuredir
from db import TheoremDB, Paper

with open(f"{DATA_PATH}/papers_db.pkl", "rb") as f:
    db = pickle.load(f)

print("Welcome to TheoremDB!")
print()
print("Articles:")
dclasses = {}
counts = []
for paper in db.papers.values():
    if paper.dclass not in dclasses:
        dclasses[paper.dclass] = []
    dclasses[paper.dclass].append(paper)

for dclass, papers in dclasses.items():
    count = len(papers)
    counts.append((count, dclass))

# https://gist.github.com/critiqjo/2ca84db26daaeb1715e1
def col_print(lines, term_width=None, indent=0, pad=2):
    if not term_width:
        size = shutil.get_terminal_size((80, 20))
        term_width = size.columns
    n_lines = len(lines)
    if n_lines == 0:
        return

    col_width = max(len(line) for line in lines)
    n_cols = int((term_width + pad - indent)/(col_width + pad))
    n_cols = min(n_lines, max(1, n_cols))

    col_len = int(n_lines/n_cols) + (0 if n_lines % n_cols == 0 else 1)
    if (n_cols - 1) * col_len >= n_lines:
        n_cols -= 1

    cols = [lines[i*col_len : i*col_len + col_len] for i in range(n_cols)]

    rows = list(zip(*cols))
    rows_missed = zip(*[col[len(rows):] for col in cols[:-1]])
    rows.extend(rows_missed)

    for row in rows:
        print(" "*indent + (" "*pad).join(line.ljust(col_width) for line in row))

counts.sort(reverse=True)
to_print = []
for count, dclass in counts:
    if len(dclass) > 20:
        dclass = dclass[:17]+".."
    to_print.append(f"{dclass}: {count}")

col_print(to_print)
print()
while True:
    
    dclass = input("Choose a document class or [E]xit: ")

    if dclass == "e":
        break

    if dclass not in dclasses:
        print("Unknown document class.\n")
        continue

    to_print = [(">" if p.n_results() > 0 else "x") + p.id for p in dclasses[dclass]]
    col_print(to_print)
    print()
        
    while True:
        article = input(f"[{dclass}] Choose an article or [R]eturn: ")

        if article == "r":
            break

        if article not in db.papers:
            print("Unknown article.\n")
            continue

        db.papers[article].describe()
        print()
        while True:
            result = input(f"[{dclass}][{article}] Choose the result to print or [R]eturn: ")

            if result == "r":
                break

            try:
                pdf = fitz.open(f"{TARGET_PATH}/{article}/{article}.pdf")
                db.papers[article].results.render(int(result), pdf)
            except Exception:
                print("Error.")
            
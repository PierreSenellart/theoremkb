#!/bin/python3
import os,sys,shutil,fileinput,subprocess,re
import filetype
from ..config import SOURCE_PATH, TARGET_PATH, WORKING_PATH, LOGS_PATH, REGENERATE, ensuredir
from datetime import datetime
from joblib import Parallel, delayed  

class PreprocessStatistics:
    def __init__(self):
        self.success= []
        self.no_tex = []
        self.main_not_found = []
        self.no_pdf = []
        self.oom    = []
        self.nop    = []
        self.err    = []
        self.unk    = []

    def print_statistics(self):
        print("Statistics:")
        print(f"{len(self.success)} extracted.")

        n_fail = sum(len(x) for x in [self.no_tex, self.no_pdf, self.main_not_found,\
                                      self.oom, self.nop, self.err, self.unk])

        print(f"{n_fail} extraction failed:")
        print(f"{len(self.no_tex)} had no .tex sources.")
        print(f"{len(self.main_not_found)} could not find main tex.")
        print(f"{len(self.no_pdf)} had no pdf.")
        print(f"{len(self.oom)} went out of memory.")
        print(f"{len(self.nop)} had no theorem.")
        print(f"{len(self.err)} had too many errors.")
        print(f"{len(self.unk)} had unknown.")

    def save_statistics(self, target):
        with open(target, "w") as f:
            f.write("OK:"+",".join(self.success)+"\n")
            f.write("NOTEX:"+",".join(self.no_tex)+"\n")
            f.write("MNF:"+",".join(self.main_not_found)+"\n")
            f.write("NOPDF:"+",".join(self.no_pdf)+"\n")
            f.write("OOM:"+",".join(self.oom)+"\n")
            f.write("NOP:"+",".join(self.nop)+"\n")
            f.write("ERR:"+",".join(self.err)+"\n")
            f.write("UNK:"+",".join(self.unk)+"\n")

    def add_success(self, paper):
        """Extraction has been successful."""
        self.success.append(paper)
        return "OK"

    def add_already_done(self, paper):
        self.success.append(paper)
        return "SKIPPED"

    def add_no_tex(self, paper):
        """No tex found in the source directory."""
        self.no_tex.append(paper)
        return "NOTEX"

    def add_main_not_found(self, paper):
        """Main Tex file hasn't been identified."""
        self.main_not_found.append(paper)
        return "MNF"

    def add_no_pdf(self, paper):
        """No full PDF article found."""
        self.no_pdf.append(paper)
        return "NOPDF"

    def add_oom(self, paper):
        """pdflatex went out of memory."""
        self.oom.append(paper)
        return "OOM"

    def add_nop(self, paper):
        """No page produced."""
        self.nop.append(paper)
        return "NOP"

    def add_err(self, paper):
        """Too many errors."""
        self.err.append(paper)
        return "ERR"
    
    def add_unk(self, paper):
        """Unknown error."""
        self.unk.append(paper)
        return "UNK"


stats = PreprocessStatistics()

def contains_documentclass(path):
    """
    Check if the given file contains a \documentclass{} instruction
    """
    with open(path, "rb") as f:
        for line in f:
            if line.strip().startswith(b"\\documentclass"):
                return True
    return False

def process_paper(paper):
    global stats

    paper_dash  = paper.replace('.','-')
    paper_dir   = f"{SOURCE_PATH}/CC-src/{paper_dash}"
    pdf_path    = f"{SOURCE_PATH}/CC-pdf/{paper}.pdf"

    target_directory = f"{TARGET_PATH}/{paper}"
    ensuredir(target_directory)

    ## Import check that full text PDF exists.
    pdf_type = filetype.guess(pdf_path)
    if pdf_type is None or pdf_type.mime != "application/pdf":
        return stats.add_no_pdf(paper)

    # shutil.copy(pdf_path, f"{target_directory}/{paper}.pdf")

    if not os.path.exists(paper_dir):
        return stats.add_no_tex(paper)  
    
    if not REGENERATE and os.path.exists(f"{target_directory}/{paper}.pdf"):
        return stats.add_already_done(paper)
    
    ## Inject extraction module to gather training data.
    source_files     = os.listdir(paper_dir)
    # check papers that have a single tex source.
    n_tex = len(list(filter(lambda x: x.endswith(".tex"), source_files)))
    if n_tex >= 1:
        working_directory = f"{WORKING_PATH}/{paper}/"
        ensuredir(working_directory)

        working_source    = f"{working_directory}/{paper}.tex"



        # Import whole directory and rename main tex source to {paper}.tex
        found_main_source = False
        for file in source_files:
            source = f"{paper_dir}/{file}"

            if file.endswith(".tex") and contains_documentclass(source):
                found_main_source = True
                destination = working_source
            else:
                destination = f"{working_directory}/{file}"
            
            if os.path.isdir(source):
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copyfile(source, destination)
        # add extraction script.
        dir = os.path.dirname(os.path.realpath(__file__))
        shutil.copy(f"{dir}/extthm.sty", working_directory)
        
        if not found_main_source:
            return stats.add_main_not_found(paper)

        # insert extraction package in the source file.
        extraction_code_inserted = False
        source_file = open(working_source, "rb")
        content = source_file.readlines()
        source_file.close()
        source_file = open(working_source, "wb")
        for line in content:
            if line.startswith(b"\\newtheorem") and not extraction_code_inserted:
                extraction_code_inserted = True
                line = line.replace(
                    b"\\newtheorem",
                    b"%EXTRACTING\n"
                    b"\\usepackage{./extthm}\n"
                    b"%ENDEXTRACTING\n"
                    b"\\newtheorem"
                )
            
            if line.startswith(b"\\begin{document}") and not extraction_code_inserted:
                line = line.replace(
                    b"\\begin{document}",
                    b"%EXTRACTING\n"
                    b"\\usepackage{./extthm}\n"
                    b"%ENDEXTRACTING\n"
                    b"\\newtheorem{theorem}{Theorem}\n"
                    b"\\begin{document}"
                )
            
            source_file.write(line)
        source_file.close()
       
        latex_cmd = ["pdflatex", "-interaction=batchmode", f"-output-directory={working_directory}", working_source]
        
        failure = False
        for _ in range(2):
            subprocess.run(["timeout", "40s"] + latex_cmd, stdout=subprocess.DEVNULL, cwd=working_directory)
            with open(f"{working_directory}/{paper}.log","rb") as f:
                for line in f.readlines():
                    if b"TeX capacity exceeded" in line:
                        return stats.add_oom(paper)
                    elif b"No pages of output." in line:
                        return stats.add_nop(paper)
                    elif b"errors; please try again.)" in line:
                        return stats.add_err(paper)
                    elif b"! Emergency stop." in line:
                        return stats.add_err(paper)
                    elif b"Fatal error occurred" in line:
                        return stats.add_unk(paper)
            if failure:
                break
            
        if not failure:
            if os.path.exists(f"{working_directory}/{paper}.pdf"):
                shutil.move(f"{working_directory}/{paper}.pdf", f"{target_directory}/{paper}.pdf")
                return stats.add_success(paper)
            else:
                return stats.add_unk(paper)

    else: # n_tex == 0:
        return stats.add_no_tex(paper)



def process_file(i, n_papers, paper):
    paper = paper.strip() # remove trailing whitespace

    result = process_paper(paper)
    print("{:04.1f}|{}: {}".format(100*i/n_papers, paper, result))


def run():
    article_list = open(f"{SOURCE_PATH}/CC.txt","r")    

    # Create working directories if they don't exist.
    for x in [WORKING_PATH, TARGET_PATH, LOGS_PATH]:
        ensuredir(x)

    start_at = 0
    end_at   = -1

    # for each paper, copy pdf, extract the theorems and proofs.
    todo        = list(article_list.readlines())[start_at:end_at]
    n_papers  = len(todo)

    Parallel(n_jobs=-1, require='sharedmem')(delayed(process_file)(i, n_papers, paper) for (i, paper) in enumerate(todo))

    print("Done!")
    stats.print_statistics()

    date = datetime.now().strftime("%d-%m")
    stats.save_statistics(f"{LOGS_PATH}/{date}-source-to-pdf.log")

if __name__ == "__main__":
    run()

    
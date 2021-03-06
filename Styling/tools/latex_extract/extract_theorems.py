#!/bin/python3
import os, sys, shutil, fileinput, subprocess, re
from datetime import datetime
from joblib import Parallel, delayed
import argparse

EXTTHM_STRATEGY = "override-env" # "override-newtheorem" # | override-env

def ensuredir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


LIST_RESULTS = [
    "theorem",
    "claim",
    "case",
    "conjecture",
    "corollary",
    "definition",
    "lemma",
    "example",
    "exercice",
    "lemma",
    "note",
    "problem",
    "property",
    "proposition",
    "question",
    "solution",
    "remark",
    "fact",
    "hypothesis",
    "observation",
]


class PreprocessStatistics:
    def __init__(self):
        self.success= []
        self.no_tex = []
        self.main_not_found = []
        self.no_insert = []
        self.no_pdf = []
        self.oom    = []
        self.nop    = []
        self.err    = []
        self.unk    = []
        self.pdflink= []
        self.nores  = []

        self.count_results = {}

    def print_statistics(self):
        print("Statistics:")
        print(f"{len(self.success)} extracted.")

        n_fail = sum(len(x) for x in [self.no_tex, self.no_pdf, self.main_not_found,\
                                      self.no_insert, self.oom, self.nop, self.err, self.nores, self.unk])

        print(f"{n_fail} extraction failed:")
        print(f"{len(self.no_tex)} had no .tex sources.")
        print(f"{len(self.main_not_found)} could not find main tex.")
        print(f"{len(self.no_insert)} no extraction code inserted.")
        print(f"{len(self.no_pdf)} had no pdf.")
        print(f"{len(self.oom)} went out of memory.")
        print(f"{len(self.nop)} had no theorem.")
        print(f"{len(self.err)} had too many errors.")
        print(f"{len(self.pdflink)} had pdf link error.")
        print(f"{len(self.nores)} had no results.")
        print(f"{len(self.unk)} had unknown.")
        print("Results found:")
        for k,v in self.count_results.items():
            print(f"{k}: {v}")

    def save_statistics(self, target):
        with open(target, "w") as f:
            f.write("OK:"+",".join(self.success)+"\n")
            f.write("NOTEX:"+",".join(self.no_tex)+"\n")
            f.write("MNF:"+",".join(self.main_not_found)+"\n")
            f.write("NOINSERT:"+",".join(self.no_tex)+"\n")
            f.write("NOPDF:"+",".join(self.no_pdf)+"\n")
            f.write("OOM:"+",".join(self.oom)+"\n")
            f.write("NOP:"+",".join(self.nop)+"\n")
            f.write("ERR:"+",".join(self.err)+"\n")
            f.write("PDFLINK:"+",".join(self.pdflink)+"\n")
            f.write("UNK:"+",".join(self.unk)+"\n")
            f.write("NORES:"+",".join(self.nores)+"\n")

    def add_success(self, paper, counts):
        """Extraction has been successful."""
        self.success.append(paper)
        for k,v in counts.items():
            if k not in self.count_results:
                self.count_results[k] = 0
            self.count_results[k] += v
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

    def add_no_insert(self, paper):
        """No code inserted."""
        self.no_insert.append(paper)
        return "NOINSERT"

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
    
    def add_pdflink(self, paper):
        """\pdfendlink ended up in different nesting level than \pdfstartlink."""
        self.pdflink.append(paper)
        return "PDFLINK"

    def add_no_results(self, paper):
        """ no results found. """
        self.nores.append(paper)
        return "NORES"

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

def process_paper(args, paper, paths):
    global stats
    SOURCE_PATH_S = paths['SOURCE']
    TARGET_PATH_S = paths['TARGET']
    WORKING_PATH_S = paths['WORKING']

    paper_dir   = f"{SOURCE_PATH_S}/{paper}"
    target_directory = f"{TARGET_PATH_S}/{paper}"
    ensuredir(target_directory)

    ## Import check that full text PDF exists.
    #pdf_type = filetype.guess(pdf_path)
    #if pdf_type is None or pdf_type.mime != "application/pdf":
        #return stats.add_no_pdf(paper)

    # shutil.copy(pdf_path, f"{target_directory}/{paper}.pdf")

    if not os.path.exists(paper_dir):
        return stats.add_no_tex(paper)  
    
    if not args.regenerate and os.path.exists(f"{target_directory}/{paper}.pdf"):
        return stats.add_already_done(paper)
    
    ## Inject extraction module to gather training data.
    source_files     = os.listdir(paper_dir)
    # check papers that have a single tex source.
    n_tex = len(list(filter(lambda x: x.endswith(".tex"), source_files)))
    if n_tex >= 1:
        working_directory = f"{WORKING_PATH_S}/{paper}/"
        ensuredir(working_directory)

        # Import whole directory and find main tex source.
        found_main_source = False
        for file in source_files:
            source = f"{paper_dir}/{file}"
            destination = f"{working_directory}/{file}"
            

            if file.endswith(".tex") and contains_documentclass(source):
                found_main_source = True
                working_source    = destination
                working_file      = file[:-4]
            
            if os.path.isdir(source):
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copyfile(source, destination)
        # add extraction script.
        dir = os.path.dirname(os.path.realpath(__file__))

        if EXTTHM_STRATEGY == "override-env":
            infile = "extthm-override-env"
        else:
            infile = "extthm-override-newtheorem"

        shutil.copy(f"{dir}/{infile}.sty", f"{working_directory}/extthm.sty")
        
        if not found_main_source:
            return stats.add_main_not_found(paper)

        # insert extraction package in the source file.
        extraction_code_inserted = False
        if EXTTHM_STRATEGY == "override-env":
            source_file = open(working_source, "rb")
            content = source_file.readlines()
            source_file.close()
            source_file = open(working_source, "wb")
            for line in content:

                if line.strip().startswith(b"\\begin{document}"):
                    extraction_code_inserted = True
                    source_file.write(
                        b"%EXTRACTING\n"
                        b"\\usepackage{./extthm}\n"
                        b"%ENDEXTRACTING\n")
                
                source_file.write(line)
            source_file.close()
        elif EXTTHM_STRATEGY == "override-newtheorem":
            input_matcher  = re.compile(rb"\\input\{(.+)\}.*")
            usepkg_matcher = re.compile(rb"\\usepackage\{(.+)\}.*")
            
            def insert(file):
                ok = False
                if not os.path.exists(file):
                    return False
                
                with open(file, "rb+") as f:
                    content = f.readlines()
                    f.seek(0)
                    for line in content:
                        if ok:
                            f.write(line)
                        else:
                            input_match = input_matcher.match(line.strip())
                            pkg_match   = usepkg_matcher.match(line.strip())
                            try:
                                if input_match is not None:
                                    target = input_match.group(1).decode()
                                    if not target.endswith('.tex'):
                                        target += '.tex'
                                    ok = insert(working_directory+"/"+target)
                                elif pkg_match is not None and os.path.exists(working_directory+"/"+pkg_match.group(1).decode()+".sty"):
                                    ok = insert(working_directory+"/"+pkg_match.group(1).decode()+".sty")
                                elif line.strip().startswith(b"\\newtheorem"):
                                    ok = True
                                    f.write(b"\\usepackage{./extthm}\n")
                            except:
                                print("decode error.")
                            f.write(line)
                
                return ok
            extraction_code_inserted = insert(working_source)
        else:
            extraction_code_inserted = False

        if not extraction_code_inserted:
            return stats.add_no_insert(paper)

       
        latex_cmd = ["pdflatex", "-interaction=batchmode", f"-output-directory={working_directory}", working_source]
        
        def remove_eventual_pdf():
            try:
                os.remove(f"{working_directory}/{working_file}.pdf")
            except OSError:
                pass

        results = {}
        for _ in range(2):
            subprocess.run(["timeout", "40s"] + latex_cmd, stdout=subprocess.DEVNULL, cwd=working_directory)
            stat_mode = False
            with open(f"{working_directory}/{working_file}.log","rb") as f:
                for line in f.readlines():
                    if b"TeX capacity exceeded" in line:
                        remove_eventual_pdf()
                        return stats.add_oom(paper)
                    elif b"No pages of output." in line:
                        remove_eventual_pdf()
                        return stats.add_nop(paper)
                    elif b"errors; please try again.)" in line:
                        remove_eventual_pdf()
                        return stats.add_err(paper)
                    elif b"! Emergency stop." in line:
                        remove_eventual_pdf()
                        return stats.add_err(paper)
                    elif b"pdfendlink ended up in different nesting level" in line:
                        remove_eventual_pdf()
                        return stats.add_pdflink(paper)
                    elif b"Fatal error occurred" in line:
                        remove_eventual_pdf()
                        return stats.add_unk(paper)
                    elif b"EXTTHM-STATS" in line:
                        try:
                            spl = line.strip().decode().split(":")
                            if len(spl) == 3:
                                kind, value = spl[1], spl[2]
                                results[kind] = int(value)
                        except:
                            print(paper,":", end="")
                            print(b"Failed to parse line '"+line+b"'")

    
        if sum(v for v in results.values()) == 0:
            return stats.add_no_results(paper)

        if os.path.exists(f"{working_directory}/{working_file}.pdf"):
            shutil.move(f"{working_directory}/{working_file}.pdf", f"{target_directory}/{paper}.pdf")
            return stats.add_success(paper, results)
        else:
            return stats.add_unk(paper)
        

    else: # n_tex == 0:
        return stats.add_no_tex(paper)



def process_file(i, args, n_papers, paper,paths):
    result = process_paper(args, paper,paths)
    print("{:04.1f}|{:12}: {}".format(100*i/n_papers, paper, result))


def run(args, pdfs=None, subdirectory=""):
    WORKING_PATH_S = "%s/%s"%(args.tmp,subdirectory)
    TARGET_PATH_S = "%s/%s"%(args.target,subdirectory)
    LOGS_PATH_S = "%s/%s"%(args.logs,subdirectory)
    SOURCE_PATH_S = "%s/%s"%(args.source,subdirectory)

    paths = {'TARGET': TARGET_PATH_S, 'SOURCE':SOURCE_PATH_S,'WORKING':WORKING_PATH_S}

    # Create working directories if they don't exist.
    for x in [WORKING_PATH_S, TARGET_PATH_S, LOGS_PATH_S]:
        ensuredir(x)

    article_list = os.listdir(SOURCE_PATH_S)    

    # for each paper, copy pdf, extract the theorems and proofs.
    todo        = list(map(lambda x: x.strip(), article_list))
    if pdfs is not None:
        pdfs = set(pdfs)
        todo = list(filter(lambda x: x in pdfs, todo))
    n_papers  = len(todo)

    Parallel(n_jobs=-1, require='sharedmem')(delayed(process_file)(i, args, n_papers, paper,paths) for (i, paper) in enumerate(todo))

    print("Done!")
    stats.print_statistics()

    date = datetime.now().strftime("%d-%m")
    stats.save_statistics(f"{LOGS_PATH_S}/{date}-source-to-pdf.log")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("--tmp", default="/tmp/tkb-extract")
    parser.add_argument("-l", "--logs", default=".")
    parser.add_argument("-r", "--regenerate", action="store_true")
    args = parser.parse_args(sys.argv[1:])

    run(args)

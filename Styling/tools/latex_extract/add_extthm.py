#!/usr/bin/env python3

import os
import re
import shutil
import sys

def contains_documentclass(path):
  with open(path, "rb") as f:
    for line in f:
      if line.strip().startswith(b"\\documentclass"):
        return True
  return False
            
input_matcher  = re.compile(rb"(?:\\input|\\include)(?: *| *\{)([^{} ]+)")
documentclass_matcher  = re.compile(rb"\\documentclass *(?:\[.*\])? *\{(.+)\}")
usepkg_matcher = re.compile(rb"\\usepackage *(?:\[.*\])? *\{(.+)\}")
newtheorem_matcher = re.compile(rb"[^%]*(?<!\\def)\\(newtheorem|declaretheorem|spnewtheorem)( *\[[^]]*\])? *\{|\\def\\@Xthm|.*\\begin *\{document}")

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
        documentclass_match = documentclass_matcher.match(line.strip())
        try:
          if input_match is not None:
            target = input_match.group(1).decode()
            if not target.endswith('.tex'):
              target += '.tex'
            print("Input: " + target)
            ok = insert(out_dir+"/"+target)
          elif pkg_match is not None and os.path.exists(in_dir+"/"+pkg_match.group(1).decode()+".sty"):
              target = pkg_match.group(1).decode()
              print("Package: " + target)
              ok = insert(out_dir+"/"+target+".sty")
          elif documentclass_match is not None and os.path.exists(in_dir+"/"+documentclass_match.group(1).decode()+".cls"):
              ok = insert(out_dir+"/"+documentclass_match.group(1).decode()+".cls")
          elif newtheorem_matcher.match(line.strip()) is not None:
            ok = True
            print("Inserting before: "+line.strip().decode())
            f.write(b"\\usepackage{./extthm}\n")
        except:
          print("decode error.")
        f.write(line)
    return ok

if __name__ == "__main__":
  if len(sys.argv) !=3:
    print(f"Usage: {argv[0]} in_dir out_dir\n")
    sys.exit(1)

  in_dir = sys.argv[1]
  out_dir = sys.argv[2]

  shutil.copytree(in_dir, out_dir)
  ## Inject extraction module to gather training data.
  source_files     = os.listdir(in_dir)
  # check papers that have a single tex source.
  n_tex = len(list(filter(lambda x: x.endswith(".tex"), source_files)))
  if n_tex >= 1:
    # Import whole directory and find main tex source.
    found_main_source = False
    for file in source_files:
        source = f"{in_dir}/{file}"
        destination = f"{out_dir}/{file}"

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

  if found_main_source:
    print("Main source:" + working_source)
    extraction_code_inserted = insert(working_source)
    if not(extraction_code_inserted):
      print("Nothing inserted!")
  else:
    print("Could not find main source!")
  
  for i in os.listdir("packages/"):
    shutil.copy("packages/"+i, out_dir)

# Responsible for indexing files in a folder.
# Given a folder of files the indexer:
# 1. Goes through the files and parses, chunks, and saves chunks with file metadata in an array
# 2. Passes array of file data to embedder --> uploader

from pathlib import Path

def process_folder(folder_path: Path, target_types: tuple[str]):
    
    count = 0

    for root, dirs, files in folder_path.walk(top_down=True):
        for file in files:
            if file.endswith(target_types):
                count += 1
                print(str(root) + ": " + file)
    print("Found " + str(count) + " files with matching types of: " + str(target_types))

path = input("enter directory: ")
p = Path(path)
process_folder(p, (".md", ".pdf", ".txt"))
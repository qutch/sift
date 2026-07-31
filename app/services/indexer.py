# Responsible for indexing files in a folder.
# Given a folder of files the indexer:
# 1. Goes through the files and parses, chunks, and saves chunks with file metadata in an array
# 2. Passes array of file data to embedder --> uploader

from pathlib import Path

def process_folder(folder_path: Path, target_types: tuple[str]) -> list[str]:

    target_files = []

    for root, dirs, files in folder_path.walk(top_down=True):

        # Go through each file
        for file in files:
            # Check if it matches target file types
            if file.endswith(target_types):
                # Add file path to the list of files to process further
                target_files.append(f"{str(root)}/{file}")

    print("Found " + str(len(target_files)) + " files with matching types of: " + str(target_types))
    print(target_files)
    return target_files


from fileParser import Parser

if __name__ == '__main__':
    # path = input("enter directory: ")
    path = '/users/hutch/desktop/desktop/test-folder'
    p = Path(path)

    files = process_folder(p, (".md", ".pdf", ".txt"))
    # test parsing
    p = Parser()
    for file_loc in files:
        out = p.ParseFile(file_loc)
        print("==============")
        print(f"File Name: {out[1].get('name')}")
        print(f'Type: {out[1].get('type')}')
        print(f'Location: {out[1].get('path')}')
        print(f'Size: {out[1].get('size')} bytes')
        print("==============\n")
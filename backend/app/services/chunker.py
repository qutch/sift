# Takes in a string of text and outputs a list of text chunk
# text --> the string of text information
# overlap --> number of characters to overlap
# chunk_size --> number of characters to make each chunk
def ChunkText(text: str, overlap: int, chunk_size: int) -> list[str]:
    chunks = []
    metadata = []
    tags = []

    allowedChunkEndings = [' ', ',', '.', '!', '?', ';', ':']
    textLength = len(text)

    lastChunkIndex = 0 # Keeps track of last chunk index without overlap
    currentIndex = 0 # Keeps track of index with overlap + extensions
    chunkAndOverlapSize = chunk_size + overlap
    currentChunk = ""

    while currentIndex < textLength:
        if lastChunkIndex + chunkAndOverlapSize < textLength:

            # Create current chunk
            currentIndex = lastChunkIndex + chunkAndOverlapSize
            currentChunk = text[lastChunkIndex:currentIndex]

            # Check if chunk naturally ends on a word ending
            curChar = currentChunk[-1]

            if curChar not in allowedChunkEndings:
                # Find the next allowed chunk ending character
                charIndex = currentIndex + 1
                while curChar not in allowedChunkEndings:
                    curChar = text[charIndex]
                    charIndex += 1

                # Add extra to chunk
                currentChunk = text[lastChunkIndex:charIndex]

        else:
            currentChunk = text[lastChunkIndex:]

            # Break out of loop with bad condition
            currentIndex = textLength + 1
        
        # Update last chunk index
        lastChunkIndex += chunk_size

        chunks.append(currentChunk)

    return chunks


def CleanText(text:str) -> str:
    print("cleaning text")
    # Remove any special characters such as '\n', '\t', etc..
    cleanedText = ""
    dirtyText = repr(text)
    toBeRemoved = ['\\n', '\\t', '\\v', '\\r']
    badIndices = []

    for i in range(0, len(dirtyText)):

        if i in badIndices:
            continue

        if dirtyText[i] == '\\':
            # Check patterns
            suspect = dirtyText[i:i+2]
            if suspect in toBeRemoved:
                # Skip over these characters
                badIndices.append(i)
                badIndices.append(i+1)
                continue

        cleanedText += dirtyText[i]

    print(repr(cleanedText))

    return cleanedText

from fileParser import Parser
from llamaService import Summarizer

def main():
    parser = Parser()
    fileLocation = input("enter file location: ")
    userText = parser.ParseFile(fileLocation)
    print(repr(userText))
    cleanedUserText = CleanText(userText)
    result = ChunkText(cleanedUserText, 20, 100)
    print("result length: " + str(len(result)))

    s = Summarizer()

    # test summarization
    for index, chunk in enumerate(result):
        print("\n--== CHUNK " + str(index) + ": " + chunk)
        s1b = s.summarize(3, chunk)
        # s3b = s.summarize(2, chunk)
        print("Summary 1B: " + s1b)
        # print("Summary 3B: " + s3b)
        print("--===============--")

if __name__ == "__main__":
    main()
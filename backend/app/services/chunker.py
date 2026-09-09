from classes.Vector import Vector

"""
Takes in a string of text and outputs a list of text chunk
text --> the string of text information
overlap --> number of characters to overlap
chunk_size --> number of characters to make each chunk
"""

class Chunker:
    
    def __init__(self):
        pass
        
    def ChunkText(self, text: str, overlap: int, chunk_size: int) -> list[str]:
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


    def CleanText(self, text:str) -> str:
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

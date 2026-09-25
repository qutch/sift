from ollama import chat
from pydantic import BaseModel, Field

class FileRelevance(BaseModel):
    filePath: str
    relevance: int = Field(ge=1, le=10)
    reason: str

class RankingResult(BaseModel):
    rankings: list[FileRelevance]

class ChunkSummarizer:

    summaryPrompt = ""

    summaryLevel = {
            1: 'llama3.2:1b',
            2: 'llama3.2:3b',
            3: 'gemma3:1b',
        }

    def __init__(self):
        self.systemPrompt = """You are a keyword extractor. You output ONLY keywords, nothing else.

                            RULES:
                            1. Read the text chunk.
                            2. Pick 3 to 8 SPECIFIC, DISTINCTIVE words or short phrases: proper nouns, names, numbers, dates, technical terms, unique topics.
                            3. If the text has NO proper nouns or numbers, pick the most UNUSUAL or RARE words/phrases instead (e.g. "clockwork birds", "fluttered wings") — never the common ones (the, and, seemed, every, a).
                            4. NEVER output most or all of the words from the original text in their original order. You are SELECTING a few words, not repeating the whole chunk with periods inserted.
                            5. Output must be ON ONE SINGLE LINE. Never use a line break.
                            6. Do NOT write sentences. Do NOT explain. Do NOT add intro or outro text.
                            7. Format is EXACTLY: keyword1. keyword2. keyword3.
                            - Each keyword ends with a period, followed by a space.
                            - No numbering, no bullets, no quotes, no newlines.

                            EXAMPLE 1 (good):
                            Text: "The Amazon rainforest lost 12% of its tree cover in 2023 due to illegal logging in Brazil."
                            Output: Amazon rainforest. 12% tree cover loss. 2023. illegal logging. Brazil.

                            EXAMPLE 2 (good — no proper nouns, so pick unusual phrases):
                            Text: "and tiny clockwork birds whose wings fluttered whenever the weather changed. Every object seemed to carry a story"
                            Output: clockwork birds. fluttering wings. weather changed. objects carry story.

                            EXAMPLE 3 (BAD — do not do this):
                            Text: "and tiny clockwork birds whose wings fluttered whenever the weather changed."
                            Output: and. tiny. clockwork. birds. whose. wings. fluttered. whenever. the. weather. changed.
                            (This is WRONG: it is just the whole sentence with periods added, not selected keywords.)

                        Now extract keywords from the next text chunk. Output on one line only."""

        self.messages = [{'role':'system', 'content': self.systemPrompt}]

    def summarize(self, level: int, chunk: str) -> str:
        
        print("using: " + self.summaryLevel.get(level))

        newMessage = {'role': 'user','content': 'Text: ' + chunk}
        self.messages.append(newMessage)

        response = chat(
            model=Summarizer.summaryLevel.get(level),
            messages=[
                {'role':'system', 'content': self.systemPrompt},
                newMessage
            ]
        )

        return response.message.content


class Summarizer:
    def __init__(self):
        self.model = 'gemma3:1b'
        self.systemPrompt = "You are a document summarizer. Summarize the text provieded in MAXIMUM 1 short sentence with KEYWORDS INCLUDED."
        self.summaryPrompt = "You are a text summarizer. You are to summarize the chunks given to you in order to give it back to the user so they can better understand what they're looking for. Use this prompt for better context. PROMPT: "
    
    def Summarize(self, text: str):
        response = chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': self.systemPrompt},
                {'role': 'user', 'content': text}
            ]
        )

        return response.message.content

    # Summarization method used to return a summary to the user after searching
    def SummarizeResults(self, query: str, chunks: list[dict]):

        resultText = "\n".join(chunk.get('chunkText', '') for chunk in chunks)

        response = chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': self.summaryPrompt + query},
                {'role': 'user', 'content': resultText}
            ]
        )

        return response.message.content

class Ranker:
    def __init__(self):
        # Ranking is a reasoning task (compare query against several
        # candidates), not simple extraction, so it needs a stronger model
        # than the 1b models used elsewhere in this file
        self.model = 'llama3.2:3b'
        self.rankingPrompt = """You are a file relevance ranker. You will be given a user's
                            search query and a numbered list of files, each with a
                            snippet of its content. Score EVERY file listed, exactly
                            once, from 1 (irrelevant) to 10 (highly relevant) based on
                            how well its content relates to the query."""

    # Chunks come back from the vector search grouped by chunk, not by file,
    # so multiple chunks can share the same filePath. Join them into one
    # block of text per file and cap the length so the prompt stays inside
    # the local model's context window.
    def _groupChunksByFile(self, chunks: list[dict], maxCharsPerFile: int = 800) -> dict[str, str]:
        grouped: dict[str, list[str]] = {}
        for chunk in chunks:
            filePath = chunk.get('filePath')
            grouped.setdefault(filePath, []).append(chunk.get('chunkText', ''))

        return {
            filePath: ' '.join(texts)[:maxCharsPerFile]
            for filePath, texts in grouped.items()
        }

    # Ranks the files that produced the given chunks by relevance to the query.
    # metadata, keyed by filePath (e.g. from DBService.GetMetadataForFiles),
    # optionally supplies a summary so the model has more than a raw chunk to
    # go on. Returns a list of {filePath, relevance, reason} dicts, most
    # relevant first.
    def RankFiles(self, query: str, chunks: list[dict], metadata: dict[str, dict] | None = None, topK: int | None = None) -> list[dict]:
        fileTexts = self._groupChunksByFile(chunks)
        if not fileTexts:
            return []

        metadata = metadata or {}
        entries = []
        for i, (path, text) in enumerate(fileTexts.items()):
            summary = metadata.get(path, {}).get('summary')
            summaryLine = f"\n   summary: {summary}" if summary else ""
            entries.append(f"{i + 1}. filePath: {path}{summaryLine}\n   content: {text}")

        fileList = "\n".join(entries)
        userPrompt = f"Query: {query}\n\nFiles:\n{fileList}"

        response = chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': self.rankingPrompt},
                {'role': 'user', 'content': userPrompt},
            ],
            # Structured output is what makes this reliable with a small
            # local model - without a forced schema, gemma/llama 1b-3b
            # models drift from free-form ranking instructions
            format=RankingResult.model_json_schema(),
        )

        try:
            result = RankingResult.model_validate_json(response.message.content)
        except ValueError as e:
            print(f"Ranker: failed to parse model output ({e}); returning unranked files")
            return [{'filePath': path, 'relevance': None, 'reason': None} for path in fileTexts]

        ranked = sorted(result.rankings, key=lambda r: r.relevance, reverse=True)

        if topK is not None:
            ranked = ranked[:topK]

        return [r.model_dump() for r in ranked]
from ollama import chat

class Summarizer:

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
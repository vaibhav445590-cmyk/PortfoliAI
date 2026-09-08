"""
PortfoliAI — Parser Pipeline

Tries registered parsers in priority order and returns
the first successful result. If all parsers fail,
raises RuntimeError (should never happen if the regex
parser is registered — it always succeeds).

Usage:
    from parser_pipeline import create_default_pipeline

    pipeline = create_default_pipeline()
    result, parser_name = pipeline.parse(resume_text)
"""

from resume_data import ResumeData
from parser_base import BaseResumeParser


class ParserPipeline:
    """
    Fallback chain of resume parsers.

    Parsers are tried in registration order.
    The first parser that:
        1. Reports is_available() == True
        2. Returns a non-None ResumeData from parse()
    wins, and its result is returned.
    """

    def __init__(self):
        self._parsers: list[BaseResumeParser] = []


    def register(self, parser: BaseResumeParser):
        """
        Add a parser to the pipeline.

        Parsers are tried in the order they are
        registered. Register the best parser first,
        and the fallback parser last.
        """
        self._parsers.append(parser)


    @property
    def parsers(self) -> list[BaseResumeParser]:
        """Return the list of registered parsers."""
        return list(self._parsers)


    def parse(self, text: str) -> tuple[ResumeData, str]:
        """
        Parse resume text using the best available parser.

        Returns:
            (ResumeData, parser_name) — the parsed data
            and the name of the parser that produced it.

        Raises:
            RuntimeError — if all parsers fail (should
            never happen with the regex fallback).
        """

        errors = []

        for parser in self._parsers:

            # --------------------------------------------------
            # CHECK AVAILABILITY
            # --------------------------------------------------

            try:

                if not parser.is_available():
                    continue

            except Exception as e:

                errors.append(
                    f"{parser.name()}: availability check failed — {e}"
                )

                continue


            # --------------------------------------------------
            # PARSE
            # --------------------------------------------------

            try:

                result = parser.parse(text)

                if result is not None:
                    return result, parser.name()

            except Exception as e:

                errors.append(
                    f"{parser.name()}: parse failed — {e}"
                )

                continue


        # --------------------------------------------------
        # ALL FAILED
        # --------------------------------------------------

        error_details = "\n".join(errors)

        raise RuntimeError(
            f"All parsers failed.\n{error_details}"
        )


# ============================================================
# DEFAULT PIPELINE FACTORY
# ============================================================

def create_default_pipeline() -> ParserPipeline:
    """
    Create the default parser pipeline with all
    available parsers registered in priority order.

    Currently registered:
        1. Enhanced Regex (always available)

    Future parsers (Ollama, spaCy, OpenAI) will be
    added here when implemented.
    """

    from parsers.regex_parser import EnhancedRegexParser

    pipeline = ParserPipeline()

    # --------------------------------------------------------
    # FUTURE: register AI parsers here
    # --------------------------------------------------------
    #
    # from parsers.ollama_parser import OllamaResumeParser
    # pipeline.register(OllamaResumeParser())
    #
    # from parsers.spacy_parser import SpacyResumeParser
    # pipeline.register(SpacyResumeParser())
    #

    # --------------------------------------------------------
    # FALLBACK: Enhanced Regex (always available)
    # --------------------------------------------------------

    pipeline.register(EnhancedRegexParser())

    return pipeline

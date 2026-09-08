"""
PortfoliAI — Parser Base Class

Abstract interface that all resume parsers must implement.
This ensures every parser (regex, spaCy, Ollama, OpenAI)
is interchangeable and works with the pipeline.
"""

from abc import ABC, abstractmethod
from resume_data import ResumeData


class BaseResumeParser(ABC):
    """
    Abstract base class for all resume parsers.

    Subclasses must implement:
        - name()          → human-readable parser name
        - is_available()  → whether the parser can run
        - parse()         → parse text into ResumeData
    """

    @abstractmethod
    def name(self) -> str:
        """
        Return a human-readable name for this parser.

        Examples: "Enhanced Regex", "spaCy NER", "Ollama"
        """
        ...


    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this parser can run right now.

        Return True if all required dependencies,
        services, and API keys are available.

        The regex parser should always return True.
        """
        ...


    @abstractmethod
    def parse(self, text: str) -> ResumeData | None:
        """
        Parse resume text into structured ResumeData.

        Return a ResumeData instance on success.
        Return None if the parser fails or produces
        no useful output.

        The pipeline will try the next parser on None.
        """
        ...

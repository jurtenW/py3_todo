"""MockUI – scriptable mock for the UIBackend protocol."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class MockUI:
    """Scriptable mock UI that records all calls and returns queued responses.

    Usage:
        mock = MockUI()
        mock.queue_menu_response("Toggle Done")
        mock.queue_menu_response("Back")
        mock.queue_text_response("My task")

        # Pass `mock` to TodoApp instead of RofiUI.
        # After execution:
        #   mock.menu_calls  → list of (prompt, options)
        #   mock.text_calls  → list of (prompt, initial)
    """

    def __init__(self) -> None:
        self.menu_calls: List[Tuple[str, List[str]]] = []
        self.text_calls: List[Tuple[str, str]] = []
        self._menu_responses: List[Optional[str]] = []
        self._text_responses: List[Optional[str]] = []

    # -- queue helpers --------------------------------------------------------

    def queue_menu_response(self, response: Optional[str]) -> None:
        self._menu_responses.append(response)

    def queue_text_response(self, response: Optional[str]) -> None:
        self._text_responses.append(response)

    def queue_menu_responses(self, *responses: Optional[str]) -> None:
        self._menu_responses.extend(responses)

    def queue_text_responses(self, *responses: Optional[str]) -> None:
        self._text_responses.extend(responses)

    # -- UIBackend interface --------------------------------------------------

    def show_menu(self, prompt: str, options: List[str]) -> Optional[str]:
        self.menu_calls.append((prompt, list(options)))
        if self._menu_responses:
            return self._menu_responses.pop(0)
        return None

    def ask_text(self, prompt: str, initial: str = "") -> Optional[str]:
        self.text_calls.append((prompt, initial))
        if self._text_responses:
            return self._text_responses.pop(0)
        return None

    # -- diagnostics ----------------------------------------------------------

    def menu_prompts(self) -> List[str]:
        return [prompt for prompt, _ in self.menu_calls]

    def menu_option_sets(self) -> List[List[str]]:
        return [opts for _, opts in self.menu_calls]

    def assert_menu_shown(self, prompt_contains: str) -> None:
        """Assert that a menu with a prompt containing the given text was shown."""
        matching = [p for p, _ in self.menu_calls if prompt_contains in p]
        assert matching, (
            f"No menu prompt containing {prompt_contains!r} found. "
            f"Prompts: {[p for p, _ in self.menu_calls]}"
        )

    def assert_asked_for(self, prompt_contains: str) -> None:
        """Assert that ask_text was called with a prompt containing the given text."""
        matching = [p for p, _ in self.text_calls if prompt_contains in p]
        assert matching, (
            f"No ask_text prompt containing {prompt_contains!r} found. "
            f"Prompts: {[p for p, _ in self.text_calls]}"
        )

"""Append-mode joining: voice builds on the draft, never replaces it."""

from __future__ import annotations

from darkevox.ui.draft import Draft, join_utterance


def test_join_into_empty_draft_is_verbatim() -> None:
    assert join_utterance("", "Hello there.") == "Hello there."
    assert join_utterance("   ", "Hello there.") == "Hello there."


def test_join_after_finished_sentence_keeps_capital() -> None:
    joined = join_utterance("First thought.", "Second thought here.")
    assert joined == "First thought. Second thought here."


def test_join_mid_sentence_lowercases_the_continuation() -> None:
    joined = join_utterance("I wanted to say", "That we should ship on Friday.")
    assert joined == "I wanted to say that we should ship on Friday."


def test_join_mid_sentence_keeps_i_acronyms_and_dictionary_terms() -> None:
    assert join_utterance("tomorrow", "I will call") == "tomorrow I will call"
    assert join_utterance("send it to", "NASA today") == "send it to NASA today"
    joined = join_utterance("ping", "Jake about it", keep_words=("Jake",))
    assert joined == "ping Jake about it"


def test_join_after_newline_starts_fresh_line() -> None:
    joined = join_utterance("First paragraph.\n", "Second paragraph.")
    assert joined == "First paragraph.\nSecond paragraph."


def test_empty_utterance_changes_nothing() -> None:
    assert join_utterance("keep me", "") == "keep me"
    assert join_utterance("keep me", "   ") == "keep me"


def test_draft_commit_appends_and_empty_session_cannot_wipe() -> None:
    draft = Draft()
    draft.begin_session("")
    assert draft.commit("First take.") == "First take."
    draft.begin_session("First take.")
    # The accidental-tap case: an empty session leaves the draft untouched.
    assert draft.commit("") == "First take."
    draft.begin_session("First take.")
    assert draft.commit("Second take.") == "First take. Second take."


def test_draft_render_previews_without_committing() -> None:
    draft = Draft()
    draft.begin_session("Base text.")
    assert draft.render("live words") == "Base text. live words"
    assert draft.base == "Base text."


def test_draft_undo_rolls_back_one_take_at_a_time() -> None:
    draft = Draft()
    draft.begin_session("")
    draft.commit("One.")
    draft.begin_session("One.")
    draft.commit("Two.")
    assert draft.can_undo
    assert draft.undo() == "One."
    assert draft.undo() == ""
    assert draft.undo() is None


def test_draft_sync_adopts_manual_edits() -> None:
    draft = Draft()
    draft.begin_session("")
    draft.commit("Spoken text.")
    draft.sync("Spoken text, edited by hand.")
    assert draft.base == "Spoken text, edited by hand."

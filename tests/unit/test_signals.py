"""Unit tests for locus.feedback.signals — inferred disagreement detection (#19)."""

import pytest
from locus.feedback.signals import SignalResult, classify_message, format_inferred_note


# ---------------------------------------------------------------------------
# Fail signals
# ---------------------------------------------------------------------------

class TestFailSignals:
    @pytest.mark.parametrize("text", [
        "that's wrong",
        "That's wrong",
        "THAT'S WRONG",
        "that is wrong",
        "that's incorrect",
        "that is incorrect",
        "that's not right",
        "that is not right",
        "you got that wrong",
        "wrong answer",
        "not correct",
        "incorrect",
        "no, that's not what I asked",
        "no, that is wrong",
    ])
    def test_detects_fail(self, text):
        result = classify_message(text)
        assert result is not None
        assert result.quality == "fail"

    def test_fail_confidence_exact(self):
        result = classify_message("that's wrong")
        assert result.confidence == 1.0

    def test_fail_substring_confidence(self):
        result = classify_message("hmm, that's wrong I think")
        assert result is not None
        assert result.quality == "fail"
        assert result.confidence == 0.6

    def test_fail_returns_matched_pattern(self):
        result = classify_message("that's wrong")
        assert result.matched_pattern == "that's wrong"


# ---------------------------------------------------------------------------
# Partial signals
# ---------------------------------------------------------------------------

class TestPartialSignals:
    @pytest.mark.parametrize("text", [
        "actually, the IP is 192.168.1.1",
        "Actually that's not quite right",
        "not quite",
        "almost, but you missed the port",
        "close, but incomplete",
        "almost right",
        "you missed the namespace",
        "you're missing the port",
        "that's not complete",
        "that didn't answer my question",
        "doesn't answer my question",
        "not what i asked",
        "try again",
        "that's only part of the answer",
    ])
    def test_detects_partial(self, text):
        result = classify_message(text)
        assert result is not None
        assert result.quality == "partial"

    def test_partial_confidence_exact(self):
        result = classify_message("not quite")
        assert result.confidence == 0.8

    def test_partial_prefix_confidence(self):
        result = classify_message("actually, you got the version right but missed the namespace")
        assert result is not None
        assert result.quality == "partial"
        assert result.confidence == 0.8


# ---------------------------------------------------------------------------
# No signal (should return None)
# ---------------------------------------------------------------------------

class TestNoSignal:
    @pytest.mark.parametrize("text", [
        "thanks",
        "ok",
        "got it",
        "yes that's right",
        "perfect",
        "let's continue",
        "what about the other service?",
        "can you also check the port?",
        "",
        "   ",
    ])
    def test_no_signal(self, text):
        assert classify_message(text) is None


# ---------------------------------------------------------------------------
# False positive guards
# ---------------------------------------------------------------------------

class TestFalsePositiveGuards:
    def test_long_message_ignored(self):
        # > 300 chars even with a fail pattern embedded
        long = "that's wrong " + "x" * 300
        assert classify_message(long) is None

    def test_url_ignored(self):
        assert classify_message("that's wrong, see https://example.com for the fix") is None

    def test_code_block_ignored(self):
        assert classify_message("that's wrong\n```bash\ncurl -v\n```") is None

    def test_inline_code_ignored(self):
        assert classify_message("that's wrong, use `kubectl get pods` instead") is None

    def test_file_path_ignored(self):
        assert classify_message("that's wrong, check ./config/settings.yaml") is None

    def test_slash_command_ignored(self):
        assert classify_message("/locus feedback fail") is None

    def test_exactly_300_chars_not_ignored(self):
        # Exactly 300 — should still classify
        text = "that's wrong" + " " * (300 - len("that's wrong"))
        assert len(text) == 300
        result = classify_message(text)
        assert result is not None

    def test_301_chars_ignored(self):
        text = "that's wrong" + " " * (301 - len("that's wrong"))
        assert classify_message(text) is None


# ---------------------------------------------------------------------------
# Confidence threshold
# ---------------------------------------------------------------------------

class TestConfidence:
    def test_fail_exact_is_1_0(self):
        assert classify_message("incorrect").confidence == 1.0

    def test_partial_exact_is_0_8(self):
        assert classify_message("try again").confidence == 0.8

    def test_substring_is_0_6(self):
        result = classify_message("hmm I think that's wrong though")
        assert result.confidence == 0.6

    def test_fail_beats_partial_when_both_present(self):
        # "actually that's wrong" — fail pattern should win (checked first)
        result = classify_message("actually that's wrong")
        assert result is not None
        assert result.quality == "fail"


# ---------------------------------------------------------------------------
# format_inferred_note
# ---------------------------------------------------------------------------

class TestFormatNote:
    def test_includes_confidence(self):
        result = SignalResult("fail", 1.0, "that's wrong")
        note = format_inferred_note(result, "that's wrong")
        assert "confidence: 1.0" in note

    def test_includes_original_message(self):
        result = SignalResult("partial", 0.8, "not quite")
        note = format_inferred_note(result, "not quite right")
        assert "not quite right" in note

    def test_truncates_long_original(self):
        result = SignalResult("partial", 0.6, "not quite")
        long = "not quite " + "x" * 200
        note = format_inferred_note(result, long)
        assert "…" in note
        assert len(note) < len(long) + 50

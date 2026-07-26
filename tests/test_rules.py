import unittest

from vesper.models import ExpectedLabel, Status
from vesper.rules import (
    AUTHORIZED_FILL_ML,
    GOVERNMENT_WARNING,
    extract_regulated_values,
    validate_expected,
)
from vesper.service import verify_label_text


GOOD_TEXT = f"""
VESPER RESERVE
VODKA
40% ALCOHOL BY VOLUME (80 PROOF)
750 mL
{GOVERNMENT_WARNING}
"""


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.expected = ExpectedLabel("Vesper Reserve", "Vodka", 40.0, 750)

    def test_perfect_label_matches(self):
        report = verify_label_text(GOOD_TEXT, self.expected)
        self.assertEqual(report.overall_status, Status.MATCH)
        self.assertTrue(all(c.status == Status.MATCH for c in report.checks))

    def test_capitalization_and_punctuation_are_normalized(self):
        text = (
            GOOD_TEXT.replace("VESPER RESERVE", "Vesper, Reserve!")
            .replace("\nVODKA\n", "\nvodka\n")
        )
        report = verify_label_text(text, self.expected)
        self.assertEqual(report.overall_status, Status.MATCH)

    def test_ocr_joined_brand_words_are_normalized(self):
        report = verify_label_text(GOOD_TEXT.replace("VESPER RESERVE", "VESPERRESERVE"), self.expected)
        check = next(c for c in report.checks if c.field == "Brand name")
        self.assertEqual(check.status, Status.MATCH)

    def test_wrong_abv_mismatches(self):
        report = verify_label_text(GOOD_TEXT.replace("40% ALCOHOL", "45% ALCOHOL"), self.expected)
        check = next(c for c in report.checks if c.field == "Alcohol content")
        self.assertEqual(check.status, Status.MISMATCH)

    def test_proof_must_equal_twice_abv(self):
        report = verify_label_text(GOOD_TEXT.replace("80 PROOF", "86 PROOF"), self.expected)
        check = next(c for c in report.checks if c.field == "Proof (optional)")
        self.assertEqual(check.status, Status.MISMATCH)

    def test_abv_abbreviation_alone_is_not_accepted(self):
        values = extract_regulated_values(GOOD_TEXT.replace("ALCOHOL BY VOLUME", "ABV"))
        self.assertIsNone(values["abv"])

    def test_liters_are_converted_to_ml(self):
        values = extract_regulated_values(GOOD_TEXT.replace("750 mL", "0.750 L"))
        self.assertEqual(values["net_contents_ml"], 750)

    def test_missing_warning_mismatches(self):
        report = verify_label_text(GOOD_TEXT.replace(GOVERNMENT_WARNING, ""), self.expected)
        check = next(c for c in report.checks if c.field == "Government warning")
        self.assertEqual(check.status, Status.MISMATCH)

    def test_warning_capitalization_variance_requires_review(self):
        report = verify_label_text(
            GOOD_TEXT.replace("GOVERNMENT WARNING:", "Government Warning:"),
            self.expected,
        )
        check = next(c for c in report.checks if c.field == "Government warning")
        self.assertEqual(check.status, Status.POSSIBLE_MATCH)

    def test_current_standard_fills_include_2026_sizes(self):
        for size in (1800, 945, 720, 710, 570, 475, 355, 331):
            self.assertIn(size, AUTHORIZED_FILL_ML)

    def test_invalid_expected_fill_is_rejected(self):
        errors = validate_expected(ExpectedLabel("A", "Vodka", 40, 330))
        self.assertTrue(any("standard of fill" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

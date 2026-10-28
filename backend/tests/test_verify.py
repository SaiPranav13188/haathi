from app.verify.verifier import check_offline

PASSAGE = "PM-SYM is a voluntary and contributory pension scheme for unorganised workers such as street vendors."


def test_citation_markers_are_not_numbers():
    assert check_offline("PM-SYM is a pension scheme for unorganised workers [2].", PASSAGE, False) == "supported"


def test_wrong_number_is_unsupported():
    assert check_offline("PM-SYM pays ₹5,000 a month [1].", PASSAGE, False) == "unsupported"


def test_indian_grouping_matches():
    assert check_offline("Cover of ₹2,00,000", "life cover of ₹2,00,000 for ₹436", True) == "supported"

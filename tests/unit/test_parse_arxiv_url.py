import util


def test_parse_abs_url():
    arxiv_id, canonical_url = util.parse_arxiv_url("https://arxiv.org/abs/2511.09030")
    assert arxiv_id == "2511.09030"
    assert canonical_url == "https://arxiv.org/abs/2511.09030"


def test_parse_pdf_url():
    arxiv_id, canonical_url = util.parse_arxiv_url("https://arxiv.org/pdf/2511.09030.pdf")
    assert arxiv_id == "2511.09030"
    assert canonical_url == "https://arxiv.org/abs/2511.09030"


def test_parse_bare_id():
    arxiv_id, canonical_url = util.parse_arxiv_url("2511.09030v2")
    assert arxiv_id == "2511.09030v2"
    assert canonical_url == "https://arxiv.org/abs/2511.09030v2"


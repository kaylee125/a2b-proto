import pytest
from tools import molit

XML = """<response><header><resultCode>000</resultCode></header><body><items>
<item><aptNm>예시단지</aptNm><aptDong>101동</aptDong><floor>10</floor><excluUseAr>84.97</excluUseAr>
<dealYear>2026</dealYear><dealMonth>1</dealMonth><dealDay>5</dealDay><dealAmount>90,000</dealAmount>
<buildYear>2018</buildYear><dealingGbn>중개거래</dealingGbn><cdealType></cdealType><umdNm>예시동</umdNm></item>
</items><totalCount>1</totalCount></body></response>"""


def test_parse_trades_maps_fields():
    rows, total = molit.parse_trades(XML)
    assert total == 1 and rows[0]["amount"] == 90000 and rows[0]["date"] == "2026-01-05"
    assert rows[0]["canceled"] is False and rows[0]["area"] == 84.97


def test_parse_trades_raises_on_api_error():
    with pytest.raises(RuntimeError):
        molit.parse_trades("<response><header><resultCode>30</resultCode><resultMsg>KEY</resultMsg></header></response>")

from gmind.markdown import parse_markdown_outline
from gmind.mind import content_summary, render_markdown


def test_parse_heading_and_nested_bullets():
    content = parse_markdown_outline(
        """# Center

- A
  - A1
  - A2
- B
"""
    )

    assert content["root"]["data"]["text"] == "Center"
    assert content["root"]["children"][0]["data"]["text"] == "A"
    assert content["root"]["children"][0]["children"][1]["data"]["text"] == "A2"
    assert content_summary(content)["node_count"] == 5


def test_parse_paragraph_under_last_node():
    content = parse_markdown_outline(
        """# Center

- A
  More detail
"""
    )

    assert content["root"]["children"][0]["data"]["text"] == "A\nMore detail"


def test_render_markdown_round_trip_shape():
    content = parse_markdown_outline("# Center\n\n- A\n  - A1\n")

    rendered = render_markdown(content)

    assert rendered.startswith("# Center\n")
    assert "- A\n  - A1\n" in rendered

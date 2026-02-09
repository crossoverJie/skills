import unittest
from auto_blog_cover import replace_frontmatter_fields


class TestReplaceFrontmatterFields(unittest.TestCase):

    def test_single_field_replacement(self):
        content = "---\nbanner_img: old_url\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img"], "https://new.img/cover.png")
        self.assertIn("banner_img: https://new.img/cover.png", result)
        self.assertNotIn("old_url", result)

    def test_multiple_fields(self):
        content = "---\nbanner_img: old1\nindex_img: old2\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img", "index_img"], "https://new.img/cover.png")
        self.assertIn("banner_img: https://new.img/cover.png", result)
        self.assertIn("index_img: https://new.img/cover.png", result)
        self.assertNotIn("old1", result)
        self.assertNotIn("old2", result)

    def test_existing_http_url(self):
        content = "---\nbanner_img: https://old.example.com/image.png\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img"], "https://new.img/cover.png")
        self.assertIn("banner_img: https://new.img/cover.png", result)
        self.assertNotIn("old.example.com", result)

    def test_extra_whitespace_after_colon(self):
        content = "---\nbanner_img:  old_url\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img"], "https://new.img/cover.png")
        self.assertIn("banner_img:  https://new.img/cover.png", result)
        self.assertNotIn("old_url", result)

    def test_field_not_in_content(self):
        content = "---\ntitle: My Post\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img"], "https://new.img/cover.png")
        self.assertEqual(content, result)

    def test_preserve_other_fields(self):
        content = "---\ntitle: My Post\ndate: 2025-01-01\nbanner_img: old_url\ntags: [python]\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img"], "https://new.img/cover.png")
        self.assertIn("title: My Post", result)
        self.assertIn("date: 2025-01-01", result)
        self.assertIn("tags: [python]", result)
        self.assertIn("banner_img: https://new.img/cover.png", result)

    def test_quoted_value(self):
        content = '---\nbanner_img: "old_url"\n---\n'
        result = replace_frontmatter_fields(content, ["banner_img"], "https://new.img/cover.png")
        self.assertIn("banner_img: https://new.img/cover.png", result)
        self.assertNotIn("old_url", result)

    def test_url_with_special_chars(self):
        url = "https://cdn.example.com/img.png?x=1&y=2"
        content = "---\nbanner_img: old_url\n---\n"
        result = replace_frontmatter_fields(content, ["banner_img"], url)
        self.assertIn(f"banner_img: {url}", result)
        self.assertNotIn("old_url", result)


if __name__ == "__main__":
    unittest.main()

import unittest

import publish_next as app


class InstagramPublishingTests(unittest.TestCase):
    def test_post_without_image_is_not_reported_as_sent(self) -> None:
        post = {"title": "Test", "text": "Text"}

        with self.assertRaisesRegex(RuntimeError, "requires an image"):
            app.publish_instagram(post, None)


if __name__ == "__main__":
    unittest.main()

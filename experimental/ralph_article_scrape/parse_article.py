#!/usr/bin/env python3
"""Parse the Ralph article and identify all media elements."""

from html.parser import HTMLParser
import json

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_article = False
        self.in_paragraph = False
        self.in_heading = False
        self.heading_level = 0
        self.content = []
        self.current_text = []
        self.media_items = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Article content container
        if tag == 'article' or ('class' in attrs_dict and 'content' in attrs_dict.get('class', '')):
            self.in_article = True

        # Headings
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.in_heading = True
            self.heading_level = int(tag[1])

        # Paragraphs
        if tag == 'p':
            self.in_paragraph = True

        # Images
        if tag == 'img':
            src = attrs_dict.get('src', '')
            alt = attrs_dict.get('alt', '')
            if src:
                # Make URL absolute if needed
                if src.startswith('/'):
                    src = 'https://ghuntley.com' + src
                self.media_items.append({
                    'type': 'image',
                    'url': src,
                    'alt': alt,
                    'placeholder': f"[IMAGE: {alt or 'Illustration'}]"
                })
                self.content.append({
                    'type': 'image',
                    'url': src,
                    'alt': alt
                })

        # Videos
        if tag == 'video':
            src = attrs_dict.get('src', '')
            if src:
                if src.startswith('/'):
                    src = 'https://ghuntley.com' + src
                self.media_items.append({
                    'type': 'video',
                    'url': src,
                    'placeholder': '[VIDEO]'
                })
                self.content.append({
                    'type': 'video',
                    'url': src
                })

        # External links (particularly tweets)
        if tag == 'a':
            href = attrs_dict.get('href', '')
            if 'twitter.com' in href or 'x.com' in href:
                self.media_items.append({
                    'type': 'tweet',
                    'url': href,
                    'placeholder': f'[TWEET: {href}]'
                })

        # Blockquotes (often contain embedded content)
        if tag == 'blockquote':
            classes = attrs_dict.get('class', '')
            if 'twitter' in classes or 'tweet' in classes:
                self.content.append({
                    'type': 'tweet_embed',
                    'classes': classes
                })

    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if self.in_heading:
                text = ''.join(self.current_text).strip()
                if text:
                    self.content.append({
                        'type': 'heading',
                        'level': self.heading_level,
                        'text': text
                    })
                self.current_text = []
                self.in_heading = False

        if tag == 'p':
            if self.in_paragraph:
                text = ''.join(self.current_text).strip()
                if text:
                    self.content.append({
                        'type': 'paragraph',
                        'text': text
                    })
                self.current_text = []
                self.in_paragraph = False

    def handle_data(self, data):
        if self.in_heading or self.in_paragraph:
            self.current_text.append(data)

def main():
    with open('/tmp/ralph_article.html', 'r') as f:
        html = f.read()

    parser = ArticleParser()
    parser.feed(html)

    # Output media items
    print("=== MEDIA ITEMS ===")
    for i, item in enumerate(parser.media_items, 1):
        print(f"\n{i}. {item['type'].upper()}")
        print(f"   URL: {item['url']}")
        if 'alt' in item:
            print(f"   Alt: {item['alt']}")

    # Save content structure
    with open('/tmp/article_structure.json', 'w') as f:
        json.dump({
            'content': parser.content,
            'media': parser.media_items
        }, f, indent=2)

    print(f"\n\nTotal media items found: {len(parser.media_items)}")
    print("Structure saved to /tmp/article_structure.json")

if __name__ == '__main__':
    main()

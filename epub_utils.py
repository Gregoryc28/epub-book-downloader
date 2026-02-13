"""
Utilities for inspecting and modifying EPUB page navigation.

Key constant:
    WORDS_PER_PAGE  — Change this value to adjust how many words
                      constitute one "page" when generating approximate
                      page numbers.  Default is 300.
"""

import os
import shutil
import subprocess

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString

# ──────────────────────────────────────────────────────────
#  Easily adjustable: number of words per page
# ──────────────────────────────────────────────────────────
WORDS_PER_PAGE = 300


def has_page_list(epub_path):
    """Return True if the EPUB already contains page-list navigation
    or pagebreak markers in its content."""
    try:
        book = epub.read_epub(epub_path, options={"ignore_ncx": False})
    except Exception:
        return False

    for item in book.get_items():
        content = item.get_content()
        if not content:
            continue

        # EPUB 3: <nav epub:type="page-list">
        if b"page-list" in content:
            soup = BeautifulSoup(content, "html.parser")
            nav = soup.find("nav", attrs={"epub:type": "page-list"})
            if nav:
                return True

        # EPUB 2: <pageList> in NCX
        if b"pageList" in content:
            soup = BeautifulSoup(content, "xml")
            if soup.find("pageList"):
                return True

        # Check for pagebreak spans in content
        if b'epub:type="pagebreak"' in content:
            return True

    return False


def _extract_text_nodes(soup):
    """Yield (text_node, word_count) for every NavigableString in <body>."""
    body = soup.find("body")
    if not body:
        return
    for node in body.descendants:
        if isinstance(node, NavigableString) and node.parent.name not in (
            "script",
            "style",
            "[document]",
        ):
            words = node.strip().split()
            if words:
                yield node, len(words)


def add_pages_to_epub(epub_path, words_per_page=None):
    """
    Insert approximate page-break markers into the EPUB and write an
    updated page-list navigation.

    The page-list is generated automatically by ebooklib's epub3_pages
    option, which scans content documents for pagebreak span markers
    and builds the <nav epub:type="page-list"> in the official nav doc.

    Returns the total number of pages generated.
    """
    if words_per_page is None:
        words_per_page = WORDS_PER_PAGE

    book = epub.read_epub(epub_path, options={"ignore_ncx": False})

    page_number = 0
    word_counter = 0

    # Walk every content document and insert span anchors
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        if item.get_name().endswith(".ncx"):
            continue

        soup = BeautifulSoup(item.get_content(), "html.parser")
        modified = False

        for text_node, wcount in list(_extract_text_nodes(soup)):
            word_counter += wcount
            while word_counter >= words_per_page:
                word_counter -= words_per_page
                page_number += 1
                anchor_id = f"pg{page_number}"

                # Create an invisible <span> that ebooklib's get_pages()
                # will detect (it looks for epub:type + id attributes)
                span = soup.new_tag("span")
                span["id"] = anchor_id
                span["epub:type"] = "pagebreak"
                span["role"] = "doc-pagebreak"
                span["aria-label"] = str(page_number)
                span["title"] = str(page_number)
                text_node.insert_before(span)
                modified = True

        if modified:
            item.set_content(str(soup).encode("utf-8"))

    if page_number == 0:
        return 0

    # Write the EPUB with epub3_pages=True so ebooklib auto-generates
    # the <nav epub:type="page-list"> in the official nav document.
    # This is what Kindle reads for page numbers.
    epub.write_epub(epub_path, book, {"epub3_pages": True})
    return page_number


def get_page_count(epub_path):
    """Return the number of pages in the EPUB, or 0."""
    try:
        book = epub.read_epub(epub_path, options={"ignore_ncx": False})
    except Exception:
        return 0

    # Check all items for page-list navigation
    for item in book.get_items():
        content = item.get_content()
        if not content:
            continue

        # EPUB3 style
        if b"page-list" in content:
            soup = BeautifulSoup(content, "html.parser")
            nav = soup.find("nav", attrs={"epub:type": "page-list"})
            if nav:
                return len(nav.find_all("a"))

        # EPUB2 NCX style
        if b"pageList" in content:
            soup = BeautifulSoup(content, "xml")
            page_list = soup.find("pageList")
            if page_list:
                return len(page_list.find_all("pageTarget"))

    # Fallback: count pagebreak spans in content
    count = 0
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content()
        if content and b'epub:type="pagebreak"' in content:
            soup = BeautifulSoup(content, "html.parser")
            count += len(soup.find_all("span", attrs={"epub:type": "pagebreak"}))
    return count


def _find_ebook_convert():
    """Locate Calibre's ebook-convert executable."""
    # 1. Check PATH
    found = shutil.which("ebook-convert")
    if found:
        return found

    # 2. Check default Windows install locations
    for path in [
        r"C:\Program Files\Calibre2\ebook-convert.exe",
        r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
    ]:
        if os.path.isfile(path):
            return path

    return None


def convert_epub_to_azw3(epub_path):
    """
    Convert an EPUB to AZW3 using Calibre's ebook-convert CLI.

    Returns the path to the generated .azw3 file, or None on failure.
    """
    exe = _find_ebook_convert()
    if not exe:
        print(
            "\033[91mError: Calibre's ebook-convert not found.\033[0m\n"
            "Install Calibre from https://calibre-ebook.com/download\n"
            "and make sure 'ebook-convert' is on your PATH."
        )
        return None

    azw3_path = epub_path.rsplit(".", 1)[0] + ".azw3"

    print(f"Converting {epub_path} → {os.path.basename(azw3_path)} ...")
    try:
        result = subprocess.run(
            [exe, epub_path, azw3_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"\033[91mConversion failed:\033[0m {result.stderr.strip()}")
            return None
    except subprocess.TimeoutExpired:
        print("\033[91mConversion timed out (>120s).\033[0m")
        return None
    except Exception as e:
        print(f"\033[91mConversion error: {e}\033[0m")
        return None

    if os.path.isfile(azw3_path):
        print("\033[92mConversion successful!\033[0m")
        return azw3_path

    print("\033[91mConversion produced no output file.\033[0m")
    return None

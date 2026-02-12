import json
import requests
import os
import smtplib
from email.message import EmailMessage
from config import email_address, email_password, smtp_server, smtp_port, headers

# --- IMPORTS FOR PAGE HANDLING ---
from remotezip import RemoteZip
from bs4 import BeautifulSoup
from ebooklib import epub
import warnings
import logging
import re # Added for parsing file size strings

# Suppress warnings from ebooklib
warnings.filterwarnings('ignore')
logging.getLogger('ebooklib').setLevel(logging.CRITICAL)

# --- HARDCODED CONSTANTS (To bypass ImportErrors) ---
ITEM_UNKNOWN     = 0
ITEM_IMAGE       = 1
ITEM_STYLE       = 2
ITEM_SCRIPT      = 3
ITEM_NAVIGATION  = 4
ITEM_VECTOR      = 5
ITEM_FONT        = 6
ITEM_VIDEO       = 7
ITEM_AUDIO       = 8
ITEM_DOCUMENT    = 9
ITEM_SMIL        = 10

def parse_size_to_mb(size_str):
    """
    Helper to convert size strings like '1.2MB', '500KB' to float MB.
    Returns 0 if parsing fails.
    """
    try:
        size_str = size_str.upper().strip()
        # Remove any non-numeric/non-unit chars (keep dots)
        val = float(re.findall(r"[\d\.]+", size_str)[0])
        
        if 'KB' in size_str:
            return val / 1024
        elif 'MB' in size_str:
            return val
        elif 'GB' in size_str:
            return val * 1024
        return 0
    except:
        return 0

def downloadBook():
    title = input("What book would you like to download? ")

    querystring = {"q":title, "ext":"epub", "sort":"mostRelevant", "source":"libgenLi, libgenRs"}
    url = "https://annas-archive-api.p.rapidapi.com/search"

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
                    print(f"Error: API request failed with status code {response.status_code}")
                    print(f"Response: {response.text}")
                    return
    except Exception as e:
        if "429" in str(e):
            print("Error: API limit reached. Please try again later.")
        else:
            print(f"Error: {e}")
        return

    books = response.json()
    try:
        if not books.get('books'):
            print("\033[91mNo books found for that title.\033[0m")
            return

        for i in range(min(5, len(books['books']))): 
            print(f"{i+1}. {books['books'][i]['title']} by {books['books'][i]['author']}; size: {books['books'][i]['size']}")
    except Exception as e:
        print(f"An error occurred while displaying books: {e}")
        return 

    choice = int(input("Which book would you like to download? "))
    md5 = books['books'][choice-1]['md5']

    url = f"https://annas-archive-api.p.rapidapi.com/download"
    querystring = {"md5":md5}
    try:
        response = requests.get(url, headers=headers, params=querystring)
    except Exception as e:
        print(f"Error: {e}")
        return
    
    title = title.rstrip()

    with open(f"{title}.epub", "wb") as f:
        downloadLink = response.json()[0]
        response = requests.get(downloadLink)
        f.write(response.content)

    print("\033[92mDownload successful!\033[0m")
    print(f"Book downloaded to {title}.epub")
    print(f"Located at: {os.getcwd()}/{title}.epub")

    return title

def downloadBookPDF():
    title = input("What book would you like to download? ")

    querystring = {"q": title, "ext": "pdf", "sort": "mostRelevant", "source": "libgenLi, libgenRs"}
    url = "https://annas-archive-api.p.rapidapi.com/search"

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(f"Error: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return
    except Exception as e:
        if "429" in str(e):
            print("Error: API limit reached. Please try again later.")
        else:
            print(f"Error: {e}")
        return

    try:
        books = response.json()
    except json.JSONDecodeError:
        print("Error: Search API returned invalid JSON.")
        print(f"Raw response: {response.text}")
        return

    if not books.get('books'):
        print("\033[91mNo books found for that title.\033[0m")
        return

    try:
        for i in range(min(5, len(books['books']))):
            print(f"{i+1}. {books['books'][i]['title']} by {books['books'][i]['author']}; size: {books['books'][i]['size']}")
    except Exception as e:
        print(f"An error occurred while displaying books: {e}")
        return

    try:
        choice = int(input("Which book would you like to download? "))
        md5 = books['books'][choice-1]['md5']
    except (ValueError, IndexError):
        print("\033[91mInvalid selection.\033[0m")
        return

    url = f"https://annas-archive-api.p.rapidapi.com/download"
    querystring = {"md5": md5}
    
    print("Fetching download link...")
    try:
        response = requests.get(url, headers=headers, params=querystring)
        
        if response.status_code != 200:
            print(f"\033[91mError: Download API failed (Status: {response.status_code})\033[0m")
            print(f"Server Message: {response.text}")
            return
            
        if not response.text.strip():
            print("\033[91mError: API returned an empty response.\033[0m")
            return

        data = response.json()
        
        if not data or not isinstance(data, list) or len(data) == 0:
            print("\033[91mError: No download link found in API response.\033[0m")
            return
            
        downloadLink = data[0]

    except json.JSONDecodeError:
        print(f"\033[91mError: Could not parse JSON from download API.\033[0m")
        print(f"Raw Response: {response.text}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    title = title.rstrip()
    print(f"Downloading {title}...")

    try:
        with requests.get(downloadLink, stream=True, headers=headers, timeout=60) as file_response:
            file_response.raise_for_status() 
            total_size = int(file_response.headers.get('content-length', 0))
            
            with open(f"{title}.pdf", "wb") as f:
                downloaded = 0
                for chunk in file_response.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        print(f"Progress: {percent}%", end='\r')

        print("\n\033[92mDownload successful!\033[0m")

    except Exception as e:
        print(f"\nError writing file: {e}")
        return

    print(f"Book downloaded to {title}.pdf")
    print(f"Located at: {os.getcwd()}/{title}.pdf")

    return title

def storeKindleEmailInConfig():
    kindleEmail = input("What is your kindle email? ")

    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
    else:
        data = {}

    data["kindleEmail"] = kindleEmail

    with open("config.json", "w") as f:
        json.dump(data, f)

    print("\033[92mKindle email saved!\033[0m")

def downloadAndSendToKindle():
    title = downloadBook()

    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            if "kindleEmail" in data:
                kindleEmail = data["kindleEmail"]
            else:
                storeKindleEmailInConfig()
    else:
        storeKindleEmailInConfig()

    if title and os.path.exists(f"{title}.epub"):
        msg = EmailMessage()
        msg['Subject'] = ''
        msg['From'] = email_address
        msg['To'] = kindleEmail
        msg.set_content('')
        with open(f"{title}.epub", "rb") as f:
            file_data = f.read()
            file_name = f"{title}.epub"
        msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
        except Exception as e:
            print(f"Error: {e} --- Email not sent.")

        print("\033[92mBook sent to kindle!\033[0m")
        os.remove(f"{title}.epub")
        print(f"Deleted {title}.epub from local directory.")
    else:
        print("\033[91mError: File not found or download cancelled.\033[0m")

def exit():
    print("Exiting program.")
    quit()

def viewCurrentKindleEmail():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            if "kindleEmail" in data:
                print(f"Kindle email: {data['kindleEmail']}")
            else:
                print("\033[91mKindle email not set.\033[0m")
    else:
        print("\033[91mKindle email not set.\033[0m")

# --- HELPER FUNCTIONS ---

def inject_page_numbers(input_path, output_path, chars_per_page=2400):
    """
    Injects synthetic page numbers and forces an EPUB 3 Navigation file.
    Uses Thertzlor's character-count method and Kindle manifest fix.
    """
    try:
        print(f"DEBUG: Reading EPUB: {input_path}")
        book = epub.read_epub(input_path)
        
        # FORCE EPUB 3.0
        book.version = '3.0'
        
        page_count = 1
        page_list_items = []
        char_accumulator = 0

        # --- STEP 1: INSERT INVISIBLE PAGE MARKERS ---
        docs = list(book.get_items_of_type(ITEM_DOCUMENT))
        print(f"DEBUG: Found {len(docs)} text chapters. Calculating Thertzlor-style pages...")

        for item in docs:
            try:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                if len(soup.get_text()) < 100: continue

                elements = soup.find_all(['p', 'div', 'span', 'li', 'blockquote'])
                modified = False

                for tag in elements:
                    text_len = len(tag.get_text())
                    char_accumulator += text_len

                    if char_accumulator >= chars_per_page:
                        page_id = f"page{page_count}"
                        
                        anchor = soup.new_tag("span", id=page_id)
                        anchor['epub:type'] = "pagebreak"
                        anchor['title'] = str(page_count)
                        anchor.string = "" 
                        tag.insert_before(anchor)
                        
                        page_list_items.append({'id': page_id, 'href': item.get_name(), 'num': page_count})
                        page_count += 1
                        char_accumulator = 0
                        modified = True

                if modified: 
                    item.set_content(str(soup).encode('utf-8'))
            except Exception as e_inner:
                print(f"DEBUG: Warning processing chapter {item.get_name()}: {e_inner}")

        print(f"DEBUG: Generated {page_count} synthetic pages.")

        # --- STEP 2: CREATE MODERN EPUB 3 NAVIGATION ---
        # Clear existing nav to avoid conflicts
        existing_nav = next((i for i in book.get_items() if i.get_type() == ITEM_NAVIGATION), None)
        if existing_nav:
            book.items.remove(existing_nav)
        
        # Create fresh Nav file
        nav_item = epub.EpubItem(uid='nav', file_name='nav.xhtml', media_type='application/xhtml+xml', content='')
        
        # CRITICAL FIX: The manifest property Kindle needs
        nav_item.properties = ['nav'] 
        
        nav_html = """<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            <li><a href="{first_href}">Start of Book</a></li>
        </ol>
    </nav>
    <nav epub:type="page-list" hidden="">
        <ol>
""".format(first_href=page_list_items[0]['href'] if page_list_items else "#")

        for entry in page_list_items:
            nav_html += f'<li><a href="{entry["href"]}#{entry["id"]}">{entry["num"]}</a></li>\n'
        
        nav_html += """</ol></nav></body></html>"""
        
        nav_item.set_content(nav_html.encode('utf-8'))
        book.add_item(nav_item)
        book.set_identifier("nav") 

        epub.write_epub(output_path, book)
        print("DEBUG: EPUB 3 Upgrade & Thertzlor-style injection complete.")
        return page_count

    except Exception as e:
        print(f"❌ Critical Error in inject_page_numbers: {e}")
        return 0

# --- SMART COMMAND: DOWNLOAD + CHECK VERSION + INJECT ---
def downloadAddPagesAndSend():
    title = input("What book would you like to download? ")
    querystring = {"q": title, "ext": "epub", "sort": "mostRelevant", "source": "libgenLi, libgenRs"}
    url = "https://annas-archive-api.p.rapidapi.com/search"

    print(f"Searching for '{title}'...")
    try:
        response = requests.get(url, headers=headers, params=querystring)
        books_data = response.json()
    except: return

    if not books_data.get('books'): return
    
    all_results = books_data['books']
    print(f"Found {len(all_results)} total results. Scanning for best candidate (Size < 3MB)...")

    best_candidate_path = None
    best_candidate_title = None
    fallback_path = None
    fallback_title = None
    valid_candidates_checked = 0

    for i, book in enumerate(all_results):
        if valid_candidates_checked >= 5:
            print("\nChecked 5 valid candidates. No EPUB 3 found yet.")
            break

        size_mb = parse_size_to_mb(book.get('size', '0'))
        if size_mb > 3.0: continue
            
        print(f"\nChecking Candidate {valid_candidates_checked+1}: {book['title']} ({book['size']})")
        valid_candidates_checked += 1
        
        dl_api_url = f"https://annas-archive-api.p.rapidapi.com/download"
        try:
            dl_res = requests.get(dl_api_url, headers=headers, params={"md5": book['md5']})
            if not dl_res.json(): continue
            dl_link = dl_res.json()[0]
            
            safe_title = "".join([c for c in book['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            temp_filename = f"temp_{i}.epub"
            
            with requests.get(dl_link, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()
                with open(temp_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        except: 
            print("  Download failed. Skipping.")
            continue

        try:
            check_book = epub.read_epub(temp_filename)
            version = float(check_book.version) if check_book.version else 2.0
            print(f"  Detected Version: EPUB {version}")

            if version >= 3.0:
                print(f"\033[92m  ✅ BINGO! Found EPUB 3.0 match.\033[0m")
                best_candidate_path = f"{safe_title}.epub"
                if os.path.exists(best_candidate_path): os.remove(best_candidate_path)
                os.rename(temp_filename, best_candidate_path)
                best_candidate_title = safe_title
                break 
            else:
                print("  ❌ Too old (EPUB 2).")
                if fallback_path is None:
                    fallback_path = f"{safe_title}.epub"
                    if os.path.exists(fallback_path): os.remove(fallback_path)
                    os.rename(temp_filename, fallback_path)
                    fallback_title = safe_title
                    print("  (Saved as fallback option)")
                else:
                    os.remove(temp_filename)
        except:
            if os.path.exists(temp_filename): os.remove(temp_filename)

    final_file = best_candidate_path or fallback_path
    if not final_file:
        print("\n❌ No valid books found.")
        return

    print(f"Injecting page numbers (Thertzlor Character Method)...")
    paged_file = f"paged_{final_file}"
    pages = inject_page_numbers(final_file, paged_file)
    
    if os.path.exists(final_file): os.remove(final_file)
    os.rename(paged_file, final_file)
    
    print(f"\033[92mReady! Book has approximately {pages} pages.\033[0m")

    if input("Send to Kindle? (y/n): ").lower() == 'y':
        if os.path.exists("config.json"):
            with open("config.json", "r") as f: data = json.load(f)
            kindleEmail = data.get("kindleEmail")
        else:
            storeKindleEmailInConfig()
            with open("config.json", "r") as f: data = json.load(f)
            kindleEmail = data.get("kindleEmail")

        msg = EmailMessage()
        msg['From'] = email_address
        msg['To'] = kindleEmail
        with open(final_file, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=final_file)
        
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
            print("\033[92mBook sent!\033[0m")
            os.remove(final_file)
        except Exception as e: print(e)
    else:
        print(f"Saved locally: {final_file}")

# --- NEW COMMAND FUNCTIONS ---

def downloadAndSendPagesOnly():
    """
    Option 1: Aggressive Brute Force Search.
    Checks for Navigation Lists AND internal pagebreak markers.
    """
    title = input("What book would you like to download? ")
    querystring = {"q": title, "ext": "epub", "sort": "mostRelevant", "source": "libgenLi, libgenRs"}
    url = "https://annas-archive-api.p.rapidapi.com/search"

    print(f"Searching for '{title}'...")
    try:
        response = requests.get(url, headers=headers, params=querystring)
    except Exception as e:
        print(f"Error searching: {e}")
        return

    books = response.json()
    if not books.get('books'):
        print("\033[91mNo books found.\033[0m")
        return

    candidates = books['books'][:5]
    found_book_path = None
    found_book_title = None

    print("Checking top results for built-in page numbers...")
    print("(This downloads files temporarily to verify accuracy)")

    for i, book in enumerate(candidates):
        print(f"\nChecking candidate {i+1}/{len(candidates)}: {book['title']}...")
        
        dl_api_url = f"https://annas-archive-api.p.rapidapi.com/download"
        try:
            dl_response = requests.get(dl_api_url, headers=headers, params={"md5": book['md5']})
            if dl_response.status_code != 200 or not dl_response.json():
                print("  Skipping: Could not retrieve download link.")
                continue
            download_link = dl_response.json()[0]
        except Exception:
            print("  Skipping: API Error.")
            continue

        safe_title = "".join([c for c in book['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        temp_filename = f"temp_check_{i}.epub"
        
        try:
            with requests.get(download_link, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()
                with open(temp_filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception:
            print("  Skipping: Download failed.")
            if os.path.exists(temp_filename): os.remove(temp_filename)
            continue

        has_pages = False
        try:
            check_book = epub.read_epub(temp_filename)
            
            for item in check_book.get_items():
                name = item.get_name().lower()
                if any(name.endswith(ext) for ext in ['.html', '.xhtml', '.xml', '.ncx', '.opf']):
                    content = item.get_content()
                    if b'page-list' in content or b'pageList' in content:
                        has_pages = True
                        print(f"  DEBUG: Found 'page-list' structure in {item.get_name()}")
                        break
                    if b'epub:type="pagebreak"' in content or b'title="page' in content:
                        has_pages = True
                        print(f"  DEBUG: Found internal 'pagebreak' markers in {item.get_name()}")
                        break

        except Exception as e:
            print(f"  Warning: Structure error in candidate {i+1} ({e})")
        
        if has_pages:
            print(f"\033[92m  ✅ Found Match! Candidate {i+1} has detected page numbers.\033[0m")
            final_filename = f"{safe_title}.epub"
            if os.path.exists(final_filename): os.remove(final_filename)
            os.rename(temp_filename, final_filename)
            found_book_path = final_filename
            found_book_title = safe_title
            
            for j in range(len(candidates)):
                junk_file = f"temp_check_{j}.epub"
                if os.path.exists(junk_file): os.remove(junk_file)
            break 
        else:
            print("  ❌ No page numbers detected. Deleting...")
            os.remove(temp_filename)

    if not found_book_path:
        print("\n\033[91mNo books with built-in page numbers were found in the top results.\033[0m")
        return

    print(f"\nSelected: {found_book_title}")
    confirm = input("Send this book to Kindle? (y/n): ").lower()
    
    if confirm != 'y':
        print(f"Book saved locally as {found_book_path}")
        return

    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            kindleEmail = data.get("kindleEmail")
    else:
        storeKindleEmailInConfig()
        with open("config.json", "r") as f: data = json.load(f)
        kindleEmail = data.get("kindleEmail")

    msg = EmailMessage()
    msg['Subject'] = ''
    msg['From'] = email_address
    msg['To'] = kindleEmail
    msg.set_content('')
    
    with open(found_book_path, "rb") as f:
        file_data = f.read()
    msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=found_book_path)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)
        print("\033[92mBook sent to kindle!\033[0m")
        os.remove(found_book_path)
        print(f"Deleted {found_book_path} from local directory.")
    except Exception as e:
        print(f"Error sending email: {e}")

def helpMessage():
    print("\n\033[1mCommands:\033[0m")
    print("\033[94mdownload\033[0m - Download a book")
    print("\033[94mdownloadpdf\033[0m - Download a pdf")
    print("\033[94msend\033[0m - Send a book to your kindle")
    print("\033[94msendpages\033[0m - Find only books with pages and send")
    print("\033[94msendadd\033[0m - Download, add pages, and optionally send")
    print("\033[94mconfig\033[0m - Configure your kindle email")
    print("\033[94mview\033[0m - View your current kindle email")
    print("\033[94mhelp\033[0m - Show this help message")
    print("\033[94mexit\033[0m - Exit the program")

def main():
    print("Welcome to the Book Downloader!")
    helpMessage()
    while True:
        command = input("Enter a command: ")
        if command == "download":
            downloadBook()
        elif command == "downloadpdf":
            downloadBookPDF()
        elif command == "send":
            downloadAndSendToKindle()
        elif command == "sendpages":
            downloadAndSendPagesOnly()
        elif command == "sendadd":
            downloadAddPagesAndSend()
        elif command == "config":
            storeKindleEmailInConfig()
        elif command == "view":
            viewCurrentKindleEmail()
        elif command == "help":
            helpMessage()
        elif command == "exit":
            exit()
        else:
            print("\033[91mError: Command not recognized.\033[0m")

main()
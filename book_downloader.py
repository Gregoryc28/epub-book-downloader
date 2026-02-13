import json
import requests
import os
import smtplib
from email.message import EmailMessage
from config import email_address, email_password, smtp_server, smtp_port, headers
import epub_utils


def downloadBook():
    # Ask the user for the title of the book they want to download
    title = input("What book would you like to download? ")

    querystring = {
        "q": title,
        "ext": "epub",
        "sort": "mostRelevant",
        "source": "libgenLi, libgenRs",
    }
    url = "https://annas-archive-api.p.rapidapi.com/search"

    # Print out the books title and author for each of the top 5 results in a nice format
    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(f"Error: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return
    except Exception as e:
        # Figure out what the error is and print a message to the user
        if "429" in str(e):
            print("Error: API limit reached. Please try again later.")
        else:
            print(f"Error: {e}")

    books = response.json()
    try:
        # Check if any books were returned
        if not books.get("books"):
            print("\033[91mNo books found for that title.\033[0m")
            return

        for i in range(
            min(5, len(books["books"]))
        ):  # Loop up to 5 or the number of results found
            print(
                f"{i + 1}. {books['books'][i]['title']} by {books['books'][i]['author']}; size: {books['books'][i]['size']}"
            )
    except Exception as e:
        print(f"An error occurred while displaying books: {e}")
        return  # Exit if we can't display books

    # Ask the user which book they would like to download
    choice = int(input("Which book would you like to download? "))

    # Get the md5 hash of the book the user chose
    md5 = books["books"][choice - 1]["md5"]

    # Download the book
    url = "https://annas-archive-api.p.rapidapi.com/download"
    querystring = {"md5": md5}
    try:
        response = requests.get(url, headers=headers, params=querystring)
    except Exception as e:
        print(f"Error: {e}")
        return
    # Remove any spaces from the end of the title
    title = title.rstrip()

    # Download the book file the download link (the first element of the list in response.content) (Use requests.get()) and save it to a file with the title of the book
    with open(f"{title}.epub", "wb") as f:
        downloadLink = response.json()[0]
        response = requests.get(downloadLink)
        f.write(response.content)

    # Print out a message to the user letting them know the book has been downloaded successfully (color success message green)
    print("\033[92mDownload successful!\033[0m")

    # print the path of the downloaded book
    print(f"Book downloaded to {title}.epub")
    print(f"Located at: {os.getcwd()}/{title}.epub")

    return title


def downloadBookPDF():
    # Ask the user for the title of the book they want to download
    title = input("What book would you like to download? ")

    querystring = {
        "q": title,
        "ext": "pdf",
        "sort": "mostRelevant",
        "source": "libgenLi, libgenRs",
    }
    url = "https://annas-archive-api.p.rapidapi.com/search"

    # --- SEARCH PHASE ---
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

    # Check if any books were returned
    if not books.get("books"):
        print("\033[91mNo books found for that title.\033[0m")
        return

    try:
        for i in range(min(5, len(books["books"]))):
            print(
                f"{i + 1}. {books['books'][i]['title']} by {books['books'][i]['author']}; size: {books['books'][i]['size']}"
            )
    except Exception as e:
        print(f"An error occurred while displaying books: {e}")
        return

    # Ask the user which book they would like to download
    try:
        choice = int(input("Which book would you like to download? "))
        # Get the md5 hash of the book the user chose
        md5 = books["books"][choice - 1]["md5"]
    except (ValueError, IndexError):
        print("\033[91mInvalid selection.\033[0m")
        return

    # --- DOWNLOAD PHASE ---
    url = "https://annas-archive-api.p.rapidapi.com/download"
    querystring = {"md5": md5}

    print("Fetching download link...")
    try:
        response = requests.get(url, headers=headers, params=querystring)

        # FIX: Check status code before parsing JSON
        if response.status_code != 200:
            print(
                f"\033[91mError: Download API failed (Status: {response.status_code})\033[0m"
            )
            print(f"Server Message: {response.text}")
            return

        # FIX: Check if response is empty before parsing
        if not response.text.strip():
            print("\033[91mError: API returned an empty response.\033[0m")
            return

        data = response.json()

        # Check if we actually got a list with a link
        if not data or not isinstance(data, list) or len(data) == 0:
            print("\033[91mError: No download link found in API response.\033[0m")
            return

        downloadLink = data[0]

    except json.JSONDecodeError:
        print("\033[91mError: Could not parse JSON from download API.\033[0m")
        print(f"Raw Response: {response.text}")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    # Remove any spaces from the end of the title
    title = title.rstrip()

    print(f"Downloading {title}...")

    # Download the book file with STREAMING
    try:
        # stream=True keeps the connection open and downloads in chunks
        # timeout=60 gives the server more time to respond
        with requests.get(
            downloadLink, stream=True, headers=headers, timeout=60
        ) as file_response:
            file_response.raise_for_status()  # Check for errors

            # Get total file size for progress tracking (optional but helpful)
            total_size = int(file_response.headers.get("content-length", 0))

            with open(f"{title}.pdf", "wb") as f:
                downloaded = 0
                # Download in 8KB chunks
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Print a simple progress percentage
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        print(f"Progress: {percent}%", end="\r")

        print("\n\033[92mDownload successful!\033[0m")

    except Exception as e:
        print(f"\nError writing file: {e}")
        return

    # Print out a message to the user
    print(f"Book downloaded to {title}.pdf")
    print(f"Located at: {os.getcwd()}/{title}.pdf")

    return title


def storeKindleEmailInConfig():
    # Ask the user for their kindle email
    kindleEmail = input("What is your kindle email? ")

    # Check if the config file exists (config.json)
    if os.path.exists("config.json"):
        # If it does, load the data from the file
        with open("config.json", "r") as f:
            data = json.load(f)
    else:
        # If it doesn't, create an empty dictionary
        data = {}

    # Check if the kindleEmail key exists in the dictionary
    if "kindleEmail" in data:
        # If it does, update the value
        data["kindleEmail"] = kindleEmail
    else:
        # If it doesn't, create the key and value
        data["kindleEmail"] = kindleEmail

    # Write the data back to the config file
    with open("config.json", "w") as f:
        json.dump(data, f)

    # Print a message to the user letting them know their kindle email has been saved
    print("\033[92mKindle email saved!\033[0m")


def downloadAndSendToKindle():
    # Run the downloadBook function
    title = downloadBook()

    # Get the user's kindle email from the config file (check if it exists first)
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            if "kindleEmail" in data:
                kindleEmail = data["kindleEmail"]
            else:
                # If it doesn't, ask the user for their kindle email
                storeKindleEmailInConfig()
    else:
        # If it doesn't, ask the user for their kindle email
        storeKindleEmailInConfig()

    # Make sure the title.epub file exists
    if title and os.path.exists(f"{title}.epub"):
        # Create email message
        msg = EmailMessage()
        msg["Subject"] = ""
        msg["From"] = email_address
        msg["To"] = kindleEmail
        msg.set_content("")
        # Attach the book file to the email
        with open(f"{title}.epub", "rb") as f:
            file_data = f.read()
            file_name = f"{title}.epub"
        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="octet-stream",
            filename=file_name,
        )

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
        except Exception as e:
            print(f"Error: {e} --- Email not sent.")

        # Print a message to the user letting them know the book has been sent to their kindle
        print("\033[92mBook sent to kindle!\033[0m")
        # Delete the book file from the local directory
        os.remove(f"{title}.epub")
        print(f"Deleted {title}.epub from local directory.")
    else:
        # If it doesn't, print an error message to the user
        print("\033[91mError: File not found or download cancelled.\033[0m")


def downloadBookWithPages():
    """Search for books, download top results, and only show ones with built-in pages."""
    title = input("What book would you like to download? ")

    querystring = {
        "q": title,
        "ext": "epub",
        "sort": "mostRelevant",
        "source": "libgenLi, libgenRs",
    }
    url = "https://annas-archive-api.p.rapidapi.com/search"

    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(f"Error: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        if "429" in str(e):
            print("Error: API limit reached. Please try again later.")
        else:
            print(f"Error: {e}")
        return None

    books = response.json()
    if not books.get("books"):
        print("\033[91mNo books found for that title.\033[0m")
        return None

    top_books = books["books"][:5]
    books_with_pages = []  # list of (original_index, book_info, filepath)
    temp_files = []  # track all temp downloads for cleanup

    print("Checking books for built-in page navigation...")

    for i, book_info in enumerate(top_books):
        md5 = book_info["md5"]
        temp_name = f"_temp_check_{i}.epub"
        try:
            dl_url = "https://annas-archive-api.p.rapidapi.com/download"
            dl_qs = {"md5": md5}
            dl_resp = requests.get(dl_url, headers=headers, params=dl_qs)
            if dl_resp.status_code != 200:
                continue
            dl_data = dl_resp.json()
            if not dl_data or not isinstance(dl_data, list) or len(dl_data) == 0:
                continue
            download_link = dl_data[0]
            file_resp = requests.get(download_link)
            with open(temp_name, "wb") as f:
                f.write(file_resp.content)
            temp_files.append(temp_name)

            if epub_utils.has_page_list(temp_name):
                books_with_pages.append((i, book_info, temp_name))
                page_count = epub_utils.get_page_count(temp_name)
                print(f"  \033[92m✓\033[0m {book_info['title']} — {page_count} pages")
            else:
                print(f"  ✗ {book_info['title']} — no pages")
        except Exception as e:
            print(f"  ✗ {book_info['title']} — error checking: {e}")
            continue

    if not books_with_pages:
        print("\033[91mNone of the top results have built-in page navigation.\033[0m")
        # Clean up all temp files
        for tf in temp_files:
            if os.path.exists(tf):
                os.remove(tf)
        return None

    # Display the filtered list
    print("\n\033[1mBooks with built-in pages:\033[0m")
    for idx, (orig_i, book_info, _) in enumerate(books_with_pages):
        page_count = epub_utils.get_page_count(books_with_pages[idx][2])
        print(
            f"{idx + 1}. {book_info['title']} by {book_info['author']}; "
            f"size: {book_info['size']}; pages: {page_count}"
        )

    try:
        choice = int(input("Which book would you like to download? "))
        if choice < 1 or choice > len(books_with_pages):
            print("\033[91mInvalid selection.\033[0m")
            for tf in temp_files:
                if os.path.exists(tf):
                    os.remove(tf)
            return None
    except ValueError:
        print("\033[91mInvalid selection.\033[0m")
        for tf in temp_files:
            if os.path.exists(tf):
                os.remove(tf)
        return None

    # Keep the chosen file, delete the rest
    _, chosen_info, chosen_path = books_with_pages[choice - 1]
    final_title = chosen_info["title"].rstrip()
    final_name = f"{final_title}.epub"

    # Rename chosen temp file to proper name
    if os.path.exists(final_name):
        os.remove(final_name)
    os.rename(chosen_path, final_name)

    # Clean up remaining temp files
    for tf in temp_files:
        if os.path.exists(tf) and tf != chosen_path:
            os.remove(tf)

    print("\033[92mDownload successful!\033[0m")
    print(f"Book downloaded to {final_name}")
    return final_title


def downloadAndSendPaginated():
    """sendpages: download a book that already has pages, send to Kindle."""
    title = downloadBookWithPages()

    if not title:
        return

    epub_path = f"{title}.epub"
    if not os.path.exists(epub_path):
        print("\033[91mError: File not found or download cancelled.\033[0m")
        return

    # Convert EPUB → AZW3 for Kindle page number support
    azw3_path = epub_utils.convert_epub_to_azw3(epub_path)
    if not azw3_path:
        print("\033[93mFalling back to sending EPUB directly.\033[0m")
        send_path = epub_path
    else:
        send_path = azw3_path

    # Get kindle email
    kindleEmail = None
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            if "kindleEmail" in data:
                kindleEmail = data["kindleEmail"]
    if not kindleEmail:
        storeKindleEmailInConfig()
        with open("config.json", "r") as f:
            data = json.load(f)
            kindleEmail = data.get("kindleEmail")

    msg = EmailMessage()
    msg["Subject"] = ""
    msg["From"] = email_address
    msg["To"] = kindleEmail
    msg.set_content("")
    with open(send_path, "rb") as f:
        file_data = f.read()
    msg.add_attachment(
        file_data,
        maintype="application",
        subtype="octet-stream",
        filename=os.path.basename(send_path),
    )
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_address, email_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Error: {e} --- Email not sent.")
        return

    print("\033[92mBook sent to kindle!\033[0m")
    # Clean up both files
    if os.path.exists(epub_path):
        os.remove(epub_path)
    if azw3_path and os.path.exists(azw3_path):
        os.remove(azw3_path)
    print("Cleaned up local files.")


def downloadAddPagesAndSend():
    """sendadd: download a book, add pages, convert to AZW3, then ask user to send/skip/download."""
    title = downloadBook()

    if not title:
        return

    epub_path = f"{title}.epub"
    if not os.path.exists(epub_path):
        print("\033[91mError: File not found or download cancelled.\033[0m")
        return

    print(f"\nAdding page numbers to {epub_path}...")
    page_count = epub_utils.add_pages_to_epub(epub_path)

    if page_count == 0:
        print(
            "\033[93mWarning: Could not generate pages (book may be empty or unreadable).\033[0m"
        )
    else:
        print(f"\033[92mDone! Added approximately {page_count} pages.\033[0m")

    # Convert EPUB → AZW3 for Kindle page number support
    azw3_path = epub_utils.convert_epub_to_azw3(epub_path)

    print("\n\033[1mBook details:\033[0m")
    print(f"  Title: {title}")
    print(f"  Pages: ~{page_count}")
    if azw3_path:
        print(f"  File:  {azw3_path} (Kindle-optimized)")
    else:
        print(f"  File:  {epub_path}")
        print("\033[93m  Note: AZW3 conversion failed; sending EPUB directly.\033[0m")

    choice = (
        input("\nSend to Kindle? (y = send, n = cancel, d = download only): ")
        .strip()
        .lower()
    )

    send_path = azw3_path if azw3_path else epub_path

    if choice == "y":
        # Get kindle email
        kindleEmail = None
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                data = json.load(f)
                if "kindleEmail" in data:
                    kindleEmail = data["kindleEmail"]
        if not kindleEmail:
            storeKindleEmailInConfig()
            with open("config.json", "r") as f:
                data = json.load(f)
                kindleEmail = data.get("kindleEmail")

        msg = EmailMessage()
        msg["Subject"] = ""
        msg["From"] = email_address
        msg["To"] = kindleEmail
        msg.set_content("")
        with open(send_path, "rb") as f:
            file_data = f.read()
        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="octet-stream",
            filename=os.path.basename(send_path),
        )
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_address, email_password)
                server.send_message(msg)
        except Exception as e:
            print(f"Error: {e} --- Email not sent.")
            return

        print("\033[92mBook sent to kindle!\033[0m")
        # Clean up both files
        if os.path.exists(epub_path):
            os.remove(epub_path)
        if azw3_path and os.path.exists(azw3_path):
            os.remove(azw3_path)
        print("Cleaned up local files.")

    elif choice == "d":
        # Keep the AZW3 (or EPUB if conversion failed), delete the other
        keep_path = azw3_path if azw3_path else epub_path
        if azw3_path and os.path.exists(epub_path):
            os.remove(epub_path)
        print(f"\033[92mBook saved locally at: {os.path.abspath(keep_path)}\033[0m")

    else:
        # n or any other input — cancel and delete both
        if os.path.exists(epub_path):
            os.remove(epub_path)
        if azw3_path and os.path.exists(azw3_path):
            os.remove(azw3_path)
        print("Cancelled. Cleaned up local files.")


def exit():
    # Print a message to the user letting them know the program is exiting
    print("Exiting program.")
    # Exit the program
    quit()


def viewCurrentKindleEmail():
    # Check if the config file exists
    if os.path.exists("config.json"):
        # If it does, load the data from the file
        with open("config.json", "r") as f:
            data = json.load(f)
            if "kindleEmail" in data:
                # If the kindleEmail key exists in the dictionary, print the kindle email to the user
                print(f"Kindle email: {data['kindleEmail']}")
            else:
                # If it doesn't, print a message to the user letting them know the kindle email hasn't been set
                print("\033[91mKindle email not set.\033[0m")
    else:
        # If it doesn't, print a message to the user letting them know the kindle email hasn't been set
        print("\033[91mKindle email not set.\033[0m")


def helpMessage():
    # Print a help message to the user
    print("\n\033[1mCommands:\033[0m")
    print("\033[94mdownload\033[0m - Download a book")
    print("\033[94mdownloadpdf\033[0m - Download a pdf")
    print("\033[94msend\033[0m - Send a book to your kindle")
    print(
        "\033[94msendpages\033[0m - Send a book (only shows books with built-in pages)"
    )
    print("\033[94msendadd\033[0m - Download a book, add pages, then send/save")
    print("\033[94mconfig\033[0m - Configure your kindle email")
    print("\033[94mview\033[0m - View your current kindle email")
    print("\033[94mhelp\033[0m - Show this help message")
    print("\033[94mexit\033[0m - Exit the program")


def main():
    # Print a welcome message to the user
    print("Welcome to the Book Downloader!")
    # Print a help message to the user
    helpMessage()
    # Run a loop that asks the user for a command
    while True:
        command = input("Enter a command: ")
        # Check the command and call the appropriate function
        if command == "download":
            downloadBook()
        elif command == "downloadpdf":
            downloadBookPDF()
        elif command == "send":
            downloadAndSendToKindle()
        elif command == "sendpages":
            downloadAndSendPaginated()
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
            # If the command is not recognized, print an error message to the user
            print("\033[91mError: Command not recognized.\033[0m")


main()

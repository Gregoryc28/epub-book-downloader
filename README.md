# EPUB Book Downloader

A Python script to search, download ePub books from Anna's Archive API, and optionally send them to your Kindle device via email.

## Features
- Search for books by title
- Display top 5 most relevant results with title, author, and file size
- Download selected book in ePub format
- Store Kindle email address in a config file
- Send downloaded books to your Kindle via email
- Command-line interface with multiple commands
- Color-coded success/error messages

## Requirements
- Python 3.x
- `requests` library
- Anna's Archive API key from RapidAPI
- Gmail account with App Password for SMTP

## Setup
1. Clone the repository: `git clone [repository-url]` then `cd epub-book-downloader`
2. Install dependencies from the requirements file: `pip install -r requirements.txt`
3. Configure credentials:
   - Set environment variables or modify config for *(in config.py)*:
     - Gmail address and App Password
       - Generate an [App Password](https://www.zdnet.com/article/gmail-app-passwords-what-they-are-how-to-create-one-and-why-to-use-them/) for your email
     - [RapidAPI key and headers](https://rapidapi.com/tribestick-tribestick-default/api/annas-archive-api)

## Usage
To use the Book Downloader, run the script with `python book_downloader.py`. Once started, you'll see a welcome message and available commands. Enter `download` to search for and download a book by typing its title when prompted, then select from the top 5 results. Use `send` to download a book and send it to your Kindle in one step. Type `config` to set or update your Kindle email address, or `view` to see the currently configured Kindle email. For a list of commands at any time, enter `help`. To quit the program, type `exit`.

## Configuration
Kindle email is stored in `config.json`, created via the `config` command.

## Notes
- Requires internet connection
- Subject to RapidAPI rate limits
- Gmail SMTP needs App Password with 2FA
- Books saved as `[title].epub`
- Auto-deletes after Kindle send

## Security
- Use environment variables for credentials
- Add `.gitignore` for `config.json`, `config.py`, and `*.epub`
- Never commit sensitive data

## Troubleshooting
- "429 Error": API limit reached
- "Email not sent": Check credentials
- "Book not found": Verify connection/search term

## License
[MIT License](LICENSE)

## Contributing
Fork, branch, and submit pull requests with improvements.

## Credits
Created by Gregory Cohen  
Powered by Anna's Archive API via RapidAPI
import json

import requests
import os

import smtplib
from email.message import EmailMessage

from config import email_address, email_password, smtp_server, smtp_port, headers

def downloadBook():
	# Ask the user for the title of the book they want to download
	title = input("What book would you like to download? ")

	querystring = {"q":title, "ext":"epub", "sort":"mostRelevant", "source":"libgenLi, libgenRs"}
	url = "https://annas-archive-api.p.rapidapi.com/search"

	# Print out the books title and author for each of the top 5 results in a nice format
	try:
		response = requests.get(url, headers=headers, params=querystring)
	except Exception as e:
		# Figure out what the error is and print a message to the user
		if "429" in str(e):
			print("Error: API limit reached. Please try again later.")
		else:
			print(f"Error: {e}")

	books = response.json()
	try:
		for i in range(5):
			print(f"{i+1}. {books['books'][i]['title']} by {books['books'][i]['author']}; size: {books['books'][i]['size']}")
	except Exception as e:
		# Tell the user the book could not be found
		print(f"Error: {e}")
		print("\033[91mBook not found.\033[0m")

	# Ask the user which book they would like to download
	choice = int(input("Which book would you like to download? "))

	# Get the md5 hash of the book the user chose
	md5 = books['books'][choice-1]['md5']

	# Download the book
	url = f"https://annas-archive-api.p.rapidapi.com/download"
	querystring = {"md5":md5}
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
	if os.path.exists(f"{title}.epub"):
		# Create email message
		msg = EmailMessage()
		msg['Subject'] = ''
		msg['From'] = email_address
		msg['To'] = kindleEmail
		msg.set_content('')
		# Attach the book file to the email
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

		# Print a message to the user letting them know the book has been sent to their kindle
		print("\033[92mBook sent to kindle!\033[0m")
		# Delete the book file from the local directory
		os.remove(f"{title}.epub")
		print(f"Deleted {title}.epub from local directory.")
	else:
		# If it doesn't, print an error message to the user
		print("\033[91mError: File not found.\033[0m")

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
	print("\033[94msend\033[0m - Send a book to your kindle")
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
		elif command == "send":
			downloadAndSendToKindle()
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
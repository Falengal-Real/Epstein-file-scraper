# Epstein-file-scraper

Open the code and find the clearly marked area at the top of the page then follow these steps ------>
Web scraper that will download all the JE files straight from the DOJ website, it doesnt follow redirects or any other links, it will stay strictly in the datasets and will stop automatically once done

Create a new folder on your desktop - name it 'JE-Files' - right click the folder and click properties, copy and paste the the 'Location' output into the clearly marked area in the code               (you can replace what is currently there). Once you copy and paste, simply add this to the end of what you just pasted, still inside the quotes ->  \JE-Files

All websites and installs are safe

Download python - https://www.python.org/downloads/

Open 'Terminal' or 'CMD' - copy and paste this into the input bar once it opens

pip install requests selenium beautifulsoup4

(pip should be installed with python, if you have any problems copy and paste -> python -m ensurepip --upgrade <- if its not installed, install it with -> python get-pip.py <-)

to start the script open a new terminal, then copy and paste this -> python scrape.py <- this starts the script.

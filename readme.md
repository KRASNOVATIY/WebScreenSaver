## WebScreen

Script to save web pages in image format (PNG)

## Requirements

The script requires the selenium and pyvirtualdisplay libraries (see requirements.txt)
and at least one of the web drivers:
* https://github.com/Mozilla/geckodriver/releases
* https://phantomjs.org/download
* http://chromedriver.chromium.org/downloads

In addition, if you use geckodriver, then to work through a proxy server,
you need to install Firefox Developer Edition:
* https://developer.mozilla.org/en/docs/Mozilla/Firefox/Developer_Edition

## Usage

```python
from web_saver import WebScreenSaver

FIREFOX_PATH = r'D:\webdrivers\gecko\geckodriver'
FIREFOX_DEVELOPER_BIN = r"C:\Program Files\Firefox Developer Edition\firefox"
PHANTOM_PATH = r'D:\webdrivers\phantomjs\bin\phantomjs'

x = WebScreenSaver(
    phantom_path=PHANTOM_PATH,
    firefox_path=FIREFOX_PATH,
    firefox_dev_bin=FIREFOX_DEVELOPER_BIN
)

x.use_chrome()  # can not use, print message about it
print(x.take_page("http://site.com", "site1.png"))
x.size = (800, 600)
x.use_firefox()
print(x.take_page("http://site.com", "site2.png"))
print(x.take_page("http://site.com", "site3.png", adjust_size=False)
```

Also see example.py
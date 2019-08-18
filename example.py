from web_saver import WebScreenSaver

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:29.0) Gecko/20100101 Firefox/29.0'

CHROME_PATH = r''
FIREFOX_PATH = r'D:\webdrivers\gecko\geckodriver'
FIREFOX_DEVELOPER_BIN = r"C:\Program Files\Firefox Developer Edition\firefox"
PHANTOM_PATH = r'D:\webdrivers\phantomjs\bin\phantomjs'

PROXY = {'proxy_host': 'proxy.site.net',
         'proxy_port': 5555,
         'proxy_username': 'MyNameIsNill',
         'proxy_password': 'Pa$sW0Rd'}


def main():
    x = WebScreenSaver(
        phantom_path=PHANTOM_PATH,
        firefox_path=FIREFOX_PATH, firefox_dev_bin=FIREFOX_DEVELOPER_BIN
    )
    x.use_chrome()
    # x.setup_proxy(PROXY)
    print(x.get_user_agent())
    x.user_agent = USER_AGENT
    print(x.take_page("http://site.com", "site1.png"))
    print(x.get_user_agent())
    x.size = (800, 600)
    x.use_firefox()
    print(x.take_page("http://site.com", "site2.png"))
    x.use_phantom()
    del x.user_agent
    print(x.get_user_agent())
    print(x.take_page("http://site.com", "site3.png"))
    print(x.get_user_agent())
    x.size = (600, 400)
    print(x.take_page("http://site.com", "site4.png"))
    print(x.take_page("http://test.com", "site5.png"))
    x.use_firefox()
    print(x.take_page("http://test.com", "site6.png"))


if __name__ == "__main__":
    main()
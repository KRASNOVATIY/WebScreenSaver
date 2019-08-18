import os
import re
import string
import zipfile
from pathlib import Path
from subprocess import check_output

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from pyvirtualdisplay import Display


class WebScreenSaver(object):
    """
    Save web page as PNG image using web driver,
    can specify:
        webDriver, with `use_*` methods
        proxy, with `setup_proxy` method
        userAgent, with `user_agent` property
        take timeout, with `timeout` property
        take image size, with `size` property
    """
    FIREFOX_DRIVER_NAME = "firefox"
    PHANTOM_DRIVER_NAME = "phantomjs"
    CHROME_DRIVER_NAME = "chrome"

    def __init__(self, chrome_path=None, phantom_path=None, firefox_path=None, firefox_dev_bin=None):
        """
        init object
        one of *_path should be specified,
        if specified firefox_path, firefox_dev_bin should be specified to
        :param chrome_path: (str) path to chrome driver
        :param phantom_path: (str) path to phantomjs driver
        :param firefox_path: (str) path to gecko driver
        :param firefox_dev_bin: (str) path to firefox developer binary
        """

        self.display = None  # type: Display
        self.driver = None  # type: RemoteWebDriver

        assert any([chrome_path, phantom_path, firefox_path]), "path with webdriver not specified"
        if firefox_path:
            assert all([firefox_path, firefox_dev_bin]), "for gecko driver you should specify FirefoxDeveloperBinary"
        self.chrome_path = chrome_path
        self.phantomjs_path = phantom_path
        self.firefox_path = firefox_path
        self.firefox_bin = firefox_dev_bin

        self._changed = True

        self._driverName = ""
        self._use_proxy = dict()
        self._size = (1280, 800)
        self._timeout = 25
        self._custom_ua = ""

        if chrome_path:
            self._driver_name = self.CHROME_DRIVER_NAME
        elif phantom_path:
            self._driver_name = self.PHANTOM_DRIVER_NAME
        else:
            self._driver_name = self.FIREFOX_DRIVER_NAME  # gecko

        self._init_ff_ids = self._get_firefox_ids()

    def __del__(self):
        """
        close current webdriver,
        if current driver is gecko (firefox) and os == windows, terminate process with subprocess module
            !note: for unknown reasons last firefox window do not closed on driver.quit() while normal script running
            but while run it with pydev (debugging), window closed all times
        :return:
        """
        self._quit()
        if isinstance(self.driver, webdriver.Firefox):
            firefox_ids = set(self._get_firefox_ids()).difference(self._init_ff_ids)
            if not firefox_ids:  # or while os = posix
                return
            task_kill = 'taskkill /f ' + ''.join(["/pid " + f + " " for f in firefox_ids]).strip()
            check_output(task_kill.split(), shell=True)

    def _quit(self):
        if self.driver:
            self.driver.quit()
            self.display.stop() if self.display else ...

    @staticmethod
    def _get_firefox_ids():
        """
        get pid`s of all current running firefox processes
        :return: (list) pid`s of firefox processes
        """
        if os.name == "posix":
            return list()
        elif os.name == "nt":
            return re.findall(
                r"firefox.exe\s+(\d+)",
                check_output(["tasklist", "/fi", "imagename eq firefox.exe"], shell=True).decode(errors="ignore")
            )
        else:
            raise OSError("Unsupported OS")

    @property
    def _driver_name(self):
        """
        current driver name: firefox or phantomjs or chrome
        :return: (str) driver name
        """
        return self._driverName

    @_driver_name.setter
    def _driver_name(self, value):
        if not eval("self.{}_path".format(value)):
            print("{0} path not specified, cannot use method 'use_{0}'".format(value))
            return
        if value == self._driverName:
            return
        self._driverName = value
        self._changed = True

    @property
    def user_agent(self):
        """
        current user agent
        :return: (str) user agent
        """
        return self._custom_ua

    @user_agent.setter
    def user_agent(self, value):
        if value == self._custom_ua:
            return
        self._custom_ua = value
        self._changed = True

    @user_agent.deleter
    def user_agent(self):
        self._custom_ua = ""
        self._changed = True

    @property
    def size(self):
        """
        current driver screen size
        :return: (tuple(int, int)) pair(width, height)
        """
        return self._size

    @size.setter
    def size(self, value):
        if value == self._size:
            return
        self._size = value
        self._changed = True

    @property
    def timeout(self):
        """
        current page load timeout
        :return: (int) timeout
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        if value == self._timeout:
            return
        self._timeout = value
        self._changed = True

    def _create_proxyauth_extension(self, scheme='http', plugin_path=None, driver=CHROME_DRIVER_NAME):
        """
        Proxy Auth Extension
        :param scheme (str): proxy scheme, default http
        :param plugin_path (str): absolute path of the extension
        :param driver (str): name to place in js
        :return: (str) plugin_path
        """

        ext = "zip" if driver == self.CHROME_DRIVER_NAME else "xpi"
        if plugin_path is None:
            if os.name == "posix":
                plugin_path = '/tmp/{}_proxyauth_plugin.{}'.format(driver, ext)
            elif os.name == "nt":
                plugin_path = '{}\\AppData\\Local\\Temp\\{}_proxyauth_plugin.{}'.format(Path.home(), driver, ext)
            else:
                raise OSError("Unsupported OS")

        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "WebDriver Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            }
        }
        """

        background_js = string.Template("""
        var config_chrome = {
            mode: "fixed_servers",
            rules: {
                singleProxy: {
                    scheme: "${scheme}",
                    host: "${proxy_host}",
                    port: parseInt(${proxy_port})
                },
                bypassList: ["exclude.com"]
            }
        };
        var config_gecko = {
            proxyType: "manual",
            http: "http://${proxy_host}:${proxy_port}",
            httpProxyAll: true,
            socksVersion: 4
        };
        var config = "";
        if ("${driver}" == "chrome") {
            config = config_chrome;
        } else {
            config = config_gecko;
        }

        ${driver}.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "${proxy_username}",
                    password: "${proxy_password}"
                }
            };
        }

        ${driver}.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
        """).substitute(**self._use_proxy, scheme=scheme, driver=driver)

        try:
            with zipfile.ZipFile(plugin_path, 'w') as zp:
                zp.writestr("manifest.json", manifest_json)
                zp.writestr("background.js", background_js)
        except OSError:  # [Errno 22] Invalid argument: '...\\browser_proxyauth_plugin.xpi' - file in use
            pass

        return plugin_path

    def _build(self):
        """
        build driver if setting was changed
        :return:
        """
        self._changed = False

        self._quit()

        if self._driver_name == self.CHROME_DRIVER_NAME:
            self._build_chrome()
        elif self._driver_name == self.PHANTOM_DRIVER_NAME:
            self._build_phantom()
        elif self._driver_name == self.FIREFOX_DRIVER_NAME:
            self._build_firefox()
        self.driver.set_window_size(*self._size)
        self.driver.set_page_load_timeout(self.timeout)

    def use_chrome(self):
        """
        use chrome driver
        :return:
        """
        self._driver_name = self.CHROME_DRIVER_NAME

    def _build_chrome(self):
        co = webdriver.ChromeOptions()
        co.add_argument("--start-maximized")
        co.add_argument("--disable-plugins-discovery")
        co.add_argument('--ignore-certificate-errors')
        co.add_argument("--disable-gpu")
        # co.add_argument("--headless")
        if self._use_proxy:
            proxyauth_plugin_path = self._create_proxyauth_extension()
            co.add_argument("--proxy-server=http://{}:{}".format(
                self._use_proxy['proxy_host'], self._use_proxy['proxy_port']))
            co.add_extension(proxyauth_plugin_path)
        if self._custom_ua:
            co.add_argument("user-agent={}".format(self._custom_ua))
        self.display = Display(visible=0, size=self.size)
        self.display.start()
        self.driver = webdriver.Chrome(chrome_options=co, executable_path=self.chrome_path)

    def use_phantom(self):
        """
        use phantomjs driver
        :return:
        """
        self._driver_name = self.PHANTOM_DRIVER_NAME

    def _build_phantom(self):
        service_args = list()
        if self._use_proxy:
            service_args = [
                '--proxy={}:{}'.format(self._use_proxy['proxy_host'], self._use_proxy['proxy_port']),
                '--proxy-auth={}:{}'.format(self._use_proxy['proxy_username'], self._use_proxy['proxy_password']),
                '--proxy-type=https',
                '--ignore-ssl-errors=true',
            ]
        settings_ua_key = 'phantomjs.page.settings.userAgent'
        headers_ua_key = 'phantomjs.page.customHeaders.User-Agent'
        wdc = webdriver.DesiredCapabilities.PHANTOMJS
        if self._custom_ua:
            wdc[settings_ua_key] = self._custom_ua
            wdc[headers_ua_key] = self._custom_ua
        elif settings_ua_key in wdc and headers_ua_key in wdc:
            del wdc[settings_ua_key]
            del wdc[headers_ua_key]
        self.driver = webdriver.PhantomJS(
            executable_path=self.phantomjs_path,
            service_args=service_args,
        )

    def use_firefox(self):
        """
        use gecko driver
        :return:
        """
        self._driver_name = self.FIREFOX_DRIVER_NAME

    def _build_firefox(self):
        profile = webdriver.FirefoxProfile()
        if self._custom_ua:
            profile.set_preference("general.useragent.override", self._custom_ua)
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        proxyauth_plugin_path = ""
        profile.set_preference("browser.tabs.warnOnClose", False)
        if self._use_proxy:
            proxyauth_plugin_path = self._create_proxyauth_extension(driver='browser')
            options.add_argument("--private")
            profile.set_preference("extensions.allowPrivateBrowsingByDefault", True)
            profile.set_preference("extensions.firebug.onByDefault", True)
            profile.set_preference("xpinstall.signatures.required", False)
        self.driver = webdriver.Firefox(
            executable_path=self.firefox_path,
            options=options,
            firefox_profile=profile,
            firefox_binary=self.firefox_bin,
        )
        if self._use_proxy:
            self.driver.install_addon(proxyauth_plugin_path, temporary=True)

    def get_user_agent(self):
        """
        get UserAgent of current driver (not from instance property, but from runtime)
        :return: (str) navigator.userAgent
        """
        if not self.driver:
            self._build()
        return self.driver.execute_script("return navigator.userAgent")

    def setup_proxy(self, proxy):
        """
        set up proxy
        :param proxy: (dict(proxy_user, proxy, password, proxy_host, proxy_port)) proxy dict object
        :return:
        """
        self._use_proxy = proxy
        self._changed = True

    def take_page(self, url, out_file="", adjust_size=True):
        """
        create screen shot
        :param url: (str) site url
        :param out_file: (str) image PNG file
        :param adjust_size: (bool) take all page by height
        :return: (str if out_file else base64) path to screen shot or base64 string
        """
        if self._changed:
            self._build()
        try:
            self.driver.get(url)
        except TimeoutException as e:
            print(e)
            pass
        if adjust_size:
            try:
                width = self.driver.execute_script(
                    "return Math.max(document.body.scrollWidth, document.body.offsetWidth, "
                    "document.documentElement.clientWidth, document.documentElement.scrollWidth, "
                    "document.documentElement.offsetWidth);")
                height = self.driver.execute_script(
                    "return Math.max(document.body.scrollHeight, document.body.offsetHeight, "
                    "document.documentElement.clientHeight, document.documentElement.scrollHeight, "
                    "document.documentElement.offsetHeight);")
            except WebDriverException:
                width, height = self.size
            self.driver.set_window_size(width + 100, height + 100)

        if out_file:
            self.driver.save_screenshot(out_file)
            return os.path.abspath(out_file)

        return self.driver.get_screenshot_as_base64()

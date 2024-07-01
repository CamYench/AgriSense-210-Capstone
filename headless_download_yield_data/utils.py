import pickle
from pathlib import Path
from selenium.webdriver.chrome.webdriver import WebDriver

def save_cookie(driver:WebDriver, path:Path):
    with open(path, "wb") as f:
        pickle.dump(driver.get_cookies(), f)

def load_cookies(driver:WebDriver, path:Path):
    with open(path, "rb") as f:
        cookies = pickle.load(f)
        
        # lets us set cookies for a domain we are not currently at
        # specifically using the Network.setCookie method
        driver.execute_cdp_cmd("Network.enable", {})

        for cookie in cookies:
            driver.execute_cdp_cmd("Network.setCookie", cookie)
            # driver.add_cookie(cookie)
    
    # disable network tracking
    driver.execute_cdp_cmd("Network.disable", {})
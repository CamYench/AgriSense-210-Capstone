import os
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait

from utils import save_cookie, load_cookies
    
# landing page
DEST_URL = "https://calstrawberry1.sharepoint.com/sites/IndustryPortal-Landing/SitePages/MD-District-Report.aspx"
LOGIN_URL = "https://www.californiastrawberries.com/"
LANDING_URL = "https://calstrawberry1.sharepoint.com/sites/IndustryPortal-Landing/"

LOGIN_EMAIL = "dmcdonald@berkeley.edu"
LOGIN_USERNAME = "dmcdonald"
LOGIN_PASSWORD = os.getenv("CALSTRAWB_LOGIN_PASSWORD")
if not LOGIN_PASSWORD:
    LOGIN_PASSWORD = input("Enter your calstraw login password: ")



# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(stream_handler)

# setup driver paths
# download the driver from here 
# https://chromedriver.storage.googleapis.com/index.html?path=114.0.5735.90/
CHROME_EXE_PATH = Path("/home/hbar6/chrome-linux64/chrome")
DRIVER_EXE_PATH = Path("/home/hbar6/chromedriver-linux64/chromedriver")
if not DRIVER_EXE_PATH.exists():
    raise FileNotFoundError(f"Driver binary not found at {DRIVER_EXE_PATH}")
if not CHROME_EXE_PATH.exists():
    raise FileNotFoundError(f"Chrome binary not found at {CHROME_EXE_PATH}")
logger.info(f"Driver found at {DRIVER_EXE_PATH}")


# driver options
chrome_options = Options()
# chrome_options.add_argument("--headless")
# chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument('log-level=3')
chrome_options.binary_location = CHROME_EXE_PATH.as_posix()
driver = webdriver.Chrome(executable_path=DRIVER_EXE_PATH.as_posix(), options=chrome_options)
driver.implicitly_wait(10)

# login management
LOGIN_COOKIES_PATH = Path(__file__).parent / "login.cookies"
if LOGIN_COOKIES_PATH.exists(): # don't need to login again
    URL = DEST_URL
else: # need to login again --> 2FA
    URL = LOGIN_URL


if URL == LOGIN_URL:
    logger.info("Logging in...")
    # start scraping
    driver.get(URL)

    # click industry members button
    ind_mem_btn = driver.find_element_by_xpath("//span[.='Industry Members']")
    ind_mem_btn.click()

    # click login button
    login_btn = driver.find_element_by_xpath("//a[.='Login / Register']")
    login_btn.click()

    # login
    email_input_box = driver.find_element_by_name("txtEmailAddress")
    email_input_box.click()
    email_input_box.send_keys(LOGIN_EMAIL)
    continue_btn = driver.find_element_by_id("Submit")
    continue_btn.click()


    # login to berkeley
    if LOGIN_COOKIES_PATH.exists():
        load_cookies(driver, LOGIN_COOKIES_PATH)

    if not LOGIN_COOKIES_PATH.exists():
        calnet_id_password = LOGIN_PASSWORD
        calnet_id = driver.find_element_by_id("username")
        calnet_id.send_keys(LOGIN_USERNAME)
        calnet_passphrase = driver.find_element_by_id("password")
        calnet_passphrase.send_keys(calnet_id_password)
        submit_btn = driver.find_element_by_name("submit")
        submit_btn.click()

        # wait for login to be successful
        while driver.current_url != LANDING_URL:
            time.sleep(1)

        save_cookie(driver, LOGIN_COOKIES_PATH)
        
elif URL == DEST_URL:
    load_cookies(driver, LOGIN_COOKIES_PATH)
    logger.info("Navigating to destination URL")
    driver.get(URL)
    iframe = driver.find_element_by_xpath("//iframe")
    iframe_src = iframe.get_attribute("src")

    driver.get(iframe_src)
    # driver.switch_to.frame(iframe)
    # logger.info("Switched to iframe")
    
    # select district

    # wait until district dropdown is loaded
    district_dropdown = driver.find_element_by_xpath("//*[@data-parametername='District']")
    WebDriverWait(driver, 10).until(lambda x: district_dropdown.is_displayed())
    salinas_option = district_dropdown.find_element_by_xpath("//option[.='SALINAS/WATSONVILLE']")
    salinas_option.click()
    logger.info("Selected Salinas/Watsonville district")

    # wait until loading is finished
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element_by_class_name("WaitText").is_displayed())

    # select unit
    unit_dropdown = driver.find_element_by_xpath("//*[@data-parametername='Unit']")
    pounds_option = unit_dropdown.find_element_by_xpath("//option[.='POUNDS']")
    pounds_option.click()
    logger.info("Selected POUNDS unit")
    wait_element = driver.find_element_by_class_name("WaitText")
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element_by_class_name("WaitText").is_displayed())

    # select sections
    sections_dropdown = driver.find_element_by_xpath("//*[@data-parametername='Sections']")
    sections_dropdown_btn = sections_dropdown.find_element_by_xpath(".//button")
    sections_dropdown_btn.click()
    daily_section_option = driver.find_element_by_xpath(".//label[.='DAILY']")
    daily_section_option.click()
    logger.info("Selected DAILY section")
    wait_element = driver.find_element_by_class_name("WaitText")
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element_by_class_name("WaitText").is_displayed())

    # generate report
    view_report_btn = driver.find_element_by_class_name("SubmitButton")
    view_report_btn.click()
    logger.info("Generated report")
    wait_element = driver.find_element_by_class_name("WaitText")
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element_by_class_name("WaitText").is_displayed())

    time.sleep(10)

    save_btn = driver.find_element_by_xpath("//a[@title='Export drop down menu']")
    time.sleep(1)
    save_btn.click()
    time.sleep(1)
    excel_dl_btn = driver.find_element_by_xpath("//a[@title='Excel']")
    time.sleep(1)
    excel_dl_btn.click()

    time.sleep(10)
    logger.info("Downloaded excel file")


# done
driver.quit()




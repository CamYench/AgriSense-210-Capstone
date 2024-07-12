import dotenv
import os
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains

from utils import save_cookie, load_cookies

LOADED_ENV = dotenv.load_dotenv(".env")
if not LOADED_ENV:
    raise ValueError("Please create a .env file in the root directory with the following variables: CALSTRAWB_LOGIN_PASSWORD, DEST_DIR")
    
# landing page
DEST_URL = "https://calstrawberry1.sharepoint.com/sites/IndustryPortal-Landing/SitePages/MD-District-Report.aspx"
LOGIN_URL = "https://www.californiastrawberries.com/"
LANDING_URL = "https://calstrawberry1.sharepoint.com/sites/IndustryPortal-Landing/"

# login information
LOGIN_EMAIL = "dmcdonald@berkeley.edu"
LOGIN_USERNAME = "dmcdonald"
LOGIN_PASSWORD = os.getenv("CALSTRAWB_LOGIN_PASSWORD")
if not LOGIN_PASSWORD:
    raise ValueError("Please set CALSTRAWB_LOGIN_PASSWORD environment variable")

# destination directory 
DEST_DIR = os.getenv("DEST_DIR")
if not DEST_DIR:
    raise ValueError("Please set the DEST_DIDR environment variable in .env.")




# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(stream_handler)

# driver options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument('log-level=3')
driver = webdriver.Chrome(options=chrome_options)
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
    ind_mem_btn = driver.find_element(by=By.XPATH, value="//span[.='Industry Members']")
    ind_mem_btn.click()

    # click login button
    login_btn = driver.find_element(by=By.XPATH, value="//a[.='Login / Register']")
    login_btn.click()

    # login
    email_input_box = driver.find_element(by=By.NAME, value="txtEmailAddress")
    email_input_box.click()
    email_input_box.send_keys(LOGIN_EMAIL)
    continue_btn = driver.find_element(by=By.ID, value="Submit")
    continue_btn.click()


    # login to berkeley
    if LOGIN_COOKIES_PATH.exists():
        load_cookies(driver, LOGIN_COOKIES_PATH)

    if not LOGIN_COOKIES_PATH.exists():
        calnet_id_password = LOGIN_PASSWORD
        calnet_id = driver.find_element(by=By.ID, value="username")
        calnet_id.send_keys(LOGIN_USERNAME)
        calnet_passphrase = driver.find_element(by=By.ID, value="password")
        calnet_passphrase.send_keys(calnet_id_password)
        submit_btn = driver.find_element(by=By.NAME, value="submit")
        submit_btn.click()

        # wait for login to be successful
        while driver.current_url != LANDING_URL:
            time.sleep(1)

        save_cookie(driver, LOGIN_COOKIES_PATH)
        
elif URL == DEST_URL:
    driver.set_window_size(1920, 1080)
    driver.get("https://google.com")
    load_cookies(driver, LOGIN_COOKIES_PATH)
    logger.info("Navigating to destination URL")
    driver.get(URL)
    iframe = driver.find_element(by=By.XPATH, value="//iframe")
    iframe_src = iframe.get_attribute("src")

    if not iframe_src:
        raise ValueError("No iframe source found")
    driver.get(iframe_src)
    
    # select district
    # wait until district dropdown is loaded
    district_dropdown = driver.find_element(by=By.XPATH, value="//*[@data-parametername='District']")
    WebDriverWait(driver, 10).until(lambda x: district_dropdown.is_displayed())
    salinas_option = district_dropdown.find_element(by=By.XPATH, value="//option[.='SALINAS/WATSONVILLE']")
    salinas_option.click()
    logger.info("Selected Salinas/Watsonville district")

    # wait until loading is finished
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    # select unit
    unit_dropdown = driver.find_element(by=By.XPATH, value="//*[@data-parametername='Unit']")
    pounds_option = unit_dropdown.find_element(by=By.XPATH,value="//option[.='POUNDS']")
    pounds_option.click()
    logger.info("Selected POUNDS unit")
    # wait_element = driver.find_element(by=By.CLASS_NAME, value="WaitText")
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    # select sections
    sections_dropdown = driver.find_element(by=By.XPATH, value="//*[@data-parametername='Sections']")
    sections_dropdown_btn = sections_dropdown.find_element(by=By.XPATH, value=".//button")
    sections_dropdown_btn.click()
    daily_section_option = driver.find_element(by=By.XPATH, value=".//label[.='DAILY']")
    daily_section_option.click()
    logger.info("Selected DAILY section")
    # wait_element = driver.find_element(by=By.CLASS_NAME, value="WaitText")
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    # generate report
    view_report_btn = driver.find_element(by=By.CLASS_NAME, value="SubmitButton")
    view_report_btn.click()
    logger.info("Generated report")
    # wait_element = driver.find_element(by=By.CLASS_NAME, value="WaitText")
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    time.sleep(10)
    save_btn = driver.find_element(by=By.XPATH, value="//a[@title='Export drop down menu']")
    time.sleep(1)
    save_btn.click()
    time.sleep(1)
    excel_dl_btn = driver.find_element(by=By.XPATH, value="//a[@title='Excel']")
    time.sleep(1)
    excel_dl_btn.click()

    time.sleep(10)
    logger.info("Downloaded excel file")


# done
driver.quit()


# verify download
cwd = Path(__file__).parent
xlsx_files = list(cwd.glob("*.xlsx"))
if len(xlsx_files) == 0:
    raise ValueError("No excel file downloaded")

# move file to destination directory
for xlsx_file in xlsx_files:
    xlsx_file.rename(Path(DEST_DIR) / xlsx_file.name)



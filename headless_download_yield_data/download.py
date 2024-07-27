import os
import time
from pathlib import Path

import dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from utils import load_cookies, save_cookie

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
else:
    DEST_DIR = Path(DEST_DIR)

# exec options
HEADLESS = True




# driver options
chrome_options = Options()
if HEADLESS:
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
    print("Logging in...")
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
    print("Navigating to destination URL")
    driver.get(URL)
    try:
        iframe = driver.find_element(by=By.XPATH, value="//iframe")
    except NoSuchElementException:
        login_again = input("Did not find correct iframe. Cookies likely expired. Login again? Requires 2FA. (y/n): ")
        if login_again.lower() == 'y' and 'berkeley' in driver.current_url:
            username = input("Username: ")
            password = input("Password: ")
            username_element = driver.find_element(by=By.ID, value="username")
            username_element.send_keys(username)
            password_element = driver.find_element(by=By.ID, value="password")
            password_element.send_keys(password)
            submit_element = driver.find_element(by=By.ID, value='submit')
            submit_element.click()
            print("Logged in...")
            print("Sending passcode...")
            verify_text_ele = driver.find_element(by=By.TAG_NAME, value='p')
            verify_text = verify_text_ele.text
            send_passcode_btn = driver.find_element(by=By.CLASS_NAME, value="send-passcode-button")
            send_passcode_btn.click()
            print(f"Verify Test: \n\t{verify_text}")
            passcode = input("Passcode (7 digits): ")
            passcode_input_element = driver.find_element(by=By.ID, value="passcode-input")
            passcode_input_element.send_keys(passcode)
            verify_btn = driver.find_element(by=By.CLASS_NAME, value="verify-button")
            verify_btn.click()
            trust_browser_btn = driver.find_element(by=By.ID, value='trust-browser-button')
            trust_browser_btn.click() 
            stay_signed_in_ele = driver.find_element(by=By.ID, value='idSIButton9')
            stay_signed_in_ele.click()
            print("Logged in...")
            save_cookie(driver, LOGIN_COOKIES_PATH)
            try:
                iframe = driver.find_element(by=By.XPATH, value="//iframe")
            except NoSuchElementException:
                print('Some other error. Couldnt find correct iframe. Exiting...')
                exit(1)
                

        else:
            print("Exiting...")
            exit(1)

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
    print("Selected Salinas/Watsonville district")

    # wait until loading is finished
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    # select unit
    unit_dropdown = driver.find_element(by=By.XPATH, value="//*[@data-parametername='Unit']")
    pounds_option = unit_dropdown.find_element(by=By.XPATH,value="//option[.='POUNDS']")
    pounds_option.click()
    print("Selected POUNDS unit")
    # wait_element = driver.find_element(by=By.CLASS_NAME, value="WaitText")
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    # select sections
    sections_dropdown = driver.find_element(by=By.XPATH, value="//*[@data-parametername='Sections']")
    sections_dropdown_btn = sections_dropdown.find_element(by=By.XPATH, value=".//button")
    sections_dropdown_btn.click()
    daily_section_option = driver.find_element(by=By.XPATH, value=".//label[.='DAILY']")
    daily_section_option.click()
    print("Selected DAILY section")
    # wait_element = driver.find_element(by=By.CLASS_NAME, value="WaitText")
    # time.sleep(10)
    WebDriverWait(driver, 10).until(lambda x: not driver.find_element(by=By.CLASS_NAME, value="WaitText").is_displayed())

    # generate report
    view_report_btn = driver.find_element(by=By.CLASS_NAME, value="SubmitButton")
    view_report_btn.click()
    print("Generated report")
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
    print("Downloaded excel file")


# done
driver.quit()


# verify download
cwd = Path(__file__).parent
xlsx_files = list(cwd.glob("*.xlsx"))
if len(xlsx_files) == 0:
    raise ValueError("No excel file downloaded")

# move file to destination directory
DEST_DIR.mkdir(exist_ok=True)
for xlsx_file in xlsx_files:
    dest_file = DEST_DIR / xlsx_file.name
    print(f"Report moved to {dest_file}")
    xlsx_file.rename(dest_file)



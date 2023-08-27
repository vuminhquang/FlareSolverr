from dtos import (STATUS_ERROR, STATUS_OK, ChallengeResolutionResultT,
                  ChallengeResolutionT, HealthResponse, IndexResponse,
                  V1RequestBase, V1ResponseBase)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    presence_of_element_located, staleness_of, title_is)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
import utils
import logging


def resolve_bingchat(req: V1RequestBase, driver: WebDriver) -> ChallengeResolutionT:
    """resolve_bingchat resolves the challenge for bing.com
    """
    res = ChallengeResolutionT({})
    res.status = STATUS_OK
    res.message = ""

    # Set the user agent
    useragent = utils.set_user_agent(driver, req.userAgent)
    logging.info(f"User agent: {useragent}")

    driver.get(req.url)

    # set cookies if required
    if req.cookies is not None and len(req.cookies) > 0:
        logging.info(f'Setting cookies...')
        for cookie in req.cookies:
            driver.delete_cookie(cookie['name'])
            driver.add_cookie(cookie)
        # reload the page
        driver.get(req.url)
        driver.start_session()  # required to bypass Cloudflare
    else:
        driver.start_session()

    # wait for the page
    if utils.get_config_log_html():
        logging.info(f"Response HTML:\n{driver.page_source}")
    html_element = driver.find_element(By.TAG_NAME, "html")
    page_title = driver.title

    # Execute JavaScript code to retrieve conversation ID
    script = """
    const response = await fetch('https://www.bing.com/turing/conversation/create', { method: 'GET' });
    const data = await response.json();
    return JSON.stringify(data);
    """
    conversation_id = driver.execute_script(script)

    challenge_res = ChallengeResolutionResultT({})
    challenge_res.url = driver.current_url
    challenge_res.status = 200  # todo: fix, selenium not provides this info
    challenge_res.cookies = driver.get_cookies()
    challenge_res.userAgent = utils.get_user_agent(driver)

    if not req.returnOnlyCookies:
        challenge_res.headers = {}  # todo: fix, selenium not provides this info
        challenge_res.response = conversation_id

    res.result = challenge_res
    return res

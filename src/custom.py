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
import time


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

    driver.start_session({})  # required to bypass Cloudflare

    # Execute JavaScript code to retrieve conversation ID
    script = """
    const response = await fetch('https://www.bing.com/turing/conversation/create', { method: 'GET' });
    const data = await response.json();
    return JSON.stringify(data);
    """
    conversation_id = driver.execute_script(script)

    # Get request parameters, if there is parameter 'solvCaptcha' then start the captcha solving process
    if 'solvCaptcha' in req.url:
        bypass_turnstile(driver)

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


# By pass the cloudflare turnstile in bing.com
def bypass_turnstile(driver: WebDriver):
    from selenium.webdriver.support import expected_conditions as EC
    import time
    # Log that we are bypassing the turnstile
    logging.info('Bypassing the turnstile...')

    url = driver.current_url
    time.sleep(2)
    driver.get("https://bing.com")

    # wait for the chat button on bing
    WebDriverWait(driver, 10).until(
        presence_of_element_located((By.CSS_SELECTOR, "#codex > a"))
    )
    # click on the element
    driver.find_element(By.CSS_SELECTOR, "#codex > a").click()

    # wait for the element 'b_sydConvCont' to appear
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "b_sydConvCont"))
    )
    logging.info('b_sydConvCont appeared!')

    driver.execute_script("""
function waitForShadowRoot() {
  const button = document.querySelector("#b_sydConvCont > cib-serp");
  try {
    const shadowRoot1 = button.shadowRoot;
    const shadowRoot2 = shadowRoot1.querySelector("#cib-conversation-main").shadowRoot;
    const shadowRoot3 = shadowRoot2.querySelector("#cib-chat-main > cib-welcome-container").shadowRoot;
    const shadowRoot4 = shadowRoot3.querySelector("div.container-items > cib-welcome-item:nth-child(3)").shadowRoot;
    const targetButton = shadowRoot4.querySelector("button");
    // Perform actions on the target button
    targetButton.click();
  } catch (error) {
    setTimeout(waitForShadowRoot, 100); // Check again after 100 milliseconds
  }
}
waitForShadowRoot();
    """)
    logging.info('Clicked the button')

#     driver.set_script_timeout(30*60)  # 30 minutes
#     button_clicked = driver.execute_async_script("""
# function waitForButtonClick() {
#   return new Promise((resolve) => {
#     function checkButtonClick() {
#       try {
#         const button = document.querySelector("#b_sydConvCont > cib-serp")
#           .shadowRoot.querySelector("#cib-conversation-main")
#           .shadowRoot.querySelector("#cib-chat-main > cib-welcome-container")
#           .shadowRoot.querySelector("div.container-items > cib-welcome-item:nth-child(3)")
#           .shadowRoot.querySelector("button");
#         button.addEventListener('click', () => {
#           resolve(true); // Resolve the promise with true once the button is clicked
#         });
#       } catch (error) {
#         setTimeout(checkButtonClick, 100); // Check again after 100 milliseconds if the button is not found
#       }
#     }
#     checkButtonClick();
#   });
# }
# await waitForButtonClick();
# return true;
#     """)
#
#     logging.info(f"Button clicked: {button_clicked}")

    # now wait for the iframe to appear
#     driver.execute_script("""
# function waitForIFrame() {
#   try {
#     const iframe = document.querySelector("#b_sydConvCont > cib-serp")
#       .shadowRoot.querySelector("#cib-conversation-main")
#       .shadowRoot.querySelector("#cib-chat-main > cib-chat-turn")
#       .shadowRoot.querySelector("cib-message-group.response-message-group")
#       .shadowRoot.querySelector("cib-message")
#       .shadowRoot.querySelector("iframe");
#     const iframeDocument = iframe.contentDocument;
#     const turnstile_widget = iframeDocument.querySelector("#turnstile-widget");
#     // get the iframe inside turnstile_widget
#     const iframe2 = turnstile_widget.querySelector("iframe");
#     const iframe2Root = iframe2.getRootNode();
#     const iframe2Clickable = iframe2Root.querySelector("#challenge-stage > div > label > map > area");
#
#   } catch (error) {
#     setTimeout(waitForIFrame, 100); // Check again after 100 milliseconds
#   }
# }
# waitForIFrame();
#     """)

    # wait for the page
    if utils.get_config_log_html():
        logging.debug(f"Response HTML:\n{driver.page_source}")
    html_element = driver.find_element(By.TAG_NAME, "html")
    page_title = driver.title
    logging.info(f"Page title: {page_title}")

    click_verify(driver)

    # alert the user that the turnstile appeared
    logging.info('Turnstile appeared!')


def click_verify(driver: WebDriver):
    try:
        logging.info("Try to find the Cloudflare verify checkbox...")
        # sleep for 10 seconds
        time.sleep(10)
        from selenium.webdriver.support import expected_conditions as EC
        element = WebDriverWait(driver, 10*60).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#b_sydConvCont > cib-serp')))

        # Get the iframe element
        iframe_element = driver.execute_script(
            'return arguments[0].shadowRoot.querySelector("#cib-conversation-main").shadowRoot.querySelector("#cib-chat-main > cib-chat-turn").shadowRoot.querySelector("cib-message-group.response-message-group").shadowRoot.querySelector("cib-message").shadowRoot.querySelector("iframe")',
            element)
        if iframe_element:
            logging.info("Cloudflare verify iframe found!")
        # iframe = driver.find_element(By.XPATH, "//iframe[@class='captcha-frame']")
        driver.switch_to.frame(iframe_element)
        # check if the iframe is not present
        if iframe_element is None:
            logging.info("Cloudflare verify iframe not found on the page.")
            return
        # driver.switch_to.frame(iframe)
        iframe = driver.find_element(By.XPATH, "//iframe[@title='Widget containing a Cloudflare security challenge']")
        # check if the iframe is not present
        if iframe is None:
            logging.info("Cloudflare verify iframe Widget not found on the page.")
            return
        driver.switch_to.frame(iframe)
        # wait for the checkbox to appear
        logging.info("Wait for the Cloudflare verify checkbox to appear...")
        WebDriverWait(driver, 10*60).until(
            presence_of_element_located((By.XPATH, '//*[@id="challenge-stage"]/div/label/map/img'))
        )
        checkbox = driver.find_element(
            by=By.XPATH,
            value='//*[@id="challenge-stage"]/div/label/map/img',
        )
        if checkbox:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(checkbox, 5, 7)
            actions.click(checkbox)
            actions.perform()
            logging.info("Cloudflare verify checkbox found and clicked!")
    except Exception:
        logging.info("Cloudflare verify checkbox not found on the page.")
    finally:
        driver.switch_to.default_content()

    try:
        logging.info("Try to find the Cloudflare 'Verify you are human' button...")
        button = driver.find_element(
            by=By.XPATH,
            value="//input[@type='button' and @value='Verify you are human']",
        )
        if button:
            actions = ActionChains(driver)
            actions.move_to_element_with_offset(button, 5, 7)
            actions.click(button)
            actions.perform()
            logging.debug("The Cloudflare 'Verify you are human' button found and clicked!")
    except Exception:
        logging.info("The Cloudflare 'Verify you are human' button not found on the page.")

    time.sleep(2)


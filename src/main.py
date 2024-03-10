import json
import logging
import os
import re
import time
from logging.handlers import RotatingFileHandler
from multiprocessing import Process

from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

log_dir = "./log"
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "selenium.log")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

logging.getLogger().addHandler(file_handler)

log = logging.getLogger(__name__)


def parse_time(time_str: str) -> int:
    """
    Parse the time string in the format of "1h 30m 21s" and convert it into seconds.
    """
    time_units = {"h": 3600, "m": 60, "s": 1}
    total_seconds = 0
    time_parts = re.findall(r"(\d+)([hms])", time_str)
    for value, unit in time_parts:
        total_seconds += int(value) * time_units[unit]
    return total_seconds


def open_video_with_profile(
    profiles_location: str, profile_name: str, video_url: str, run_time: int
):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"--user-data-dir={profiles_location}")
    chrome_options.add_argument(f"--profile-directory={profile_name}")

    driver = webdriver.Chrome(options=chrome_options)
    video_name = "Failed before it was possible to read the name"

    try:
        driver.get(video_url)

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.TAG_NAME, "video"))
        )

        try:
            # if not playing, start the video
            driver.find_element(
                by=By.CSS_SELECTOR, value=".ytp-large-play-button.ytp-button"
            ).click()
        except (NoSuchElementException, ElementNotInteractableException):
            pass

        video_element = driver.find_element(by=By.TAG_NAME, value="video")

        log.info("Searching for video name")
        video_name_element = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[@id='title']/h1/yt-formatted-string")
            )
        )
        video_name = video_name_element.find_element(
            By.XPATH, "//*[@id='title']/h1/yt-formatted-string"
        ).text

        action_chains = ActionChains(driver)
        action_chains.context_click(video_element).perform()

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, ".ytp-popup.ytp-contextmenu")
            )
        )

        context_menu = driver.find_element(
            by=By.CSS_SELECTOR, value=".ytp-popup.ytp-contextmenu"
        )
        menu = context_menu.find_element(by=By.CLASS_NAME, value="ytp-panel-menu")

        WebDriverWait(menu, 10).until(EC.element_to_be_clickable((By.XPATH, "*")))

        loop_option = menu.find_element(by=By.XPATH, value="*")
        loop_option.click()

        log.info(
            f"Watching video with name: {video_name}. Will be watching for {run_time} seconds"
        )
        time.sleep(run_time)
    except Exception as e:
        log.error(f"An error occurred: {repr(e)}")
    finally:
        log.info(f"Closing video with name: {video_name}")
        driver.quit()


if __name__ == "__main__":
    with open("./conf.json", "r") as file:
        data = json.load(file)
        video_url = data["video_url"]
        profiles_location = data["profiles_location"]
        profiles = data["profiles"]
        run_time = parse_time(
            data["loop_duration"]
        )  # Set the run time for each video window (in seconds)

    processes = []

    for profile in profiles:
        process = Process(
            target=open_video_with_profile,
            args=(profiles_location, profile, video_url, run_time),
        )
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

import os
import logging
import datetime

import requests
import sh
import click
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from logentries import LogentriesHandler
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv(), override=True)


RANDOM_PASSWORD_GENERATOR_URL = 'https://www.random.org/strings/?num=1&len=12&digits=on&loweralpha=on&unique=on&format=plain&rnd=new'
SLACK_MESSAGE_URL = 'https://slack.com/api/chat.postMessage'
DEFAULT_PASSWORD_FILE = '.password'

SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.environ.get('SLACK_CLIENT_SECRET')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL')
SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
AP_USERNAME = os.environ.get('AP_USERNAME')
AP_PASSWORD = os.environ.get('AP_PASSWORD')
LOG_ENTRIES_TOKEN = os.environ.get('LOG_ENTRIES_TOKEN')

log = logging.getLogger('logentries')
log.setLevel(logging.INFO)
log.addHandler(LogentriesHandler(LOG_ENTRIES_TOKEN))



def generate_random_password():
    log.info('--- GENERATE RANDOM PASSWORD ---')
    log.info('Send request to %s for a new password' % RANDOM_PASSWORD_GENERATOR_URL)
    req = requests.get(RANDOM_PASSWORD_GENERATOR_URL)
    password = req.text.strip()
    log.info('Received a new password from random.org')
    return password


def send_new_password_to_slack(password):
    log.info('--- SEND NEW PASSWORD TO SLACK ---')
    message = 'Wifi password of this month is: %s' % password
    log.info('Send a message about the new password to channel %s' % SLACK_CHANNEL)
    response = requests.post('https://slack.com/api/chat.postMessage', {
        'token': SLACK_TOKEN,
        'channel': SLACK_CHANNEL,
        'text': message,
        'as_user': True
    })
    log.info('Received response %s from Slack API', response)
    return response


def connect_to_eastagile_vnpt(password):
    log.info('--- CONNECT TO LOCAL WIFI ---')
    log.info('Connect local wifi with interface: en1, ssid: EastAgile-VNPT');
    sh.networksetup('-setairportnetwork', 'en1', 'EastAgile-VNPT', password)


def chrome_headless_browser():
    log.info('Initialize a headless chrome browser')
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(chrome_options=options)
    return driver


def get_old_password(password_file=None):
    password_file = password_file or DEFAULT_PASSWORD_FILE
    log.info('Read the previous wifi password stored in %s' % password_file)

    if not os.path.exists(password_file):
        log.error('%s is not exists' % password_file)
        raise Exception()

    with open(password_file, 'r') as f:
        return f.readline().strip()


def store_password(password, password_file=None):
    password_file = password_file or DEFAULT_PASSWORD_FILE
    log.info('Store new password to file %s for the next usage' % password_file)
    with open(password_file, 'w+') as f:
        return f.write(password)


def change_eastagile_vnpt_password(password):
    log.info('--- CHANGE THE LOCAL WIFI PASSWORD ---')
    auth_url = "http://{username}:{router_password}@192.168.1.2".format(username=AP_USERNAME, router_password=AP_PASSWORD)
    url = "http://192.168.1.2"

    driver = chrome_headless_browser()
    log.info('Visit access point adminitration site in with local url %s' % url)
    # NOTE: There's a workaround to avoid the bug blank page with Seleniumn when we try to vist a url with basic authentication
    driver.get(auth_url)
    driver.get(url)

    log.info('Read the page content from the AP admin site')
    log.info('Switch to content frame')
    driver.switch_to_frame('title')

    log.info('Follow all the links and enter wifi security section')
    driver.find_element_by_id('f20').click()
    driver.find_element_by_id('s30').click()
    driver.find_element_by_xpath('//*[@id="32"]/a').click()

    driver.switch_to_frame('mainFrame')

    log.info('Change router password to the new one')
    password_input = driver.find_element_by_css_selector('[name=pskValue]')
    password_input.clear()
    password_input.send_keys(password)

    log.info('Save router password change')
    driver.find_element_by_id('wlwpa_mbssid_value_01').click()

    driver.quit()


@click.command()
@click.option('--password', help='Specify password instead of auto-generating')
@click.option('--password-file', help='Specify password instead of auto-generating')
def main(password, password_file):
    log.info('--- START NEW SESSION ---')
    log.info('Start new session %s', datetime.datetime.now())
    old_password = get_old_password(password_file=password_file)
    connect_to_eastagile_vnpt(old_password)

    new_password = password or generate_random_password()
    change_eastagile_vnpt_password(new_password)

    store_password(new_password, password_file=password_file)

    connect_to_eastagile_vnpt(new_password)
    send_new_password_to_slack(new_password)
    log.info('--- END SESSION ---')


if __name__ == "__main__":
    main()

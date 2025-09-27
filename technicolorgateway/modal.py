import logging
import re

import html2text
from bs4 import BeautifulSoup
from typing import Optional

_LOGGER = logging.getLogger(__name__)

h = html2text.HTML2Text()
h.body_width = 0

regex_broadband_modal = re.compile(
    r" {2}Line Rate +(?P<us>[0-9.]+)"
    r" Mbps (?P<ds>[0-9.]+)"
    r" Mbps *Data Transferred +(?P<uploaded>[0-9.]+)"
    r" .Bytes (?P<downloaded>[0-9.]+) .Bytes "
)

regex_device_modal = re.compile(
    r"(?P<name>[\w\-_]+) ?\|"
    r" ?(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})? ?\|"
    r" ?(?P<mac>\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})"
)


def get_broadband_modal(content):
    body = h.handle(content)
    body = body[body.find("DSL Status") : body.find("Close")]
    body = body.replace("_", "").replace("\n", " ")
    return regex_broadband_modal.search(body).groupdict()


def get_device_modal(content):
    data = []
    soup = BeautifulSoup(content, features="lxml")
    devices = soup.find_all("div", {"class": "popUp smallcard span4"})
    _LOGGER.debug("devices len %s" % len(devices))
    rows = soup.find_all("tr")
    _LOGGER.debug("rows len %s" % len(rows))
    if len(devices) > 0:
        get_data_from_devices(data, devices)
    elif len(rows) > 0:
        return get_data_from_rows(rows)
    return data


def get_data_from_devices(data, devices):
    _LOGGER.debug("get_data_from_devices")
    _LOGGER.debug(f"first device {devices[0]}")
    for device in devices:
        device_contents = device.contents
        name = device_contents[1].contents[1].contents[1].text
        ip_address = device_contents[3].contents[3].contents[1].text
        mac = device_contents[3].contents[5].contents[1].text
        data.append({"name": name, "ip": ip_address, "mac": mac})


# Canonical header mappings
_CANONICAL_MAP = {
    "mac": ["mac", "mac address"],
    "ip": ["ipv4", "ip address"],
    "name": ["hostname"],
    "interface": ["interface"],
    "connected": ["connected time"],
    "expires": ["expires in"],
}

# Build reverse lookup for O(1) lookups
_HEADER_LOOKUP = {
    alt.lower(): canon for canon, alts in _CANONICAL_MAP.items() for alt in alts
}


def normalize_header(header: str) -> Optional[str]:
    """Return canonical header name if recognized, else None."""
    return _HEADER_LOOKUP.get(header.strip().lower())


def get_data_from_rows(rows) -> list[dict[str, str]]:
    """Extract structured data from table rows."""
    data = []
    if not rows:
        return data

    _LOGGER.debug("Parsing %d rows", len(rows))

    for row in rows[1:]:
        cols = row.find_all('td')
        record = {
            canon: col.text.strip()
            for col in cols
            if (canon := normalize_header(col.get('data-title', '')))
        }
        if record:
            data.append(record)

    return data


def get_system_info_modal(content):
    soup = BeautifulSoup(content, "html.parser")
    # Extract product information
    product_info = {}
    for div in soup.select("div.control-group"):
        label = div.select_one("label.control-label")
        span = div.select_one("span.simple-desc")
        if label and span:
            key = label.text.strip()
            value = span.text.strip()
            product_info[key] = value
    return product_info


def get_diagnostics_connection_modal(content):
    soup = BeautifulSoup(content, "html.parser")
    # Extract connection diagnostics
    product_info = {}
    for div in soup.select("div.control-group"):
        label = div.select_one("label.control-label")
        span = div.select_one("span.simple-desc")
        if label and span:
            key = label.text.strip()
            value = span.text.strip()
            product_info[key] = value
    return product_info

import requests
import time
from secrets import (PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY,
                     PORKBUN_DOMAIN, PORKBUN_RECORD_NAMES, PORKBUN_RECORD_TYPE)


def print_safe(*args, **kwargs):
    args = list(args)

    secrets = {
        # PORKBUN_DOMAIN: "<domain>",
        PORKBUN_API_KEY: "<api_key>",
        PORKBUN_SECRET_API_KEY: "<secret_key>"
    }

    for secret, replace in secrets.items():
        for cnt, arg in enumerate(args):
            args[cnt] = arg.replace(secret, replace)

        for key in kwargs.keys():
            kwargs[key] = kwargs[key].replace(secret, replace)

    print(*args, **kwargs)


def get_public_ip():
    """Get the current public IP address."""
    for i in range(10):
        try:
            response = requests.get("http://ipinfo.io/ip")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(60)
            print(f"connection error, retrying in 60 seconds... retry {i+1}")
    return response.text.strip()


def test_ping(api_key, secret_api_key):
    """Ping Porkbun to test if the API key and secret are correct."""
    json = None
    retries = 10
    for retry in range(retries):
        url = "https://porkbun.com/api/json/v3/ping"
        payload = {
            "apikey": api_key,
            "secretapikey": secret_api_key
        }

        response = requests.post(url, json=payload)
        try:
            json = response.json()
            break
        except requests.exceptions.JSONDecodeError:
            if retry == retries - 1:
                raise  # retries exceeded
    return json


def get_domain_dns(api_key, secret_api_key, domain):
    """Get the domain dns records"""
    url = f"https://porkbun.com/api/json/v3/dns/retrieve/{domain}"

    payload = {
        "secretapikey": secret_api_key,
        "apikey": api_key,
        "start": "1",
        "includeLabels": "yes"
    }

    response = requests.post(url, json=payload)
    return response.json()


def update_domain_dns(api_key, secret_api_key, domain, record_id, record_name, record_type, content):
    """Update the domain dns records"""
    url = f"https://porkbun.com/api/json/v3/dns/edit/{domain}/{record_id}"

    payload = {
        "secretapikey": secret_api_key,
        "apikey": api_key,
        "name": record_name,
        "type": record_type,
        "content": content,
        "ttl": "300"
    }

    response = requests.post(url, json=payload)
    return response.json()


def main():
    # Get the current public IP
    current_ip = get_public_ip()
    
    try:
        with open('last_ip.txt', 'r') as file:
            last_ip = file.read().strip()
    except FileNotFoundError:
        last_ip = None

    if current_ip == last_ip:
        return

    # Test the authentication with ping
    ping_response = test_ping(PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY)

    if ping_response.get('status') != 'SUCCESS':
        raise Exception("Failed to authenticate with Porkbun API.")

    records = get_domain_dns(PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY, PORKBUN_DOMAIN)

    success = True
    for record_name in PORKBUN_RECORD_NAMES:
        record_name_find = record_name + '.' + PORKBUN_DOMAIN if record_name != '@' else PORKBUN_DOMAIN
        record_name_real = record_name if record_name != '@' else ''

        print_safe(f"Updating record {record_name_find} for {PORKBUN_DOMAIN} to {current_ip}")

        record_id = None
        for record in records['records']:
            if record['name'] == record_name_find and record['type'] == PORKBUN_RECORD_TYPE:
                record_id = record['id']
                break

        if record_id is None:
            print_safe(f"Records: {records}")
            raise Exception(f"Record {record_name_find} not found in {PORKBUN_DOMAIN}. Skipping update.")

        update_response = update_domain_dns(PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY, PORKBUN_DOMAIN, record_id,
                                            record_name_real, PORKBUN_RECORD_TYPE, current_ip)

        try:
            success = success and update_response["status"] == "SUCCESS"
        except KeyError:
            success = False
        if update_response["status"] == "SUCCESS":
            print_safe(f"Successfully updated {record_name_find} to {current_ip}")
        else:
            print_safe(f"Failed to update {record_name_find} to {current_ip}: {update_response}")

    if success:
        with open('last_ip.txt', 'w') as file:
            file.write(current_ip)
    else:
        print_safe("Failed to update all DNS records.")


if __name__ == "__main__":
    main()

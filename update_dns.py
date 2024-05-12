import requests
from secrets import (PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY,
                     PORKBUN_DOMAIN, PORKBUN_RECORD_NAMES, PORKBUN_RECORD_TYPE)
from commands import Print

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

    Print.prettify(*args, **kwargs)


def get_public_ip():
    """Get the current public IP address."""
    response = requests.get("http://ipinfo.io/ip")
    return response.text.strip()


def test_ping(api_key, secret_api_key):
    """Ping Porkbun to test if the API key and secret are correct."""
    url = "https://porkbun.com/api/json/v3/ping"
    payload = {
        "apikey": api_key,
        "secretapikey": secret_api_key
    }

    response = requests.post(url, json=payload)
    return response.json()


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
    print_safe(f"Current IP: {current_ip}")

    # Test the authentication with ping
    ping_response = test_ping(PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY)
    print_safe(f"Ping Response: {ping_response}")

    if ping_response.get('status') != 'SUCCESS':
        raise Exception("Failed to authenticate with Porkbun API.")

    try:
        with open('last_ip.txt', 'r') as file:
            last_ip = file.read().strip()
    except FileNotFoundError:
        last_ip = None

    if current_ip == last_ip:
        print_safe("IP has not changed. No need to update DNS records.")
        return

    success = True
    for record_name in PORKBUN_RECORD_NAMES:
        print_safe(f"Updating record {record_name} for {PORKBUN_DOMAIN} to {current_ip}")

        records = get_domain_dns(PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY, PORKBUN_DOMAIN)

        if record_name == '@':
            record_name_real = PORKBUN_DOMAIN
        else:
            record_name_real = record_name + '.' + PORKBUN_DOMAIN

        record_id = None
        for record in records['records']:
            if record['name'] == record_name_real and record['type'] == PORKBUN_RECORD_TYPE:
                record_id = record['id']
                break

        if record_id is None:
            raise Exception(f"Record {record_name_real} not found in {PORKBUN_DOMAIN}. Skipping update.")

        update_response = update_domain_dns(PORKBUN_API_KEY, PORKBUN_SECRET_API_KEY, PORKBUN_DOMAIN, record_id,
                                            record_name_real, PORKBUN_RECORD_TYPE, current_ip)

        try:
            success = success and update_response["status"] == "SUCCESS"
        except KeyError:
            success = False
        if update_response:
            print_safe(f"Update Response for {record_name}: {update_response}")
        else:
            print_safe("Failed to update {record_name}.")

    if success:
        with open('last_ip.txt', 'w') as file:
            file.write(current_ip)
    else:
        raise Exception("Failed to update DNS records.")


if __name__ == "__main__":
    main()
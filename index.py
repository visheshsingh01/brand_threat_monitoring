import socket
import whois
import json
import requests

def generate_domain_variants(base_domain):
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()
    
    for i in range(len(base_name)):
        variations.add(base_name[:i] + base_name[i+1:])
        if i > 0:
            variations.add(base_name[:i] + base_name[i] + base_name[i] + base_name[i+1:])
    
    for i in range(len(base_name) - 1):
        swapped = base_name[:i] + base_name[i+1] + base_name[i] + base_name[i+2:]
        variations.add(swapped)
    
    for i in range(1, len(base_name)):
        variations.add(base_name[:i] + '-' + base_name[i:])
    
    tlds = ["com", "net", "org", "co", "info", "biz", "shop"]
    for t in tlds:
        variations.add(f"{base_name}.{t}")
    
    return variations

def get_ip_addresses(domain):
    try:
        result = socket.gethostbyname_ex(domain)
        return result[2] 
    except socket.gaierror:
        return []

def is_domain_active(domain):
    return bool(get_ip_addresses(domain))

def get_domain_info(domain):
    try:
        domain_info = whois.whois(domain)
        return {
            "domain": domain,
            "registrar": domain_info.registrar,
            "creation_date": str(domain_info.creation_date),
            "expiration_date": str(domain_info.expiration_date)
        }
    except Exception:
        return None

if __name__ == "__main__":
    base_domain = "amazon.com"
    variants = generate_domain_variants(base_domain)
    print(f"Generated {len(variants)} domain variations. Checking active domains...")

    active_domains = []

    for domain in variants:
        ip_addresses = get_ip_addresses(domain)
        if ip_addresses:
            domain_details = get_domain_info(domain) or {"domain": domain}
            domain_details["ip_addresses"] = ip_addresses
            active_domains.append(domain_details)
            print(f"Found active domain: {domain}")

    json_filename = "amazon_variants.json"
    with open(json_filename, "w") as json_file:
        json.dump(active_domains, json_file, indent=4)
    
    print(f"JSON file '{json_filename}' has been created with the details of active domains.")

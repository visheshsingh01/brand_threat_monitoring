import socket
import json
import csv
import dns.resolver
import whois

# -------------------------------
# 1. Domain Permutation Functions
# -------------------------------

def basic_variants(base_domain):
    """
    Generate simple variations by omitting letters, doubling letters,
    swapping adjacent characters, inserting hyphens, TLD changes,
    and adding common prefixes/suffixes.
    """
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()

    # Missing letters and doubling letters.
    for i in range(len(base_name)):
        # Remove letter at position i.
        variations.add(base_name[:i] + base_name[i+1:] + '.' + tld)
        # Double letter at position i.
        variations.add(base_name[:i] + base_name[i] + base_name[i] + base_name[i+1:] + '.' + tld)

    # Swap adjacent letters.
    for i in range(len(base_name) - 1):
        swapped = base_name[:i] + base_name[i+1] + base_name[i] + base_name[i+2:]
        variations.add(swapped + '.' + tld)

    # Insert hyphen at every possible position.
    for i in range(1, len(base_name)):
        variations.add(base_name[:i] + '-' + base_name[i:] + '.' + tld)

    # Try different common TLDs.
    common_tlds = ["com", "net", "org", "co", "info", "biz", "shop"]
    for new_tld in common_tlds:
        variations.add(base_name + '.' + new_tld)

    # Add common prefixes and suffixes.
    common_prefixes = ["my", "the", "buy", "shop", "secure", "official"]
    common_suffixes = ["online", "store", "site", "service"]
    for prefix in common_prefixes:
        variations.add(prefix + base_name + '.' + tld)
    for suffix in common_suffixes:
        variations.add(base_name + suffix + '.' + tld)

    # Remove the original domain.
    variations.discard(base_domain)
    return variations

# Homoglyph mapping – characters with visually similar alternatives.
homoglyphs = {
    'a': ['@', '4'],
    'o': ['0'],
    'l': ['1', 'i'],
    'i': ['1', 'l'],
    'e': ['3'],
    's': ['5', '$'],
    # Expand this dictionary as needed.
}

def homoglyph_variants(base_domain):
    """
    Create variants by replacing characters with similar-looking ones.
    """
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()

    for i, char in enumerate(base_name):
        if char.lower() in homoglyphs:
            for replacement in homoglyphs[char.lower()]:
                variant = base_name[:i] + replacement + base_name[i+1:] + '.' + tld
                variations.add(variant)
    return variations

def bitsquatting_variants(base_domain):
    """
    Generate variants by flipping one bit in the ASCII value of each character.
    Only alphanumeric results are kept.
    """
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()

    for i, char in enumerate(base_name):
        original_ord = ord(char)
        for bit in range(8):
            flipped = original_ord ^ (1 << bit)
            new_char = chr(flipped)
            if new_char.isalnum():
                variant = base_name[:i] + new_char + base_name[i+1:] + '.' + tld
                variations.add(variant)
    return variations

# -------------------------------
# 2. DNS and WHOIS Query Functions
# -------------------------------

def get_a_record(domain):
    """Return A records (IP addresses) for the domain."""
    try:
        answers = dns.resolver.resolve(domain, 'A')
        return [rdata.to_text() for rdata in answers]
    except Exception:
        return []

def get_ns_records(domain):
    """Return name server (NS) records for the domain."""
    try:
        answers = dns.resolver.resolve(domain, 'NS')
        return [rdata.to_text() for rdata in answers]
    except Exception:
        return []

def get_mx_records(domain):
    """Return mail server (MX) records for the domain."""
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return [f"{rdata.preference} {rdata.exchange.to_text()}" for rdata in answers]
    except Exception:
        return []

def get_whois_info(domain):
    """Return basic WHOIS info for the domain."""
    try:
        info = whois.whois(domain)
        return {
            "registrar": info.registrar,
            "creation_date": str(info.creation_date),
            "expiration_date": str(info.expiration_date)
        }
    except Exception:
        return {}

# -------------------------------
# 3. Main Processing Function
# -------------------------------

def main():
    base_domain = "amazon.com"
    print(f"Generating domain permutations for: {base_domain}")
    
    # Generate variants using multiple techniques.
    variants = set()
    variants |= basic_variants(base_domain)
    variants |= homoglyph_variants(base_domain)
    variants |= bitsquatting_variants(base_domain)
    
    print(f"Total generated variants: {len(variants)}")
    
    results = []  # To store data for each active domain.

    # Process each variant.
    for domain in variants:
        # Check if domain has an A record (i.e. it's registered and active).
        a_records = get_a_record(domain)
        if not a_records:
            continue  # Skip unregistered or inactive domains.

        # Retrieve additional DNS details.
        ns_records = get_ns_records(domain)
        mx_records = get_mx_records(domain)
        whois_info = get_whois_info(domain)

        domain_data = {
            "domain": domain,
            "a_records": a_records,
            "ns_records": ns_records,
            "mx_records": mx_records,
            "whois": whois_info
        }
        results.append(domain_data)
        print(f"Found active domain: {domain} -> A: {a_records}")

    # -------------------------------
    # 4. Save Data to JSON and CSV
    # -------------------------------

    # Save as JSON.
    with open("domains.json", "w") as json_file:
        json.dump(results, json_file, indent=4)
    print("Data saved to domains.json")

    # Save as CSV.
    with open("domains.csv", "w", newline='') as csvfile:
        fieldnames = ["domain", "a_records", "ns_records", "mx_records", "registrar", "creation_date", "expiration_date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for entry in results:
            row = {
                "domain": entry["domain"],
                "a_records": "; ".join(entry["a_records"]),
                "ns_records": "; ".join(entry["ns_records"]),
                "mx_records": "; ".join(entry["mx_records"]),
                "registrar": entry["whois"].get("registrar", ""),
                "creation_date": entry["whois"].get("creation_date", ""),
                "expiration_date": entry["whois"].get("expiration_date", "")
            }
            writer.writerow(row)
    print("Data saved to domains.csv")

if __name__ == "__main__":
    main()

import socket
import json

# --- Existing Basic Permutations ---

def basic_variants(base_domain):
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()

    # 1. Typos: Missing letters and double letters
    for i in range(len(base_name)):
        # Missing a letter
        variations.add(base_name[:i] + base_name[i+1:] + '.' + tld)
        # Doubling a letter (if possible)
        if i < len(base_name):
            variations.add(base_name[:i] + base_name[i] + base_name[i] + base_name[i+1:] + '.' + tld)

    # 2. Swapping adjacent characters
    for i in range(len(base_name) - 1):
        swapped = base_name[:i] + base_name[i+1] + base_name[i] + base_name[i+2:]
        variations.add(swapped + '.' + tld)

    # 3. Adding hyphens in the domain name
    for i in range(1, len(base_name)):
        variations.add(base_name[:i] + '-' + base_name[i:] + '.' + tld)

    # 4. Common TLD variations (example)
    common_tlds = ["com", "net", "org", "co", "info", "biz", "shop"]
    for new_tld in common_tlds:
        variations.add(base_name + '.' + new_tld)

    # 5. Adding common prefixes/suffixes
    common_prefixes = ["my", "the", "buy", "shop", "secure", "official"]
    common_suffixes = ["online", "store", "site", "service"]
    for prefix in common_prefixes:
        variations.add(prefix + base_name + '.' + tld)
    for suffix in common_suffixes:
        variations.add(base_name + suffix + '.' + tld)

    # Remove the original domain if it exists
    variations.discard(base_domain)
    return variations

# --- Homoglyph Substitutions ---

# Define a mapping of characters to similar-looking characters.
homoglyphs = {
    'a': ['@', '4'],
    'o': ['0'],
    'l': ['1', 'i'],
    'i': ['1', 'l'],
    'e': ['3'],
    's': ['5', '$'],
    # You can expand this mapping as needed.
}

def homoglyph_variants(base_domain):
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()

    # Create variants by substituting each character that has a homoglyph
    for i, char in enumerate(base_name):
        if char.lower() in homoglyphs:
            for replacement in homoglyphs[char.lower()]:
                variant = base_name[:i] + replacement + base_name[i+1:] + '.' + tld
                variations.add(variant)
    return variations

# --- Bitsquatting Variants ---

def bitsquatting_variants(base_domain):
    base_name, tld = base_domain.rsplit('.', 1)
    variations = set()

    # For each character in base_name, flip one bit at a time.
    for i, char in enumerate(base_name):
        original_ord = ord(char)
        for bit in range(8):  # flip each bit in the byte
            # Flip the bit using XOR.
            flipped = original_ord ^ (1 << bit)
            new_char = chr(flipped)
            # Consider only alphanumeric substitutions (you can adjust this filter as needed)
            if new_char.isalnum():
                variant = base_name[:i] + new_char + base_name[i+1:] + '.' + tld
                variations.add(variant)
    return variations

# --- Check if Domain is Active ---

def is_domain_active(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

# --- Main Function to Generate and Check Variants ---

def main():
    base_domain = "amazon.com"
    print(f"Generating variants for {base_domain}...")

    # Get variants from multiple methods.
    variants = set()
    variants |= basic_variants(base_domain)
    variants |= homoglyph_variants(base_domain)
    variants |= bitsquatting_variants(base_domain)
    
    print(f"Total generated variants: {len(variants)}")

    active_domains = []
    for domain in variants:
        if is_domain_active(domain):
            try:
                ip = socket.gethostbyname(domain)
            except Exception:
                ip = "N/A"
            active_domains.append({
                "domain": domain,
                "ip_address": ip
            })
            print(f"Found active domain: {domain} -> {ip}")

    # Save active domains to a JSON file.
    json_filename = "active_domains.json"
    with open(json_filename, "w") as f:
        json.dump(active_domains, f, indent=4)

    print(f"\nActive domains have been saved to '{json_filename}'.")

if __name__ == "__main__":
    main()

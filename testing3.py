import dns.resolver
import whois
import json
import socket

def generate_homoglyph_variations(domain):
    """Generate domain variations using homoglyphs only."""
    base_name, tld = domain.rsplit('.', 1)
    variations = set()

    homoglyphs = {
        'a': ['@', '4', 'á', 'à', 'â', 'ã'],
        'b': ['8', 'ß', 'ḅ'],
        'c': ['ç', '¢', '©'],
        'd': ['ḍ'],
        'e': ['3', '€', 'ë', 'ê', 'è', 'é'],
        'f': ['ƒ'],
        'g': ['9', 'ğ'],
        'h': ['ḧ', '#'],
        'i': ['1', '!', '|', 'ï', 'î', 'í', 'ì'],
        'j': ['ʝ'],
        'k': ['ḳ'],
        'l': ['1', '|', '£'],
        'm': ['ṁ'],
        'n': ['ñ', 'ń'],
        'o': ['0', 'ø', 'ö', 'õ', 'ó', 'ò', 'ô'],
        'p': ['ρ', 'þ'],
        'q': ['9', 'ԛ'],
        'r': ['®', 'ṙ'],
        's': ['$', '5', '§', 'ś'],
        't': ['7', 'τ', '+'],
        'u': ['ü', 'ù', 'ú', 'û'],
        'v': ['ṿ'],
        'w': ['ẃ'],
        'x': ['×', 'ẍ'],
        'y': ['¥', 'ý', 'ÿ'],
        'z': ['2', 'ẓ']
    }

    for i in range(len(base_name)):
        char = base_name[i]
        if char in homoglyphs:
            for replacement in homoglyphs[char]:
                new_variant = base_name[:i] + replacement + base_name[i+1:]
                variations.add(new_variant + '.' + tld)

    return list(variations)

def check_dns(domain):
    """Check if domain has active DNS records and return IP address."""
    try:
        ip_address = socket.gethostbyname(domain)
        return ip_address
    except socket.gaierror:
        return None

def get_whois_info(domain):
    """Retrieve WHOIS information."""
    try:
        w = whois.whois(domain)
        return {
            "domain": domain,
            "registrar": str(w.registrar),
            "creation_date": str(w.creation_date),
            "expiration_date": str(w.expiration_date),
            "name_servers": list(w.name_servers) if w.name_servers else [],
        }
    except Exception:
        return None

def main():
    target_domains = ["facebook.com"]  # Example domains with 'dns'
    
    results = []
    for domain in target_domains:
        print(f"Generating variations for: {domain}")
        variations = generate_homoglyph_variations(domain)
        
        for var_domain in variations:
            print(f"Checking: {var_domain}")
            ip_address = check_dns(var_domain)
            if ip_address:
                whois_info = get_whois_info(var_domain)
                if whois_info:
                    whois_info["ip_address"] = ip_address
                    results.append(whois_info)
    
    # Save results to JSON
    with open("dns_variations.json", "w") as f:
        json.dump(results, f, indent=4)
    
    print(f"Scanning complete. Found {len(results)} active domains.")

if __name__ == "__main__":
    main()

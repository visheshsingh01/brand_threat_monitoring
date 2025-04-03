import subprocess
import json
import socket

def run_dnstwist(domain, timeout=180):
    """Run dnstwist on the given domain and capture the output."""
    try:
        print(f"Running dnstwist on {domain} (timeout={timeout}s)...")
        result = subprocess.run(
            ["dnstwist", "--format", "json", domain],
            capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        print("dnstwist timed out!")
        return None
    
    if result.returncode != 0:
        print("Error running dnstwist:", result.stderr)
        return None

    if not result.stdout.strip():
        print("dnstwist did not return any output.")
        return None

    print("dnstwist completed, parsing output...")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print("Error parsing JSON output:", e)
        return None

def resolve_domain(domain):
    """Resolve the domain to its IP addresses using the socket module."""
    ip_addresses = set()
    try:
        infos = socket.getaddrinfo(domain, None)
        for info in infos:
            ip_addresses.add(info[4][0])
    except Exception as e:
        return ["No IP found"]
    
    return list(ip_addresses) if ip_addresses else ["No IP found"]

def extract_fake_domains(dnstwist_output):
    """Extract fake domains, resolve their IP addresses, and capture the permutation type."""
    fake_domains = []
    
    for entry in dnstwist_output:
        if entry.get("fuzzer") != "original":
            domain_name = entry.get("domain")
            ip_addresses = resolve_domain(domain_name)
            
            fake_domains.append({
                "domain": domain_name,
                "ip_address": ip_addresses,
                "permutation": entry.get("fuzzer")
            })
    
    return fake_domains

def save_to_json(data, filename):
    """Save the extracted fake domains data to a JSON file."""
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Fake domains saved to {filename}")

if __name__ == "__main__":
    domain = input("Enter the domain name to analyze: ").strip()
    output_file = "fake_domains.json"
    
    dnstwist_data = run_dnstwist(domain)
    
    if dnstwist_data:
        fake_domains = extract_fake_domains(dnstwist_data)
        save_to_json(fake_domains, output_file)
    else:
        print("No data to save.")

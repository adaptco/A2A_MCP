# GitHub Pages Domain Verification and Firewall Allowlisting

This note summarizes the values and procedures referenced during the ADAPTCO onboarding workflow for the `queen.boo` Pages domain and the associated network allowlist.

## GitHub Pages Domain Verification

To verify the custom domain with GitHub Pages:

1. **Create the TXT record** with your DNS provider.
   - **Record type:** `TXT`
   - **Hostname:** `_github-pages-challenge-adaptco.queen.boo`
   - **Value:** `50d4b36d1d8c5b02a8fcfe250df2b8`
2. Allow up to 24 hours for DNS propagation. Verification may succeed earlier depending on the provider's TTL configuration.
3. Visit the [GitHub Pages verified domains panel](https://github.com/settings/pages_verified_domains/queen.boo) to confirm the status once propagation completes.

## Firewall Allowlist

Normalize the following addresses as CIDR ranges when configuring firewalls or security groups:

- `3.134.238.10/32`
- `3.129.111.220/32`
- `52.15.118.168/32`
- `74.220.50.0/24`
- `74.220.58.0/24`

Examples for common platforms using TCP port `3030` as the placeholder application port:

### UFW (Debian/Ubuntu)

```bash
sudo ufw allow from 3.134.238.10 to any port 3030 proto tcp
sudo ufw allow from 3.129.111.220 to any port 3030 proto tcp
sudo ufw allow from 52.15.118.168 to any port 3030 proto tcp
sudo ufw allow from 74.220.50.0/24 to any port 3030 proto tcp
sudo ufw allow from 74.220.58.0/24 to any port 3030 proto tcp
```

### Raw iptables

```bash
iptables -I INPUT -p tcp -s 3.134.238.10/32 --dport 3030 -j ACCEPT
iptables -I INPUT -p tcp -s 3.129.111.220/32 --dport 3030 -j ACCEPT
iptables -I INPUT -p tcp -s 52.15.118.168/32 --dport 3030 -j ACCEPT
iptables -I INPUT -p tcp -s 74.220.50.0/24    --dport 3030 -j ACCEPT
iptables -I INPUT -p tcp -s 74.220.58.0/24    --dport 3030 -j ACCEPT
```

Persist the rules using the appropriate tooling for your distribution (for example, `iptables-save`).

### AWS Security Group (CLI)

```bash
aws ec2 authorize-security-group-ingress --group-id sg-XXXXXXXX \
  --protocol tcp --port 3030 --cidr 3.134.238.10/32

aws ec2 authorize-security-group-ingress --group-id sg-XXXXXXXX \
  --protocol tcp --port 3030 --cidr 3.129.111.220/32

aws ec2 authorize-security-group-ingress --group-id sg-XXXXXXXX \
  --protocol tcp --port 3030 --cidr 52.15.118.168/32

aws ec2 authorize-security-group-ingress --group-id sg-XXXXXXXX \
  --protocol tcp --port 3030 --cidr 74.220.50.0/24

aws ec2 authorize-security-group-ingress --group-id sg-XXXXXXXX \
  --protocol tcp --port 3030 --cidr 74.220.58.0/24
```

Replace `sg-XXXXXXXX` with the actual security group identifier and update the port number to match the service being protected. Consider pairing allowlist rules with deny or rate-limit controls for all other sources and enabling logging for audit trails.

## Ownership Lookups

Run these commands locally if you need to confirm ASN or ownership data for any of the addresses:

```bash
curl https://rdap.arin.net/registry/ip/3.134.238.10 | jq '.name, .entities[0].vcardArray[1][]'
whois 3.134.238.10
```

Replace the IP with another address from the list as needed.

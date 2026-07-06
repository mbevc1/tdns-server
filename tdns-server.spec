%if 0%{?fedora_ver} || 0%{?rhel_ver} || 0%{?centos_ver} || 0%{?almalinux_ver} || 0%{?rocky_ver}
#       Compression type and level for source/binary package payloads.
#               "w9.gzdio"      gzip level 9 (default).
#               "w9.bzdio"      bzip2 level 9.
#               "w7.xzdio"      xz level 7, xz's default.
#               "w7.lzdio"      lzma-alone level 7, lzma's default
%define _source_payload w9.xzdio
%define _binary_payload w9.xzdio
#%else
%endif

%global dns_user  dns-server
%global dns_group dns-server

Name:           tdns-server
Version:        %{_version}
Release:        %{_release}%{?dist}
Summary:        Technitium DNS Server

License:        GPL
URL:            https://technitium.com/dns/
Source0:        https://download.technitium.com/dns/archive/%{version}/DnsServerPortable.tar.gz
Source1:        https://raw.githubusercontent.com/TechnitiumSoftware/DnsServer/refs/tags/v%{version}/LICENSE
Source2:        https://raw.githubusercontent.com/TechnitiumSoftware/DnsServer/refs/tags/v%{version}/README.md
BuildRoot:      %{_tmppath}/%{name}-%{version}-build

BuildArch:      noarch
#BuildRequires:  systemd tar
Requires(pre):      shadow-utils
Requires(post):     systemd
Requires(preun):    systemd
Requires(postun):   systemd
Requires:       systemd, libicu, aspnetcore-runtime-10.0, dotnet-runtime-10.0

%description
Technitium DNS Server is a cross-platform authoritative and recursive DNS server
with DNS-over-HTTPS, DNS-over-TLS, and more.

This package installs the server to /opt/technitium/dns/ and runs it as the
unprivileged '%{dns_user}' system user, matching the upstream hardened systemd
unit.

%prep
mkdir -p tdns
tar -xzf %{SOURCE0} -C tdns

%build
# No compilation required

%install
rm -rf %{buildroot}

# Install Technitium DNS to /opt/technitium/dns
mkdir -p %{buildroot}/opt/technitium/dns
cp -a tdns/* %{buildroot}/opt/technitium/dns/
mkdir -p %{buildroot}%{_docdir}/%{name}
cp -a %{SOURCE2} %{buildroot}%{_docdir}/%{name}/


# Install systemd unit as dns.service
mkdir -p %{buildroot}/etc/systemd/system
cp %{buildroot}/opt/technitium/dns/systemd.service %{buildroot}/etc/systemd/system/dns.service

# Create config directory
mkdir -p %{buildroot}/etc/dns

# Create log directory (referenced by ReadWritePaths= in unit)
mkdir -p %{buildroot}/var/log/technitium/dns

%files
%license LICENSE
%doc %{_docdir}/%{name}
%attr(-, %{dns_user}, %{dns_group}) /opt/technitium/
/etc/systemd/system/dns.service
%dir %attr(0750, %{dns_user}, %{dns_group}) /etc/dns
%dir %attr(0750, %{dns_user}, %{dns_group}) /var/log/technitium
%dir %attr(0750, %{dns_user}, %{dns_group}) /var/log/technitium/dns
#%config(noreplace) /etc/dns/auth.config
#%config(noreplace) /etc/dns/dns.config
#%config(noreplace) /etc/dns/log.config

%pre
# Create the dns-server group and user before files are laid down so that
# %attr() ownership in %files resolves correctly.
getent group %{dns_group} >/dev/null || \
    groupadd --system %{dns_group}
getent passwd %{dns_user} >/dev/null || \
    useradd --system \
            --no-create-home \
            --gid %{dns_group} \
            --home-dir /opt/technitium/dns \
            --shell /usr/sbin/nologin \
            --comment "Technitium DNS Server" \
            %{dns_user}
exit 0

%post
%systemd_post dns.service

#LOGFILE="/var/log/tdns-install.log"

# Open firewall port 5380 (if firewalld is running)
#if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active firewalld >/dev/null 2>&1; then
#    firewall-cmd --permanent --add-port=5380/tcp >> $LOGFILE 2>&1 || :
#    firewall-cmd --reload >> $LOGFILE 2>&1 || :
#    #echo "[INFO] Opened port 5380/tcp via firewalld." >> $LOGFILE
#fi

# Create SELinux policy (stub - extend as needed)
#if command -v semanage >/dev/null 2>&1; then
#    semanage port -a -t http_port_t -p tcp 5380 2>/dev/null || :
#    #echo "[INFO] Labeled port 5380 with SELinux http_port_t." >> $LOGFILE
#fi

# Make sure existing data from older versions (where the service ran as root)
# is owned by the dns-server user on install/upgrade.
if [ $1 -ge 1 ]; then
    chown -R %{dns_user}:%{dns_group} /etc/dns /var/log/technitium /opt/technitium/dns >/dev/null 2>&1 || :
fi

# Warn (but do not auto-disable) if systemd-resolved is occupying port 53.
# The upstream install.sh disables systemd-resolved unconditionally; we leave
# that decision to the operator since it is an invasive change to system
# networking. Without this, dns.service will fail to bind port 53 on most
# modern distros.
if systemctl is-active systemd-resolved >/dev/null 2>&1; then
    echo
    echo "WARNING: systemd-resolved is active and likely holding port 53."
    echo "         dns.service may fail to bind. To free port 53:"
    echo "             systemctl disable --now systemd-resolved"
    echo "             systemctl restart dns.service"
    echo
fi

# Enable and start service on initial install only
if [ $1 -eq 1 ]; then
    systemctl enable --now dns.service #>> $LOGFILE 2>&1 || :
fi

# Ensure the systemd unit is present and enabled
if ! systemctl list-unit-files | grep -q '^dns.service'; then
    #echo "[ERROR] dns.service not found in systemd unit files!" | tee -a $LOGFILE
    exit 1
fi

if ! systemctl is-enabled dns.service >/dev/null 2>&1; then
    #echo "[ERROR] dns.service is not enabled." | tee -a $LOGFILE
    exit 1
fi

# Ensure the service is running
if ! systemctl is-active dns.service >/dev/null 2>&1; then
    #echo "[ERROR] dns.service is not running." | tee -a $LOGFILE
    exit 1
fi

# Check if something is listening on port 5380 (web console)
# Wait a bit for service to come up :|
sleep 1
if ! ss -tln | grep -q ':5380'; then
    #echo "[ERROR] Port 5380 is not listening." | tee -a $LOGFILE
    exit 1
fi

echo
echo "Technitium DNS Server installed successfully."
echo "Open http://$(hostname):5380/ to access the web console."

%preun
%systemd_preun dns.service

# Only stop and disable on uninstall, not upgrade
if [ $1 -eq 0 ]; then
    systemctl disable --now dns.service
fi

%postun
%systemd_postun_with_restart dns.service

# On full uninstall remove the system user and group we created in %pre.
if [ $1 -eq 0 ]; then
    if getent passwd %{dns_user} >/dev/null; then
        userdel %{dns_user} >/dev/null 2>&1 || :
    fi
    if getent group %{dns_group} >/dev/null; then
        groupdel %{dns_group} >/dev/null 2>&1 || :
    fi
fi

%check
echo "Skipping runtime validation during RPM build."
exit 0

%changelog
* Mon Jul 06 2026 Marko Bevc <marko@bevc.net> - 15.3.0-1
- Fixed multiple RFC compliance issues reported by Yuxiao Wu, Yunyi Zhang, Baojun Liu, and Haixin Duan from Tsinghu University.
- Fixed an issue reported by Lawrence LUO Junhua in the Apps section default permissions by removing the Delete permission for DNS Administrators group. This permissions can be misused by users in the DNS Administrators group to perform privilege escalation to get access to the DNS server's Administration section. For existing installations, it is recommended to manually remove the Delete permission for DNS Administrators group for the Apps section.
- Fixed an issue in the Settings section default permissions by removing the Delete permission for DNS Administrators group. This permission can be misused by users in the DNS Administrators to use backup/restore config files allowing to change options in the DNS Server's Administration section. For existing installations, it is recommended to manually remove the Delete permission for DNS Administrators group for the Settings section.
- Fixed multiple Stored XSS vulnerabilities in the Web Console reported by Daniel Goldberg and Anner Klein from Tenzai.
- The Linux automated installer script now supports Alpine Linux with OpenRC service. Thanks to @Wrong-Code for the PR #1889.
- Added Unix Socket support for the Web Service and DNS-over-HTTP Optional protocol. Thanks to Ingmar Stein (@IngmarStein) for the PR #1753.
- The Zones section now support search/filtering options along with option to delete multiple zones at once.
- Added option in user drop down menu to disable Update Notification. This option will prevent the Web Console from checking for updates only for the current user. This option is stored in web browser's local storage.
- Added "Enable Check For Update" option in Settings > General section which enables the DNS Server to check if an update is available when the Check For Update API is called which usually occurs after a user logs into the Web Console. Disabling this option will disable check for software update for all users such that the API will always return no update available response without actually checking for updates.
- Added "CSP Frame Ancestors Header" option in Settings > Web Service section to allow configuring the Content Security Policy (CSP) Frame Ancestors header value.
- Added "Enable Redirect To Help Page" option in Setting > Optional Protocols section to control if the DoH help page should be shown when a user visits the /dns-query DoH end point with a web browser.
- Added "No Stack Trace" option in Settings > Logging section to enable logging only short error messages instead of full exception stack trace.
- Updated SSO implementation to setup user info endpoint JSON key map for supported claim types.
- Implemented support for Locally Served DNS Zones (RFC 6303) & Special-Use Domain Names (RFC 6761). The default internal zones are removed and they are now managed under this new implementation. A new option "Locally Served DNS Zones" is added in Settings > Recursion section to allow completely disabling these local zones. A single zone can be disabled/overridden by adding a Stub or Conditional Forwarder zone for it.
- Updated TXT record implementation to allow configuring generic character-strings enabling support for Unicode strings.
- Fixed issue in DNSSEC validation that caused the "missing RRSIG" validation failure issue in certain cases when the DNS server is configured to use forwarders.
- Added new Health Check API /api/dnsClient/healthCheck to enable automated health check for the DNS server without causing query log entries.
- Added new Status API /api/status obsoleting the SSO Status API /api/sso/status.
- Updated List Zones API /api/zones/list to allow filtering zones by name and type.
- Block Page App: Updated the app to support online signing for custom CA certificate configured in the app's config. Online signing now supports both RSA and ECDSA algorithms. Thanks to Roy Hagland (@Hemsby) for PR #1897.
- Geo Continent & Geo Country Apps: Updated both apps to support creating custom groups in app config which can then be used with APP record's JSON config.
- Multiple other minor bug fixes and improvements.

* Sat May 09 2026 Marko Bevc <marko@bevc.net> - 15.2.0-1
- Updated SSO implementation to read claims from user info endpoint when available and to use HttpClientNetworkHandler as backchannel.
- Added new Web Service Reverse Proxy Addresses option to allow defining reverse proxies that are allowed such that Real IP header only works for these proxies.
- The Settings API has been updated to rename reverseProxyNetworkACL option to dnsReverseProxyNetworkACL to avoid confusion since this option is used only with DNS Optional Protocols.
- Multiple other minor bug fixes and improvements.

* Sun May 03 2026 Marko Bevc <marko@bevc.net> - 15.1.0-1
- Added option to allow configuring SSO Scopes as required by the SSO provider.
- Updated Prometheus metrics API text output to use correct naming convention.
- Multiple other minor bug fixes and improvements.

* Sun Apr 26 2026 Marko Bevc <marko@bevc.net> - 15.0.1-1
- Fixed issue that caused cluster API token to fail to sync when a secondary node joins a cluster.
- Fixed issue of incorrect sync state for SSO group map on secondary nodes.
- Added SSO scopes required by some SSO providers.
- Fixed typo in Prometheus metrics API text output.

* Sat Apr 25 2026 Marko Bevc <marko@bevc.net> - 15.0.0-1
- Upgraded codebase to use .NET 10 runtime. If you had manually installed the DNS Server or .NET Runtime earlier then you must install .NET 10 Runtime manually before upgrading the DNS Server.
- Updated the DNS Server's install script for Linux to install the DNS Server to run as a non-root systemd service. Existing installations would work the same after the upgrade.
- Updated the DNS Server's Installer for Windows to install the DNS Server to run as a non-system service. Existing installations would work the same after the upgrade.
- The HTTP API now supports passing session token via the Authorization: Bearer <token> HTTP header. The older token parameter in query string and form data is supported for backward compatibility.
- Breaking change in DNS Server Cluster setup: all nodes must be upgraded for the Cluster to work.
- Added support for Single Sign-On (SSO) with OpenID Connect (OIDC). Thanks to @zstinnett for the PR.
- Added new EDNS Client Subnet (ECS) Source Address feature to read client's source IP address from the ECS option in DNS requests over UDP or TCP.
- Added new option in Import Zone feature to allow overwriting entire zone such that only the records being imported will exist (along with zone's SOA record) after the import process.
- Added option to manually activate primary zone's Key Signing Key (KSK) status to prevent regular DS record lookups in parent zone.
- Added new option in Settings > General section to configure UDP listener socket send and receive buffer size.
- Added support for Prometheus with new metrics API call that returns lifetime counters.
- Updated DNS Server to dynamically bind UDP listeners to local interface IP address on first request to ANY address, ensuring responses are sent on the correct interface.
- Updated DHCP Server's DNS entry management to allow having persistent DNS records for reserved leases with hostname configured even when reserved lease was not allocated.
- Implemented new IPv6 Mode option in DNS Server for better performance on dual-stack networks.
- Implemented support for EDNS EXPIRE option (RFC 7314).
- Fixed bug in DNS-over-QUIC (DoQ) optional protocol that caused the DoQ service to fail to accept new connections.
- Fixed DNS amplification vulnerability caused by Self-Pointed Glue Records. Reported by Shuhan Zhang, Dan Li, and Baojun Liu from Tsinghua University.
- Fixed DNS amplification vulnerability caused by Aggressive Fetching of DNSSEC Records. Reported by Shuhan Zhang, Dan Li, and Baojun Liu from Tsinghua University.
- Fixed DNS amplification vulnerability caused by Cyclic Name Server Delegation. Reported by Qifan Zhang, Palo Alto Networks.
- Implemented new Change Theme menu feature with support for automatic dark/light mode based on host system's theme.
- Added a new Amber theme for improved visual ergonomics and accessibility. Thanks to @daedaevibin for the PR.
- The Logs > Query Logs section now supports Live Update feature for automatically refreshing query logs in results.
- The Dashboard now includes a convenient option at Top Blocked Domains to enable/disable blocking.
- Query Logs (PostgreSQL) App: Added new app to support PostgreSQL as the backend database for query logs. Thanks to @scj643 for the PR.
- Query Logs (Sqlite, MySQL, SQL Server) Apps: Updated pagination logic to significantly improve query performance. Thanks to @jimstrang for the PR.
- Block Page App: Updated the app to implement online SSL certificate signing feature to allow it to do SSL MiTM when app's self-signed root certificate is installed on client systems.
- Wild IP App: Added new allowedNetworks option in the APP record data config for configuring allowed networks to prevent misuse/abuse.
- Drop Requests App: Added new allowedLocalEndPoints option to allow requests coming only from the listed DNS Server Local End Points.
- Geo Continent App and Geo Country App: Updated apps to support Autonomous System Number (ASN) entries in APP record data.
- MISP Connector App: Removed the app since it is not feasible to be supported.
- All DNS Apps now support comments in its JSON config. The APP record data JSON too now supports comments.
- All DNS Apps now include a Read Me file in MD format. Thanks to @zbalkan for the PR.
- Fresh installation of DNS Server now uses platform specific log folder path.
- Multiple other minor bug fixes and improvements.

* Tue Dec 23 2025  Marko Bevc <marko@bevc.net> - 14.3.0-1
- Added support for Dark Mode. Thanks to @skidoodle for the PR.
- Updated Catalog zones implementation to allow adding Secondary zones as members.
- Updated Restore Settings option to allow importing backup zip files from older DNS server versions.
- Added new options in Settings to configure default TTL values for NS and SOA records.
- Added DNS record overwrite option in DHCP Scopes to allow dynamic leases to overwrite any existing DNS A record for the client domain name.
- Advanced Blocking App: Added new option to allow configuring block list update interval in minutes.
- Split Horizon App: Updated app to support mapping domain names to group for address translation feature.
- Multiple other minor bug fixes and improvements.

* Sat Nov 22 2025 Marko Bevc <marko@bevc.net> - 14.2.0-1
- Fixed bug in Clustering implementation which prevented using IPv4 and IPv6 addresses together. Thanks to @ruifung for the PR.
- There is also a breaking change in clustering and thus all cluster nodes must be upgraded to this release to avoid issues.
- Updated the "Allow / Block List URLs" option implementation to support comment entries.
- Advanced Blocking App: Updated app to implement blockingAnswerTtl option to allow specifying the TTL value used in blocked response.
- Log Exporter App: Updated the app to add EDNS logging support. Thanks to @zbalkan for the PR.
- MISP Connector App: Added new app that can block malicious domain names pulled from MISP feeds. Thanks to @zbalkan for the PR.
- Multiple other minor bug fixes and improvements.

* Sun Nov 16 2025 Marko Bevc <marko@bevc.net> - 14.1.0-1
- Updated Clustering implementation to allow configuring multiple custom IP addresses. This introduces a breaking change in the API and thus all cluster nodes must be upgraded to this release for them to work together.
- Fixed issues related to user and group permission validation when Clustering is enabled which caused permission bypass when accessing another node.
- Fixed bug that caused the Advanced Blocking app to stop working.
- Added environment variables for TLS certificate path, certificate password, and HTTP to HTTPS redirect option. Thanks to simonvandermeer for the PR.
- Updated Hagezi block list URLs. Thanks to hagezi for the PR.
- Other minor changes and improvements.

* Sun Nov 09 2025 Marko Bevc <marko@bevc.net> - 14.0.1-1
- Fixed bugs in the Force Update Block List and Temporary Disable Blocking API calls.
- Fixed session validation bypass bug during proxying request to another node when Clustering is enabled.
- Fixed issue of failing to load app config due to text encoding issues.
- Fixed issue of failure to load old config file versions due to validation failures in some cases.
- Updated GUI docs for Cluster initialization and joining.
- Other minor changes and improvements.

* Sat Nov 08 2025 Marko Bevc <marko@bevc.net> - 14.0.0-1
- Upgraded codebase to use .NET 9 runtime. If you had manually installed the DNS Server or .NET 8 Runtime earlier then you must install .NET 9 Runtime manually before upgrading the DNS server.
- This major release has a breaking changes in the Change Password HTTP API so its advised to test your API client once before deploying to production.
- Fixed Denial of Service (DoS) vulnerability in the DNS server's rate limiting implementation reported by Shiming Liu from the Network and Information Security Lab, Tsinghua University. The DNS Server now has a redesigned rate limiting implementation with different Queries Per Minute (QPM) options in Settings that help mitigate this issue.
- Fixed Cache Poisoning vulnerability achieved using a IP fragmentation attack reported by Yuxiao Wu from the NISL Lab Security, Tsinghua University. The DNS server fixes this issue by adding missing bailiwick validations for NS record in referral responses.
- Fixed DNSSEC Downgrade vulnerability that made it possible to bypass validation when one of domain name's DNSSEC algorithm was not supported by the DNS server.
- Implemented Clustering feature where you can now create a cluster of two or more DNS server instances and manage all of them from a single DNS admin web console by logging into anyone of the Cluster nodes. It also features showing aggregate Dashboard data for the entire cluster.
- Added TOTP based Two-factor authentication (2FA) support.
- Added options to configure UDP Socket pooling feature in Settings.
- Fixed bug in zone file parsing that failed to parse records when their names were not FDQN and matched with name of a record type.
- Fixed issue with internal Http Client to retry for IPv4 addresses too when Prefer IPv6 option is enabled and IPv6 address failed to connect.
- Fixed bug of missing NSEC/NSEC3 record in response for wildcard and Empty Non-terminal (ENT) records in Primary zones.
- Fixed multiple issues in Prefetch and Auto Prefetch implementation that caused undesirable frequent refreshing of cached data in certain cases.
- Query Logs (Sqlite) App: Updated app to use Channels for better performance.
- Query Logs (MySQL) App: Updated app to use Channels for better performance. Fixed bug in schema for protocol parameter causing overflow.
- Query Logs (SQL Server) App: Updated app to use Channels for better performance.
- NX Domain App: Updated app to support Extended DNS Error messages.
- Multiple other minor bug fixes and improvements.

* Sat Apr 26 2025 Marko Bevc <marko@bevc.net> - 13.6.0-1
- Added option to import a zone file when adding a Primary or Forwarder zone. This allows using a template zone file when creating new zones.
- Updated the web GUI to support custom lists for DNS Client server list, quick block drop down list and quick forwarders drop down list.
- Updated the record filtering option in zone edit view to support wildcard based search.
- Fixed issue in DNS-over-QUIC service that caused the service to stop working due to failed connection handshake.
- Query Logs (Sqlite) App: Updated app to support VACCUM option to allow trimming database file on disk to reduce its size.
- Geo Continent App and Geo Country App: Updated both apps to support macro variable to simplify APP record data JSON configuration.
- Multiple other minor bug fixes and improvements.

* Mon Apr 07 2025 Marko Bevc <marko@bevc.net> - 13.5.0-1
- First upgrade package of Technitium DNS Server
- Parser supports BIND extended zone file format
- Added feature to filter records in the zone editor based on its name or type
- Added support for user specified DNSSEC private keys
- Implemented RFC 8080 to add support for Ed25519 (15) and Ed448 (16) DNSSEC algorithms
- Added support for writing DNS logs to Console (STDOUT) along with existing option to write to a file
- Multiple other minor bug fixes and improvements

* Thu Apr 03 2025 Marko Bevc <marko@bevc.net> - 13.4.3-1
- Initial RPM release of Technitium DNS Server
- More about changes: https://github.com/TechnitiumSoftware/DnsServer/blob/master/CHANGELOG.md

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
Requires(post):     systemd
Requires(preun):    systemd
Requires(postun):   systemd
Requires:       systemd, libicu, aspnetcore-runtime-8.0, dotnet-runtime-8.0

%description
Technitium DNS Server is a cross-platform authoritative and recursive DNS server
with DNS-over-HTTPS, DNS-over-TLS, and more.

This package installs the server to /opt/technitium/dns/.

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

%files
%license LICENSE
%doc %{_docdir}/%{name}
/opt/technitium/
/etc/systemd/system/dns.service
%dir /etc/dns
#%config(noreplace) /etc/dns/auth.config
#%config(noreplace) /etc/dns/dns.config
#%config(noreplace) /etc/dns/log.config

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

%check
echo "Skipping runtime validation during RPM build."
exit 0

%changelog
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

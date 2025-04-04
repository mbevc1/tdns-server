[![Build and Publish](https://github.com/mbevc1/tdns-server/actions/workflows/build.yaml/badge.svg)](https://github.com/mbevc1/tdns-server/actions/workflows/build.yaml)

# tdns-server
Technitium DNS server RPM package

## RHEL clones repo setup

Add repository setting using command:

```terminal
dnf config-manager --add-repo https://raw.githubusercontent.com/mbevc1/tdns-server/refs/heads/main/tdns-server.repo
```

or to add manually:

```terminal
$ sudo vim /etc/yum.repos.d/tdns-server.repo
[tdns-server]
name=Technitium DNS server
baseurl=http://tdns-server.s3.eu-west-1.amazonaws.com/linux/$basearch/Packages/
gpgcheck=0
enabled=1
$ sudo dnf -y update
$ sudo dnf -y install pdns-server
```

## Browsing repo

You can check the content or download packages [here](http://tdns-server.s3-website-eu-west-1.amazonaws.com/) :rocket:

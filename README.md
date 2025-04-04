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
name=Technitium DNS server repository
baseurl=http://tdns-server.s3.eu-west-1.amazonaws.com/linux/$basearch/Packages/
gpgcheck=0
enabled=1
$ sudo yum -y update
$ sudo yum -y install pdns-server
```


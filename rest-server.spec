%define buildid @BUILDID@

%bcond_without check
%define gobuild(o:) %{expand:
  # https://bugzilla.redhat.com/show_bug.cgi?id=995136#c12
  %global _dwz_low_mem_die_limit 0
  %ifnarch ppc64
  go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-}%{?currentgoldflags} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '%__global_ldflags %{?__golang_extldflags}' -compressdwarf=false" -a -v -x %{?**};
  %else
  go build                -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-}%{?currentgoldflags} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '%__global_ldflags %{?__golang_extldflags}' -compressdwarf=false" -a -v -x %{?**};
  %endif
}

%define gometa(u:spvi) %{expand:%{lua:
local forgeurl    = rpm.expand("%{?-u*}")
if (forgeurl == "") then
	forgeurl        = rpm.expand("%{?forgeurl}")
end
-- Be explicit about the spec variables we’re setting
local function explicitset(rpmvariable,value)
	rpm.define(rpmvariable .. " " .. value)
	if (rpm.expand("%{?-v}") ~= "") then
	rpm.expand("%{echo:Setting %%{" .. rpmvariable .. "} = " .. value .. "\\n}")
	end
end
-- Never ever stomp on a spec variable the packager already set
local function safeset(rpmvariable,value)
	if (rpm.expand("%{?" .. rpmvariable .. "}") == "") then
	explicitset(rpmvariable,value)
	end
end
-- All the Go packaging automation relies on goipath being set
local goipath = rpm.expand("%{?goipath}")
if (goipath == "") then
	rpm.expand("%{error:Please set the Go import path in the “goipath” variable before calling “gometa”!}")
end
-- Compute and set spec variables
if (forgeurl ~= "") then
	rpm.expand("%forgemeta %{?-v} %{?-i} %{?-s} %{?-p} " .. forgeurl .. "\\n")
	safeset("gourl", forgeurl)
else
	safeset("gourl", "https://" .. goipath)
	rpm.expand("%forgemeta %{?-v} %{?-i} -s     %{?-p} %{gourl}\\n")
end
if (rpm.expand("%{?forgesource}") ~= "") then
	safeset("gosource", "%{forgesource}")
else
	safeset("gosource", "%{gourl}/%{archivename}.%{archiveext}")
end
safeset("goname", "%gorpmname %{goipath}")
-- Final spec variable summary if the macro was called with -i
if (rpm.expand("%{?-i}") ~= "") then
	rpm.expand("%{echo:Go-specific packaging variables}")
	rpm.expand("%{echo:  goipath:         %{?goipath}}")
	rpm.expand("%{echo:  goname:          %{?goname}}")
	rpm.expand("%{echo:  gourl:           %{?gourl}}")
	rpm.expand("%{echo:  gosource:        %{?gosource}}")
end}
}

# https://github.com/restic/rest-server
%global goipath         github.com/restic/rest-server
Version:                0.11.0

%gometa

%global common_description %{expand:
Rest Server is a high performance HTTP server that implements restic's REST backend API.
It provides secure and efficient way to backup data remotely,
using restic backup client via the rest: URL.}

%global golicenses    LICENSE


Name:    rest-server
Release: ROCKIT5%{buildid}%{?dist}
Summary: Rest Server is a high performance HTTP server that implements restic's REST backend API.
URL:     %{gourl}
License: BSD
Source0: %{name}-%{version}.tar.gz

ExcludeArch: s390x
BuildRequires: golang >= 1.17.12
BuildRequires: golang < 1.20

%description
%{common_description}

%prep
%autosetup -p1 -n %{name}-%{version}
%setup -q -T -D -n %{name}-%{version}


%build
%if 0%{?redos} == 8
export LDFLAGS=""
export CFLAGS=""
export CGO_CFLAGS=""
export CGO_LDFLAGS=""
%endif
export GO111MODULE=on
export GOFLAGS=-mod=vendor
%gobuild -o %{gobuilddir}/bin/%{name} %{goipath}/cmd/rest-server


%install
mkdir -p %{buildroot}%{_unitdir}
mkdir -p %{buildroot}%{_sysconfdir}/sysconfig
mkdir -p %{buildroot}%{_sbindir}
mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
install -p -m 755 %{gobuilddir}/bin/%{name} %{buildroot}%{_sbindir}
install -p -m 755 systemd/%{name}-starter %{buildroot}%{_sbindir}
install -p -m 755 systemd/%{name}-start-pre %{buildroot}%{_sbindir}
install -p -m 755 systemd/%{name}-stop-post %{buildroot}%{_sbindir}
install -m644 systemd/rest-server.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -m644 systemd/rest-server.service %{buildroot}%{_unitdir}
install -m644 logrotate.d/%{name} %{buildroot}%{_sysconfdir}/logrotate.d/%{name}


%files
%license LICENSE
%doc CHANGELOG.md README.md
%{_sbindir}/%{name}
%{_sbindir}/%{name}-starter
%{_sbindir}/%{name}-start-pre
%{_sbindir}/%{name}-stop-post
%{_unitdir}/%{name}.service
%{_sysconfdir}/logrotate.d/%{name}
%config(noreplace) %{_sysconfdir}/sysconfig/%{name}

%post
systemctl --quiet daemon-reload


%preun
# in case of removal
if [ $1 -eq 0 ]; then
    systemctl --quiet stop %{name}.service
    systemctl --quiet disable %{name}.service
fi


%postun
if [ $1 -eq 0 ]; then
    systemctl --quiet daemon-reload
fi


%changelog
* Tue Mar 28 2023 Aleksandr Rudenko <arudenko@croc.ru> - 0.11.0-2
- add logrotate config

* Fri Aug 12 2022 Aleksandr Rudenko <arudenko@croc.ru> - 0.11.0-1
- Initial package build

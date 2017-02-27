#
# RPM Spec for pScheduler PSClock Tool
#

%define short	psclock
Name:		pscheduler-tool-%{short}
Version:	1.0
Release:	0.24.rc3%{?dist}

Summary:	Clock tester tool class for pScheduler
BuildArch:	noarch
License:	Apache 2.0
Group:		Unspecified

Source0:	%{short}-%{version}.tar.gz

Provides:	%{name} = %{version}-%{release}

Requires:	pscheduler-server
Requires:	python-pscheduler
Requires:	pscheduler-test-idle

BuildRequires:	pscheduler-rpm


%description
Clock tester tool class for pScheduler


%prep
%setup -q -n %{short}-%{version}


%define dest %{_pscheduler_tool_libexec}/%{short}

%build
make \
     DESTDIR=$RPM_BUILD_ROOT/%{dest} \
     install



%post
pscheduler internal warmboot

%postun
pscheduler internal warmboot


%files
%defattr(-,root,root,-)
%{dest}

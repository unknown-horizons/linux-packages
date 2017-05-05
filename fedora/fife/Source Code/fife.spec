%bcond_without fifechan
%bcond_without zip
%bcond_without logging
%bcond_without python

# Upstream prefers fife as package name
%global upname fifengine
Name:           fife
Version:        0.4.1
Release:        1%{?dist}
Summary:        Multi-platform isometric game engine

# https://github.com/fifengine/fifengine/issues/986
# ./engine/core/ext/glee/GLee.cpp: BSD (2 clause) GENERATED FILE
# ./engine/core/ext/glee/GLee.h: BSD (2 clause) GENERATED FILE
# ./engine/core/util/utf8/utf8.h: BSL
# ./engine/core/util/utf8/utf8/checked.h: BSL
# ./engine/core/util/utf8/utf8/core.h: BSL
# ./engine/core/util/utf8/utf8/unchecked.h: BSL
License:        LGPLv2+ and BSD and Boost
URL:            http://www.fifengine.net/
Source0:        https://github.com/fifengine/fifengine/archive/%{version}/%{name}-%{version}.tar.gz
# https://github.com/fifengine/fifengine/pull/988
Patch0:         0001-build-install-Python-bindings-into-arch-specific-dir.patch
# https://github.com/fifengine/fifengine/pull/989
Patch1:         0001-build-use-GNUInstallDirs.patch
# https://github.com/fifengine/fifengine/commit/400636b6fd76e1d65bd1f2e261d51486f422b3b3
Patch2:         0001-Removed-leftover-stuff-from-Cursor.-Refs-991.patch

BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  SDL2-devel
BuildRequires:  SDL2_image-devel
BuildRequires:  SDL2_ttf-devel
BuildRequires:  boost-devel
BuildRequires:  libpng-devel
BuildRequires:  openal-devel
BuildRequires:  mesa-libGL-devel
BuildRequires:  tinyxml-devel
%if %{with fifechan}
BuildRequires:  fifechan-sdl-devel
%if %{with opengl}
BuildRequires:  fifechan-opengl-devel
%endif
%endif
# Something like optional builddeps
BuildRequires:  pkgconfig(ogg)
BuildRequires:  pkgconfig(vorbisfile)

%description
Flexible Isometric Free Engine (FIFE) is a multi-platform isometric game engine
written in C++. It comes with Python bindings allowing users to create games
using Python as well as C++. The engine is extendable and enables you to add
any feature you can imagine to your project.

%package        devel
Summary:        Development libraries and header files for %{name}
Requires:       %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description    devel
%{summary}.

%if %{with python}
%package     -n python2-%{name}
Summary:        Python 2.x bindings for %{name}
BuildRequires:  python2-devel
BuildRequires:  swig

%description -n python2-%{name}
%{summary}.
%endif

%prep
%autosetup -n %{upname}-%{version}

%build
mkdir %{_target_platform}
pushd %{_target_platform}
  %cmake .. \
    -GNinja                                               \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo                     \
    -Dopengl=ON                                           \
    -Dfifechan=%{?with_fifechan:ON}%{!?with_fifechan:OFF} \
    -Dzip=%{?with_zip:ON}%{!?with_zip:OFF}                \
    -Dlogging=%{?with_logging:ON}%{!?with_logging:OFF}    \
    -Dbuild-python=%{?with_python:ON}%{!?with_python:OFF} \
    -Dbuild-library=ON                                    \
    %{nil}
popd
%ninja_build -C %{_target_platform}

%install
%ninja_install -C %{_target_platform}

#check
# Something too much complicated needed to run test suite

%files
%license LICENSE.md
%doc README.md CHANGELOG.md
%{_libdir}/lib%{name}.so.*

%files devel
%{_libdir}/lib%{name}.so
%{_includedir}/%{name}/

%if %{with python}
%files -n python2-%{name}
%{python2_sitearch}/%{name}/
%endif

%changelog
* Thu Feb 09 2017 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 0.4.1-1
- Initial package

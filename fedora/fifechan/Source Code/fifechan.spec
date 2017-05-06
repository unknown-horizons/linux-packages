%bcond_without opengl
%if %{with opengl}
  %bcond_with opengl_contrib
%endif
%bcond_without sdl
%if %{with sdl}
  %bcond_without sdl_contrib
%endif

Name:           fifechan
Version:        0.1.4
Release:        1%{?dist}
Summary:        C++ GUI library designed for games

License:        LGPLv2+ and BSD and Boost
URL:            https://github.com/fifengine/fifechan
Source0:        %{url}/archive/%{version}/%{name}-%{version}.tar.gz

BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  make

%description
Fifechan is a lightweight cross platform GUI library written in C++
specifically designed for games. It has a small yet powerful built in set of
extendable GUI Widgets allowing users to create virtually unlimited types of
widgets. Fifechan supports rendering in SDL, OpenGL, or Allegro out of the box
or it can be adapted to use any rendering engine the user requires. Events are
pushed to Fifechan which allows users to use any input library they wish or
they could use the built in input handling through either SDL input or
Allegro input. The primary goal for Fifechan is to keep it extendable,
lightweight and still be powerful enough to use in all types of games
out of the box.

%package devel
Summary:        Development files for %{name}
Requires:       %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description devel
%{summary}.

%if %{with opengl}
%package opengl
Summary:        OpenGL extension for %{name}
BuildRequires:  mesa-libGL-devel
Requires:       %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description opengl
%{summary}.

%package opengl-devel
Summary:        Development files for OpenGL extension for %{name}
Requires:       %{name}-devel%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       %{name}-opengl%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       mesa-libGL-devel%{?_isa}

%description opengl-devel
%{summary}.
%endif

%if %{with sdl}
%package sdl
Summary:        SDL extension for %{name}
BuildRequires:  pkgconfig(sdl2)
# ignatenkobrain: -lSDL2Main requires static subpkg
BuildRequires:  SDL2-static
# ignatenkobrain: Looks like SDL2_image is not used anywhere
BuildRequires:  pkgconfig(SDL2_image)
%if %{with sdl_contrib}
BuildRequires:  pkgconfig(SDL2_ttf)
%endif
Requires:       %{name}%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}

%description sdl
%{summary}.

%package sdl-devel
Summary:        Development files for SDL extension for %{name}
Requires:       %{name}-devel%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       %{name}-sdl%{?_isa} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       SDL2-devel%{?_isa}
%if %{with sdl_contrib}
Requires:       SDL2_ttf-devel%{?_isa}
%endif

%description sdl-devel
%{summary}.
%endif

%prep
%autosetup
mkdir %{_target_platform}

%build
pushd %{_target_platform}
  %cmake ..                                                                        \
    -DENABLE_OPENGL=%{?with_opengl:ON}%{!?with_opengl:OFF}                         \
    -DENABLE_OPENGL_CONTRIB=%{?with_opengl_contrib:ON}%{!?with_opengl_contrib:OFF} \
    -DENABLE_SDL=%{?with_sdl:ON}%{!?with_sdl:OFF}                                  \
    -DENABLE_SDL_CONTRIB=%{?with_sdl_contrib:ON}%{!?with_sdl_contrib:OFF}          \
    %{nil}
popd
%make_build -C %{_target_platform}

%install
%make_install -C %{_target_platform}

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig
%files
%{_libdir}/lib%{name}.so.*

%files devel
%{_libdir}/lib%{name}.so
%exclude %{_includedir}/%{name}/opengl/
%exclude %{_includedir}/%{name}/opengl.hpp
%exclude %{_includedir}/%{name}/contrib/opengl/
%exclude %{_includedir}/%{name}/sdl/
%exclude %{_includedir}/%{name}/sdl.hpp
%exclude %{_includedir}/%{name}/contrib/sdl/
%{_includedir}/%{name}/
%{_includedir}/%{name}.hpp

%if %{with opengl}
%post opengl -p /sbin/ldconfig
%postun opengl -p /sbin/ldconfig
%files opengl
%{_libdir}/lib%{name}_opengl.so.*

%files opengl-devel
%{_libdir}/lib%{name}_opengl.so
%{_includedir}/%{name}/opengl/
%{_includedir}/%{name}/opengl.hpp
%if %{with opengl_contrib}
%{_includedir}/%{name}/contrib/opengl/
%endif
%endif

%if %{with sdl}
%post sdl -p /sbin/ldconfig
%postun sdl -p /sbin/ldconfig
%files sdl
%{_libdir}/lib%{name}_sdl.so.*

%files sdl-devel
%{_libdir}/lib%{name}_sdl.so
%{_includedir}/%{name}/sdl/
%{_includedir}/%{name}/sdl.hpp
%if %{with sdl_contrib}
%{_includedir}/%{name}/contrib/sdl/
%endif
%endif

%changelog
* Thu Feb 09 2017 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 0.1.4-1
- Update to 0.1.4

* Wed Nov 16 2016 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.1.3-1
- Update to 0.1.3

* Fri Sep 02 2016 Igor Gnatenko <i.gnatenko.brain@gmail.com> - 0.1.2-2.git7b77184
- Add couple of missing Requires
- Add %%post(un) triggers to ldconfig
- Fix license tag

* Sun Aug 07 2016 Igor Gnatenko <ignatenko@redhat.com> - 0.1.2-1.git7b77184
- Initial package

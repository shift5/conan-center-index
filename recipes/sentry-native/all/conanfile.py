import os
import sys
import glob
from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
from conans.util.env_reader import get_env


class SentryNativeConan(ConanFile):
    name = "sentry-native"
    description = "The Sentry Native SDK is an error and crash reporting client for native applications,\n" \
                  "optimized for C and C++. Sentry allows to add tags,\n" \
                  "breadcrumbs and arbitrary custom context to enrich error reports."
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/getsentry/sentry-native"
    license = "MIT"
    topics = ("conan", "breakpad", "crashpad",
              "error-reporting", "crash-reporting")
    _patch_file = "musl.patch"
    exports_sources = ["CMakeLists.txt", _patch_file]
    generators = "cmake", "cmake_find_package"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "backend": ["none", "inproc", "crashpad", "breakpad"],
        "transport": ["none", "curl", "winhttp"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "backend": "inproc",
        "transport": "curl"
    }

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    _cmake = None

    def requirements(self):
        if self.options.transport == "curl":
            self.requires("libcurl/7.71.0")

        if self.options.backend == "crashpad":
            raise ConanInvalidConfiguration("crashpad not available yet in CCI")
        if self.options.backend == "breakpad":
            raise ConanInvalidConfiguration("breakpad not available yet in CCI")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def system_requirements(self):
        if tools.os_info.is_linux and tools.os_info.linux_distro == "alpine":
            cmd = "%sapk add libexecinfo-dev" % self._get_sudo_str()
            self.run(cmd)

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)
        if tools.os_info.is_linux and tools.os_info.linux_distro == "alpine":
            tools.patch(patch_file=self._patch_file, base_path=self._source_subfolder)

    def configure(self):
        if self.options.backend == "inproc" and self.settings.os == "Windows" and tools.Version(self.version) < "0.4":
            raise ConanInvalidConfiguration("The in-process backend is not supported on Windows")

    def _configure_cmake(self):
        if self._cmake:
            return self._cmake
        self._cmake = CMake(self)
        self._cmake.definitions["SENTRY_BACKEND"] = self.options.backend
        self._cmake.definitions["SENTRY_ENABLE_INSTALL"] = True
        self._cmake.definitions["SENTRY_TRANSPORT"] = self.options.transport
        self._cmake.definitions["SENTRY_PIC"] = self.options.get_safe("fPIC", False)
        self._cmake.configure()
        return self._cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        for pdb in glob.glob(os.path.join(self.package_folder, "bin", "*.pdb")):
            os.unlink(pdb)

    def package_info(self):
        self.cpp_info.libs = ["sentry"]
        if self.settings.os in ("Android", "Linux"):
            self.cpp_info.exelinkflags = ["-Wl,-E,--build-id=sha1"]
            self.cpp_info.sharedlinkflags = ["-Wl,-E,--build-id=sha1"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl"]
        if tools.os_info.is_linux and tools.os_info.linux_distro == "alpine":
            self.cpp_info.system_libs.extend(["execinfo"])
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["winhttp", "dbghelp", "pathcch", "shlwapi"]

        if not self.options.shared:
            self.cpp_info.defines = ["SENTRY_BUILD_STATIC"]

    def _is_sudo_enabled(self):
        if "CONAN_SYSREQUIRES_SUDO" not in os.environ:
            if not which("sudo"):
                return False
            if os.name == 'posix' and os.geteuid() == 0:
                return False
            if os.name == 'nt':
                return False
        return get_env("CONAN_SYSREQUIRES_SUDO", True)

    def _get_sudo_str(self):
        if not self._is_sudo_enabled():
            return ""
        if hasattr(sys.stdout, "isatty") and not sys.stdout.isatty():
            return "sudo -A "
        else:
            return "sudo "

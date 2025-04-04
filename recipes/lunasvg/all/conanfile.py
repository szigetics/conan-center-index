from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rmdir
from conan.tools.build import check_min_cppstd
from conan.tools.scm import Version
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

import os

required_conan_version = ">=2.1"

class LunaSVGConan(ConanFile):
    name = "lunasvg"
    description = "lunasvg is a standalone SVG rendering library in C++."
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/sammycage/lunasvg"
    topics = ("svg", "renderer", )
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _min_cppstd(self):
        if Version(self.version) <= "2.3.2":
            return "14"
        if Version(self.version) <= "2.3.8":
            return "17"
        if Version(self.version) >= "3.0.0":
            return "17"
        return "11"

    @property
    def _compilers_minimum_version(self):
        return {
            "14": {
                "gcc": "5",
                "clang": "3.5",
                "apple-clang": "10",
                "Visual Studio": "15",
                "msvc": "191",
            },
            "17": {
                "gcc": "7.1",
                "clang": "7",
                "apple-clang": "12.0",
                "Visual Studio": "16",
                "msvc": "192",
            },
        }.get(self._min_cppstd, {})

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if Version(self.version) < "2.3.5":
            self.requires("plutovg/cci.20220103")
        elif Version(self.version) < "3.0.0":
            self.requires("plutovg/cci.20221030")
        else:
            self.requires("plutovg/0.0.7")

    def validate(self):
        if self.info.settings.compiler.cppstd:
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(str(self.info.settings.compiler), False)
        if minimum_version and Version(self.info.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        if Version(self.version) < "2.4.1":
            tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.variables["LUNASVG_BUILD_EXAMPLES"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["lunasvg"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        if Version(self.version) >= "2.4.1" and not self.options.shared:
            self.cpp_info.defines = ["LUNASVG_BUILD_STATIC"]

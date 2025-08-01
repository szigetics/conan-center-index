from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, copy, get, rmdir, replace_in_file
import os

required_conan_version = ">=2.0"


class ArucoConan(ConanFile):
    name = "aruco"
    description = "Augmented reality library based on OpenCV "
    topics = ("augmented-reality", "robotics", "markers")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.uco.es/investiga/grupos/ava/node/26"
    license = "GPL-3.0-only"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [False, True],
        "fPIC": [False, True],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Header used in public markerdetector.h
        # cv::FileStorage::FileStorage used by aruco::CameraParameters::saveToFile
        self.requires("opencv/[>=4.9.0 <5]", transitive_headers=True, transitive_libs=True)
        # Header used in levmarq.h
        self.requires("eigen/[>=3.4.0 <4]", transitive_headers=False)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ARUCO_DEVINSTALL"] = True
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_GLSAMPLES"] = False
        tc.variables["BUILD_UTILS"] = False
        tc.variables["BUILD_DEBPACKAGE"] = False
        tc.variables["BUILD_SVM"] = False
        tc.variables["INSTALL_DOC"] = False
        tc.variables["USE_OWN_EIGEN3"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("eigen", "cmake_additional_variables_prefixes", ["Eigen3"])
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "aruco")
        self.cpp_info.includedirs.append(os.path.join("include", "aruco"))
        self.cpp_info.libs = collect_libs(self)

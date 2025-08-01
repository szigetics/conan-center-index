from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.microsoft import is_msvc_static_runtime
import os

required_conan_version = ">=2.0"


class CCTagConan(ConanFile):
    name = "cctag"
    description = "Detection of CCTag markers made up of concentric circles."
    license = "MPL-2.0"
    topics = ("cctag", "computer-vision", "detection", "image-processing",
              "markers", "fiducial-markers", "concentric-circles")
    homepage = "https://github.com/alicevision/CCTag"
    url = "https://github.com/conan-io/conan-center-index"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "serialize": [True, False],
        "visual_debug": [True, False],
        "no_cout": [True, False],
        "with_cuda": [True, False],
        "cuda_cc_list": [None, "ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "serialize": False,
        "visual_debug": False,
        "no_cout": True,
        "with_cuda": False,
        "cuda_cc_list": None, # e.g. "5.2;7.5;8.2", builds all up to 7.5 by default
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def package_id(self):
        if not self.info.options.with_cuda:
            del self.info.options.cuda_cc_list

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"boost/1.85.0", transitive_headers=True, transitive_libs=True)
        self.requires("opencv/[>=4.9.0 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("onetbb/2021.10.0")
        self.requires("eigen/[>=3.4.0 <4]", transitive_headers=True)

    @property
    def _required_boost_components(self):
        return [
            "atomic", "chrono", "date_time", "exception", "filesystem",
            "math", "serialization", "stacktrace", "system", "thread", "timer",
        ]

    def validate(self):
        miss_boost_required_comp = any(
            self.dependencies["boost"].options.get_safe(f"without_{boost_comp}", True)
            for boost_comp in self._required_boost_components
        )
        if self.dependencies["boost"].options.header_only or miss_boost_required_comp:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires non header-only boost with these components: "
                f"{', '.join(self._required_boost_components)}",
            )

        if is_msvc_static_runtime(self) and not self.options.shared and self.dependencies["onetbb"].options.shared:
            raise ConanInvalidConfiguration("this specific configuration is prevented due to internal c3i limitations")

        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CCTAG_SERIALIZE"] = self.options.serialize
        tc.variables["CCTAG_VISUAL_DEBUG"] = self.options.visual_debug
        tc.variables["CCTAG_NO_COUT"] = self.options.no_cout
        tc.variables["CCTAG_BUILD_APPS"] = False
        tc.variables["CCTAG_EIGEN_NO_ALIGN"] = True
        tc.variables["CCTAG_USE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.variables["CCTAG_ENABLE_SIMD_AVX2"] = False
        tc.variables["CCTAG_BUILD_TESTS"] = False
        tc.variables["CCTAG_BUILD_DOC"] = False

        tc.variables["CCTAG_WITH_CUDA"] = self.options.with_cuda
        tc.variables["CCTAG_CUDA_CC_CURRENT_ONLY"] = False
        tc.variables["CCTAG_NVCC_WARNINGS"] = False
        if self.options.cuda_cc_list:
            tc.variables["CCTAG_CUDA_CC_LIST_INIT"] = self.options.cuda_cc_list
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        # Cleanup RPATH if Apple in shared lib of install tree
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                              "SET(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)",
                              "")
        # Link to OpenCV targets
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
                              "${OpenCV_LIBS}",
                              "opencv_core opencv_videoio opencv_imgproc opencv_imgcodecs")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CCTag")
        self.cpp_info.set_property("cmake_target_name", "CCTag::CCTag")
        suffix = "d" if self.settings.build_type == "Debug" else ""
        self.cpp_info.libs = [f"CCTag{suffix}"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "pthread"])
        self.cpp_info.requires = [
            "boost::atomic",
            "boost::chrono",
            "boost::date_time",
            "boost::exception",
            "boost::filesystem",
            "boost::math_c99",
            "boost::serialization",
            "boost::system",
            "boost::thread",
            "boost::timer",
            "eigen::eigen",
            "onetbb::onetbb",
            "opencv::opencv_core",
            "opencv::opencv_imgcodecs",
            "opencv::opencv_imgproc",
            "opencv::opencv_videoio",
        ]
        if self.settings.os == "Windows":
            self.cpp_info.requires.append("boost::stacktrace_windbg")
        else:
            self.cpp_info.requires.append("boost::stacktrace_basic")

        # CCTag links against shared CUDA runtime by default and does not use it in headers,
        # so we don't need to explicitly link against it.

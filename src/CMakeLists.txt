# GaelaniLIVE: PS5 animated wallpaper. Builds inside the OnionHEN beta2 tree as source/gaelanilive
# (add_subdirectory(gaelanilive)), using OnionHEN's libraries. GPL-3.0.
#   gaelanilive_shellui.elf - runs inside SceShellUI (embedded in gaelanilive.elf)
#   gaelanilive.elf         - the payload the user loads
cmake_minimum_required (VERSION 3.20)
project(gaelanilive C CXX ASM)

onion_module_prologue(C_STANDARD 11 CXX_STANDARD 20)
set(D_CWD "${CMAKE_CURRENT_SOURCE_DIR}")
onion_output_dirs()

set(CMAKE_C_FLAGS "${ONION_PS5_TARGET_FLAGS} -fPIC -fPIE -march=znver2 -Wall -fstack-protector-all -ffunction-sections -fdata-sections")
set(CMAKE_CXX_FLAGS "${CMAKE_C_FLAGS}")
set(CMAKE_C_FLAGS_RELEASE "-Os -DNDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "-Os -DNDEBUG")

add_executable(gaelanilive_shellui ${D_CWD}/gaelanilive_shellui.cpp)
set_target_properties(gaelanilive_shellui PROPERTIES OUTPUT_NAME "gaelanilive_shellui.elf")
target_link_options(gaelanilive_shellui PRIVATE "-Wl,--gc-sections")
add_dependencies(gaelanilive_shellui onion_proc onion_platform onion_detour)
target_include_directories(gaelanilive_shellui PRIVATE
	"${PROJECT_ROOT}/libonion_proc/include"
	"${PROJECT_ROOT}/libonion_platform/include"
	"${PROJECT_ROOT}/libonion_detour/include"
	"${PROJECT_ROOT}/include")
target_link_directories(gaelanilive_shellui PUBLIC "${ONIONHEN_PS5_STUB_DIR}")
target_link_libraries(gaelanilive_shellui PUBLIC onion_payload onion_proc onion_platform onion_detour SceNotification kernel_sys)
onion_strip_debug(gaelanilive_shellui)

add_executable(gaelanilive ${D_CWD}/gaelanilive_daemon.cpp ${D_CWD}/gaelanilive_web.cpp ${D_CWD}/gaelanilive_tile.cpp ${D_CWD}/gaelanilive_update.cpp ${D_CWD}/zstd_decompress.c)
set_target_properties(gaelanilive PROPERTIES OUTPUT_NAME "gaelanilive.elf")
if(NOT DEFINED GAELANILIVE_VERSION)
	set(GAELANILIVE_VERSION "0.0.0-dev") # CI passes -DGAELANILIVE_VERSION=<release tag>
endif()
target_link_options(gaelanilive PRIVATE "-Wl,--gc-sections")
add_dependencies(gaelanilive gaelanilive_shellui NineS onion_proc onion_platform onion_elfldr)
set_source_files_properties(${D_CWD}/gaelanilive_daemon.cpp PROPERTIES OBJECT_DEPENDS "${ONIONHEN_OUT_BIN}/gaelanilive_shellui.elf")
set_source_files_properties(${D_CWD}/gaelanilive_web.cpp PROPERTIES OBJECT_DEPENDS "${D_CWD}/gaelanilive_page.html;${D_CWD}/gaelanilive_remote.html")
set_source_files_properties(${D_CWD}/gaelanilive_tile.cpp PROPERTIES OBJECT_DEPENDS "${D_CWD}/icon0.png")
target_compile_definitions(gaelanilive PRIVATE
	GAELANILIVE_SHELLUI_ELF="${ONIONHEN_OUT_BIN}/gaelanilive_shellui.elf"
	GAELANILIVE_PAGE_HTML="${D_CWD}/gaelanilive_page.html"
	GAELANILIVE_REMOTE_HTML="${D_CWD}/gaelanilive_remote.html"
	GAELANILIVE_ICON_PNG="${D_CWD}/icon0.png"
	GAELANILIVE_VERSION="${GAELANILIVE_VERSION}")
target_include_directories(gaelanilive PRIVATE
	"${PROJECT_ROOT}/libonion_proc/include"
	"${PROJECT_ROOT}/libonion_platform/include"
	"${PROJECT_ROOT}/include")
target_link_directories(gaelanilive PUBLIC "${ONIONHEN_PS5_STUB_DIR}")
target_link_libraries(gaelanilive PUBLIC NineS onion_proc onion_platform onion_elfldr SceNotification SceSystemService SceUserService SceHttp SceSsl SceNet kernel_sys)
onion_strip_debug(gaelanilive)

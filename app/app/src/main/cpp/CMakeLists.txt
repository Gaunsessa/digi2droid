cmake_minimum_required(VERSION 3.22.1)

project(digi2droid_gphoto)

set(GPHOTO_ABI_ROOT "${CMAKE_SOURCE_DIR}/../../../../third_party/libgphoto2-android/${ANDROID_ABI}")
set(GPHOTO_INCLUDE "${CMAKE_SOURCE_DIR}/../../../../third_party/libgphoto2-android/include")

if(NOT EXISTS "${GPHOTO_ABI_ROOT}/libgphoto2.so")
    message(FATAL_ERROR
        "libgphoto2 prebuilts not found for ${ANDROID_ABI}.\n"
        "Expected: ${GPHOTO_ABI_ROOT}/libgphoto2.so\n"
        "git submodule update --init --recursive third_party/libtool third_party/libusb third_party/libgphoto2\n"
        "Then: ANDROID_ABI=${ANDROID_ABI} ./scripts/build-libgphoto2-android.sh")
endif()

add_library(gphoto2 SHARED IMPORTED)
set_target_properties(gphoto2 PROPERTIES
    IMPORTED_LOCATION "${GPHOTO_ABI_ROOT}/libgphoto2.so")

add_library(gphoto2_port SHARED IMPORTED)
set_target_properties(gphoto2_port PROPERTIES
    IMPORTED_LOCATION "${GPHOTO_ABI_ROOT}/libgphoto2_port.so")

add_library(digi2droid_gphoto SHARED gphoto_jni.cpp)

# setenv() is POSIX / GNU; exposed on Android when _GNU_SOURCE is defined.
target_compile_definitions(digi2droid_gphoto PRIVATE _GNU_SOURCE=1)

target_include_directories(digi2droid_gphoto PRIVATE "${GPHOTO_INCLUDE}")

find_library(log-lib log)

target_link_libraries(digi2droid_gphoto
    gphoto2
    gphoto2_port
    ${log-lib})
